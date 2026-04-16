from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from ag_ui.core import RunAgentInput
from ag_ui.core.types import SystemMessage
from ag_ui_langgraph.agent import LangGraphAgent
from ag_ui_langgraph.utils import camel_to_snake
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.runnables.config import ensure_config

from app.auth.auth_context import get_effective_user_id
from app.chat.store import get_chat_store, get_chat_store_status
from app.memory.memory_runtime import (
    add_turn_messages_to_memory,
    build_memory_prompt,
    recall_memory_bundle,
)
from app.observability import propagate_langfuse_attributes
from app.sandbox import bind_sandbox_context, get_sandbox_manager


def extract_graph_output_text(result: Any) -> str:
    if isinstance(result, dict):
        messages = result.get("messages")
        if isinstance(messages, list):
            for msg in reversed(messages):
                if isinstance(msg, dict):
                    role = str(msg.get("role", "")).lower()
                    if role in {"assistant", "ai"}:
                        content = msg.get("content", "")
                        return content if isinstance(content, str) else str(content)
                role = str(getattr(msg, "type", "") or getattr(msg, "role", "")).lower()
                if role in {"assistant", "ai"}:
                    content = getattr(msg, "content", "")
                    return content if isinstance(content, str) else str(content)
    return str(result)


def _stringify_content(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str) and text:
                    parts.append(text)
                    continue
                nested = item.get("content")
                if isinstance(nested, str) and nested:
                    parts.append(nested)
        return "".join(parts)
    return str(content) if content is not None else ""


def _extract_last_user_message(messages: object, fallback_messages: object | None = None) -> str:
    text = _extract_last_user_message_once(messages)
    if text:
        return text
    return _extract_last_user_message_once(fallback_messages)


def _extract_last_user_message_once(messages: object | None) -> str:
    if not isinstance(messages, list):
        return ""
    for msg in reversed(messages):
        if isinstance(msg, dict):
            role = str(msg.get("role", "")).lower()
            if role in {"user", "human"}:
                return _stringify_content(msg.get("content", ""))
            continue
        role = str(getattr(msg, "type", "") or getattr(msg, "role", "")).lower()
        if role in {"human", "user"}:
            return _stringify_content(getattr(msg, "content", ""))
    return ""


def _extract_last_assistant_message(messages: object | None) -> str:
    if not isinstance(messages, list):
        return ""
    for msg in reversed(messages):
        if isinstance(msg, dict):
            role = str(msg.get("role", "")).lower()
            if role in {"assistant", "ai"}:
                return _stringify_content(msg.get("content", ""))
            continue
        role = str(getattr(msg, "type", "") or getattr(msg, "role", "")).lower()
        if role in {"assistant", "ai"}:
            return _stringify_content(getattr(msg, "content", ""))
    return ""


async def _load_checkpoint_assistant_text(agent: LangGraphAgent, thread_id: str) -> str:
    config = ensure_config(agent.config.copy() if agent.config else {})
    config["configurable"] = {**(config.get("configurable", {}) or {}), "thread_id": thread_id}
    state = await agent.graph.aget_state(config)
    values = getattr(state, "values", None)
    if isinstance(values, dict):
        return _extract_last_assistant_message(values.get("messages"))
    return ""


def _extract_assistant_piece(event: object) -> tuple[str, str]:
    def from_mapping(mapping: dict) -> tuple[str, str]:
        role = str(mapping.get("role", "")).lower()
        if role == "assistant":
            delta = mapping.get("delta")
            if isinstance(delta, str) and delta:
                return "delta", delta
            content = mapping.get("content")
            if isinstance(content, str) and content:
                return "full", content
            text = mapping.get("text")
            if isinstance(text, str) and text:
                return "full", text

        nested = mapping.get("message")
        if isinstance(nested, dict):
            return from_mapping(nested)
        return "", ""

    if isinstance(event, dict):
        return from_mapping(event)
    if hasattr(event, "model_dump"):
        try:
            dumped = event.model_dump()
            if isinstance(dumped, dict):
                return from_mapping(dumped)
        except Exception:
            return "", ""
    return "", ""


