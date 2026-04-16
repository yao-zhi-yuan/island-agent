from __future__ import annotations

import asyncio
import json
import os
from functools import lru_cache
from typing import Any

from mem0 import Memory
from mem0.memory.utils import ensure_json_instruction, extract_json, normalize_facts, remove_code_blocks

from app.memory.extractor import (
    build_episode_summary,
    extract_profile_candidates,
    extract_profile_candidates_from_facts,
)
from app.memory.episode_vector import get_episode_vector_store
from app.memory.mem0_store import _build_local_mem0_config
from app.memory.store import get_memory_store, get_memory_store_status

_PROFILE_PROMPT_KEY_WHITELIST = {
    "response_language",
    "response_style",
    "response_format",
    "primary_os",
    "primary_editor",
    "primary_shell",
    "explicit",
}


def is_mem0_enabled() -> bool:
    return os.getenv("MEM0_ENABLED", "0") == "1"


@lru_cache(maxsize=1)
def _get_profile_memory() -> Memory:
    return Memory.from_config(_build_local_mem0_config())
def _store_enabled() -> bool:
    return bool(get_memory_store_status().get("enabled"))


def _env_int(name: str, default: int, *, minimum: int = 1, maximum: int = 10000) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, min(value, maximum))


def _extract_memory_texts(resp: dict[str, Any] | list[Any] | None) -> list[str]:
    if resp is None:
        return []
    if isinstance(resp, dict):
        rows = resp.get("results", [])
    elif isinstance(resp, list):
        rows = resp
    else:
        rows = []
    if not isinstance(rows, list):
        return []

    texts: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        text = row.get("memory") or row.get("text")
        if text and isinstance(text, str):
            texts.append(text.strip())
    deduped: list[str] = []
    seen: set[str] = set()
    for item in texts:
        if not item or item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