class ForwardingLangGraphAgent(LangGraphAgent):
    """Inject forwarded props and persist memory/chat side effects."""
    # 充血 langgraph_default_merge_state
    def langgraph_default_merge_state(
        self,
        state: dict[str, Any],
        messages: list[BaseMessage],
        input: RunAgentInput,
    ) -> dict[str, Any]:
        """Preserve injected system messages instead of dropping the first one."""
        existing_messages: list[Any] = state.get("messages", [])

        for msg in existing_messages:
            if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
                for tc in msg.tool_calls:
                    if isinstance(tc.get("args"), str):
                        try:
                            tc["args"] = json.loads(tc["args"])
                        except (json.JSONDecodeError, TypeError):
                            tc["args"] = {}

        agui_tool_content = {
            m.tool_call_id: m.content
            for m in messages
            if isinstance(m, ToolMessage) and hasattr(m, "tool_call_id")
        }
        replaced_tool_call_ids = set()
        if agui_tool_content:
            last_human_idx = -1
            for i in range(len(existing_messages) - 1, -1, -1):
                if isinstance(existing_messages[i], HumanMessage):
                    last_human_idx = i
                    break
            if last_human_idx >= 0:
                for i in range(last_human_idx + 1, len(existing_messages)):
                    msg = existing_messages[i]
                    if (
                        isinstance(msg, ToolMessage)
                        and isinstance(msg.content, str)
                        and self._ORPHAN_TOOL_MSG_RE.match(msg.content)
                        and hasattr(msg, "tool_call_id")
                        and msg.tool_call_id in agui_tool_content
                    ):
                        msg.content = agui_tool_content[msg.tool_call_id]
                        replaced_tool_call_ids.add(msg.tool_call_id)

        existing_message_ids = {msg.id for msg in existing_messages}
        new_messages = [msg for msg in messages if msg.id not in existing_message_ids]

        tools = input.tools or []
        tools_as_dicts = []
        for tool in tools:
            if hasattr(tool, "model_dump"):
                tools_as_dicts.append(tool.model_dump())
            elif hasattr(tool, "dict"):
                tools_as_dicts.append(tool.dict())
            else:
                tools_as_dicts.append(tool)

        all_tools = [*state.get("tools", []), *tools_as_dicts]
        seen_names = set()
        unique_tools = []
        for tool in all_tools:
            tool_name = tool.get("name") if isinstance(tool, dict) else getattr(tool, "name", None)
            if tool_name and tool_name not in seen_names:
                seen_names.add(tool_name)
                unique_tools.append(tool)
            elif not tool_name:
                unique_tools.append(tool)

        return {
            **state,
            "messages": new_messages,
            "tools": unique_tools,
            "ag-ui": {
                "tools": unique_tools,
                "context": input.context or [],
            },
            "copilotkit": {
                **state.get("copilotkit", {}),
                "actions": unique_tools,
            },
        }

    async def run(self, input: RunAgentInput):
        forwarded = {}
        if getattr(input, "forwarded_props", None):
            forwarded = {camel_to_snake(k): v for k, v in input.forwarded_props.items()}

        merged_state = dict(input.state or {})
        last_user_message = _extract_last_user_message(input.messages, merged_state.get("messages"))
        user_id = get_effective_user_id()
        sandbox_session_id = input.thread_id or f"run-{input.run_id or uuid4()}"
        sandbox_context = await get_sandbox_manager().ensure_session(
            user_id=user_id,
            session_id=sandbox_session_id,
        )
        for key, value in forwarded.items():
            merged_state.setdefault(key, value)

        patched_messages = list(input.messages or [])
        if last_user_message:
            try:
                memory_bundle = await recall_memory_bundle(
                    user_id=user_id,
                    session_id=input.thread_id,
                    query=last_user_message,
                )
                memory_prompt = build_memory_prompt(memory_bundle)
                print(
                    "[memory] injected",
                    {
                        "user_id": user_id,
                        "session_id": input.thread_id,
                        "instructions": len(memory_bundle.get("instructions") or []),
                        "profiles": len(memory_bundle.get("profiles") or []),
                        "episodes": len(memory_bundle.get("episodes") or []),
                    },
                )
            except Exception as exc:
                memory_prompt = None
                print(f"[memory] retrieval failed for user_id={user_id}: {exc}")
            if memory_prompt:
                patched_messages = [SystemMessage(id=str(uuid4()), content=memory_prompt), *patched_messages]

        patched = input.model_copy(
            update={"forwarded_props": forwarded, "state": merged_state, "messages": patched_messages}
        )

        if input.thread_id and last_user_message and get_chat_store_status().get("enabled"):
            try:
                store = get_chat_store()
                await store.ensure_session(
                    user_id=user_id,
                    session_id=input.thread_id,
                    title_hint=last_user_message,
                )
                await store.append_message(
                    user_id=user_id,
                    session_id=input.thread_id,
                    role="user",
                    content=last_user_message,
                    dedupe_tail=True,
                )
            except Exception as exc:
                print(f"[chat] write user message failed: {exc}")

        assistant_full = ""
        assistant_deltas: list[str] = []
        with (
            bind_sandbox_context(sandbox_context),
            propagate_langfuse_attributes(
                user_id=user_id,
                session_id=sandbox_session_id,
                trace_name="chat-session",
                metadata={
                    "channel": "chat",
                    "thread_id": sandbox_session_id,
                },
            ),
        ):
            event_stream = super().run(patched)
            async for event in event_stream:
                piece_type, piece = _extract_assistant_piece(event)
                if piece_type == "full":
                    assistant_full = piece
                elif piece_type == "delta":
                    assistant_deltas.append(piece)
                yield event

        assistant_text = (assistant_full or "".join(assistant_deltas)).strip()
        if not assistant_text and input.thread_id:
            try:
                assistant_text = (await _load_checkpoint_assistant_text(self, input.thread_id)).strip()
            except Exception as exc:
                print(f"[chat] load assistant checkpoint failed: {exc}")

        if last_user_message:
            turn_messages = [{"role": "user", "content": last_user_message}]
            if assistant_text:
                turn_messages.append({"role": "assistant", "content": assistant_text})
            try:
                await add_turn_messages_to_memory(user_id, turn_messages, session_id=input.thread_id)
            except Exception as exc:
                print(f"[memory] write failed for user_id={user_id}: {exc}")

        if input.thread_id and get_chat_store_status().get("enabled"):
            if assistant_text:
                try:
                    await get_chat_store().append_message(
                        user_id=user_id,
                        session_id=input.thread_id,
                        role="assistant",
                        content=assistant_text,
                        dedupe_tail=True,
                    )
                except Exception as exc:
                    print(f"[chat] write assistant message failed: {exc}")