async def _extract_profile_candidates_with_mem0(user_message: str) -> list[Any]:
    if not is_mem0_enabled() or not user_message.strip():
        return []

    memory = _get_profile_memory()
    system_prompt = """
You are a user profile extractor.
Extract only stable user profile facts from the user's message.

Only keep facts that are likely to remain useful across sessions, such as:
- response language preferences
- response style preferences
- format preferences
- stable environment facts (OS, editor, shell)
- explicit long-term preferences the user asks you to remember

Do NOT extract:
- questions
- one-time requests
- temporary tasks
- transient goals
- generic problem statements

Return valid JSON in the shape:
{"facts": ["..."]}
""".strip()
    user_prompt = f"Input:\nuser: {user_message.strip()}"
    system_prompt, user_prompt = ensure_json_instruction(system_prompt, user_prompt)

    try:
        response = await asyncio.to_thread(
            memory.llm.generate_response,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        response = remove_code_blocks(response)
        if not response.strip():
            facts: list[str] = []
        else:
            try:
                facts = json.loads(response, strict=False).get("facts", [])
            except json.JSONDecodeError:
                facts = json.loads(extract_json(response), strict=False).get("facts", [])
        normalized = normalize_facts(facts)
        candidates = extract_profile_candidates_from_facts(normalized)
        print(f"[memory] mem0 profile facts={normalized[:6]}")
        return candidates
    except Exception as exc:
        print(f"[memory] mem0 profile extraction failed: {exc}")
        return []


async def _log_audit(
    *,
    memory_type: str,
    action: str,
    status: str,
    detail: dict[str, Any],
    user_id: str | None = None,
    session_id: str | None = None,
) -> None:
    if not _store_enabled():
        return
    try:
        await get_memory_store().log_audit(
            memory_type=memory_type,
            action=action,
            status=status,
            detail=detail,
            user_id=user_id,
            session_id=session_id,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[memory] audit log failed: {exc}")


async def _store_profile_candidate(user_id: str, candidate, source_ref: str | None) -> None:
    if _store_enabled():
        await get_memory_store().upsert_profile(
            user_id=user_id,
            category=candidate.category,
            memory_key=candidate.memory_key,
            memory_value=candidate.memory_value,
            content=candidate.content,
            confidence=candidate.confidence,
            source_ref=source_ref,
        )
    if is_mem0_enabled():
        await asyncio.to_thread(
            _get_profile_memory().add,
            candidate.content,
            user_id=user_id,
            infer=False,
            metadata={
                "memory_type": "profile",
                "category": candidate.category,
                "memory_key": candidate.memory_key,
                "memory_value": candidate.memory_value,
            },
        )


async def search_profile_memories(user_id: str, query: str, limit: int = 5) -> list[str]:
    query = (query or "").strip()
    if not query or not user_id.strip():
        return []

    profile_texts: list[str] = []
    if is_mem0_enabled():
        try:
            resp = await asyncio.to_thread(_get_profile_memory().search, query, user_id=user_id, limit=limit)
            profile_texts = _extract_memory_texts(resp)[:limit]
        except Exception as exc:
            print(f"[memory] profile search failed for user_id={user_id}: {exc}")

    if profile_texts or not _store_enabled():
        return profile_texts[:limit]

    rows = await get_memory_store().search_profiles_fallback(user_id=user_id, query=query, limit=limit)
    return [str(row.get("content", "")).strip() for row in rows if str(row.get("content", "")).strip()][:limit]


async def search_episode_memories(user_id: str, query: str, limit: int = 3) -> list[str]:
    if not _store_enabled() or not user_id.strip() or not query.strip():
        return []
    keyword_rows = await get_memory_store().search_episodes(
        user_id=user_id,
        query=query,
        limit=max(limit * 3, 8),
    )
    vector_rows: list[dict[str, Any]] = []
    try:
        vector_rows = await get_episode_vector_store().search(
            user_id=user_id,
            query=query,
            limit=max(limit * 3, 8),
        )
    except Exception as exc:
        print(f"[memory] episode vector search failed for user_id={user_id}: {exc}")

    merged: dict[int, dict[str, Any]] = {}
    for row in keyword_rows:
        episode_id = int(row.get("id") or 0)
        if episode_id <= 0:
            continue
        item = merged.setdefault(
            episode_id,
            {
                "summary": str(row.get("summary", "")).strip(),
                "score": 0.0,
            },
        )
        item["score"] += float(row.get("_score") or 0.0)
    for row in vector_rows:
        episode_id = int(row.get("id") or 0)
        if episode_id <= 0:
            continue
        item = merged.setdefault(
            episode_id,
            {
                "summary": str(row.get("summary", "")).strip(),
                "score": 0.0,
            },
        )
        if not item["summary"]:
            item["summary"] = str(row.get("summary", "")).strip()
        item["score"] += float(row.get("score") or 0.0) * 3.0

    ranked = sorted(merged.values(), key=lambda item: item["score"], reverse=True)
    return [item["summary"] for item in ranked if item["summary"]][:limit]


def _load_env_instructions() -> list[str]:
    raw = (os.getenv("MEMORY_GLOBAL_INSTRUCTIONS") or "").strip()
    if not raw:
        return []
    items = [part.strip() for part in raw.replace("\r", "\n").split("\n") if part.strip()]
    deduped: list[str] = []
    for item in items:
        if item not in deduped:
            deduped.append(item)
    return deduped


async def load_instruction_memories(user_id: str | None = None, agent_id: str | None = None, limit: int = 10) -> list[str]:
    items = _load_env_instructions()
    if _store_enabled():
        scopes = [("global", "", "")]
        if agent_id:
            scopes.append(("agent", agent_id, user_id or ""))
        if user_id:
            scopes.append(("user", user_id, user_id))
        rows = await get_memory_store().list_instructions_for_scopes(scopes)
        for row in rows:
            content = str(row.get("content", "")).strip()
            if content and content not in items:
                items.append(content)
    return items[:limit]


def _trim_prompt_items(items: list[str], *, max_items: int, max_chars: int) -> list[str]:
    trimmed: list[str] = []
    used_chars = 0
    for item in items:
        text = str(item or "").strip()
        if not text:
            continue
        if len(trimmed) >= max_items:
            break
        next_used = used_chars + len(text)
        if trimmed and next_used > max_chars:
            break
        if not trimmed and len(text) > max_chars:
            trimmed.append(text[:max_chars].rstrip())
            break
        trimmed.append(text)
        used_chars = next_used
    return trimmed


async def recall_memory_bundle(user_id: str, session_id: str | None, query: str) -> dict[str, list[str]]:
    max_instruction_items = _env_int("MEMORY_MAX_INSTRUCTION_ITEMS", 8, maximum=32)
    max_profile_items = _env_int("MEMORY_MAX_PROFILE_ITEMS", 4, maximum=16)
    max_episode_items = _env_int("MEMORY_MAX_EPISODE_ITEMS", 2, maximum=8)
    instruction_char_budget = _env_int("MEMORY_MAX_INSTRUCTION_CHARS", 800, maximum=8000)
    profile_char_budget = _env_int("MEMORY_MAX_PROFILE_CHARS", 500, maximum=8000)
    episode_char_budget = _env_int("MEMORY_MAX_EPISODE_CHARS", 700, maximum=8000)

    instructions = await load_instruction_memories(
        user_id=user_id,
        agent_id="copilot-agent",
        limit=max(max_instruction_items * 2, 6),
    )
    profile_rules: list[str] = []
    if _store_enabled():
        recent_profiles = await get_memory_store().list_profiles(
            user_id=user_id,
            limit=10,
            categories=["preference", "environment", "explicit", "preference_note"],
        )
        for row in recent_profiles:
            memory_key = str(row.get("memory_key", "")).strip()
            category = str(row.get("category", "")).strip()
            if memory_key and memory_key not in _PROFILE_PROMPT_KEY_WHITELIST and category != "explicit":
                continue
            content = str(row.get("content", "")).strip()
            if content and content not in profile_rules:
                profile_rules.append(content)
    semantic_profiles = await search_profile_memories(user_id, query, limit=max(max_profile_items, 4))
    profiles = profile_rules[:]
    for item in semantic_profiles:
        if item not in profiles:
            profiles.append(item)
    instructions = _trim_prompt_items(
        instructions,
        max_items=max_instruction_items,
        max_chars=instruction_char_budget,
    )
    profiles = _trim_prompt_items(
        profiles,
        max_items=max_profile_items,
        max_chars=profile_char_budget,
    )
    episodes = _trim_prompt_items(
        await search_episode_memories(user_id, query, limit=max(max_episode_items, 3)),
        max_items=max_episode_items,
        max_chars=episode_char_budget,
    )

    if _store_enabled():
        await get_memory_store().log_recall(
            user_id=user_id,
            session_id=session_id,
            query=query,
            instruction_count=len(instructions),
            profile_count=len(profiles),
            episode_count=len(episodes),
            detail={
                "instructions": instructions,
                "profiles": profiles,
                "episodes": episodes,
            },
        )

    return {
        "instructions": instructions,
        "profiles": profiles,
        "episodes": episodes,
    }


def build_memory_prompt(bundle: dict[str, list[str]]) -> str | None:
    sections: list[str] = []
    instructions = bundle.get("instructions") or []
    profiles = bundle.get("profiles") or []
    episodes = bundle.get("episodes") or []

    if instructions:
        sections.append("系统长期规则：\n" + "\n".join(f"- {item}" for item in instructions))
    if profiles:
        sections.append(
            "用户长期偏好（默认遵守，除非用户当前明确要求覆盖）：\n"
            + "\n".join(f"- {item}" for item in profiles)
        )
    if episodes:
        sections.append(
            "相关历史经验（仅在与当前问题相关时参考）：\n"
            + "\n".join(f"- {item}" for item in episodes)
        )

    if not sections:
        return None
    return (
        "以下是当前请求可用的记忆上下文。"
        "其中用户长期偏好默认生效；如果和用户当前输入冲突，以当前输入为准。\n\n"
        + "\n\n".join(sections)
    )


async def add_turn_messages_to_memory(
    user_id: str,
    messages: list[dict[str, str]],
    *,
    session_id: str | None = None,
) -> None:
    cleaned: list[dict[str, str]] = []
    for msg in messages:
        role = str(msg.get("role", "")).strip().lower()
        content = str(msg.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            cleaned.append({"role": role, "content": content})
    if not cleaned:
        return

    user_message = next((m["content"] for m in cleaned if m["role"] == "user"), "")
    assistant_message = next((m["content"] for m in reversed(cleaned) if m["role"] == "assistant"), "")
    try:
        profile_candidates = await _extract_profile_candidates_with_mem0(user_message)
        if not profile_candidates:
            profile_candidates = extract_profile_candidates(user_message)
        for candidate in profile_candidates:
            await _store_profile_candidate(
                user_id,
                candidate,
                source_ref=f"session:{session_id}" if session_id else None,
            )
        if profile_candidates:
            await _log_audit(
                memory_type="profile",
                action="upsert",
                status="ok",
                detail={"items": [candidate.content for candidate in profile_candidates]},
                user_id=user_id,
                session_id=session_id,
            )

        episode_summary = build_episode_summary(user_message, assistant_message)
        if episode_summary and _store_enabled():
            episode = await get_memory_store().add_episode(
                user_id=user_id,
                session_id=session_id,
                summary=episode_summary,
                source_user_message=user_message[:500],
                source_assistant_message=assistant_message[:1000],
                importance=1,
                metadata={"auto": True},
            )
            try:
                await get_episode_vector_store().upsert_episode(
                    episode_id=int(episode["id"]),
                    user_id=user_id,
                    session_id=session_id,
                    summary=episode_summary,
                    archived=bool(episode.get("archived", False)),
                )
            except Exception as exc:
                print(f"[memory] episode vector upsert failed for user_id={user_id}: {exc}")
            await _log_audit(
                memory_type="episode",
                action="insert",
                status="ok",
                detail={"summary": episode_summary},
                user_id=user_id,
                session_id=session_id,
            )

    except Exception as exc:
        await _log_audit(
            memory_type="runtime",
            action="persist_turn",
            status="error",
            detail={"error": str(exc)},
            user_id=user_id,
            session_id=session_id,
        )
        raise
