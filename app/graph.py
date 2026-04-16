from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from pathlib import Path

from deepagents import create_deep_agent
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.redis import AsyncRedisSaver

from app.config.mcp_config import mcp_config_prod
from app.config.settings import settings
from app.lighting.tools import (
    create_lighting_project_from_requirement,
    generate_layout_for_project,
    select_fixtures_for_project,
    update_lighting_project_requirement,
)
from app.model.llm import build_qwen_llm
from app.prompts.prompt import system_prompt
from app.sandbox import SessionSandboxBackend
from app.tasks.tools import create_scheduled_task, delete_scheduled_task, query_scheduled_tasks
from app.tools import (
    get_current_sandbox_info,
    install_skill_package,
    list_installed_skills,
    list_uploaded_excel_files,
    parse_excel_file,
)


async def _build_tools() -> list[BaseTool | Callable]:
    tools: list[BaseTool | Callable] = [
        get_current_sandbox_info,
        install_skill_package,
        list_installed_skills,
        list_uploaded_excel_files,
        parse_excel_file,
        create_scheduled_task,
        delete_scheduled_task,
        query_scheduled_tasks,
        # 第 3 周第二批：接入“初步灯具族选型”工具。
        # 第 4 周第二批：仅接入 Layout Tool，不扩展布局能力，也不接 BOM/report/报价。
        create_lighting_project_from_requirement,
        update_lighting_project_requirement,
        select_fixtures_for_project,
        generate_layout_for_project,
    ]
    if mcp_config_prod:
        static_client = MultiServerMCPClient(mcp_config_prod, tool_name_prefix=True)
        tools.extend(await static_client.get_tools())
    return tools


def _create_agent_graph(
    tools: list[BaseTool | Callable],
    checkpointer: MemorySaver | AsyncRedisSaver,
    skills_sources: list[str],
) -> object:
    graph = create_deep_agent(
        model=build_qwen_llm(settings.agent_model),
        checkpointer=checkpointer,
        system_prompt=system_prompt,
        tools=tools,
        skills=skills_sources,
        backend=SessionSandboxBackend(),
        subagents=None,#拓展子智能体，智能体隔离
    )
    return graph.with_config({"recursion_limit": settings.agent_recursion_limit})


def _normalize_skill_source(source: str, app_root: Path) -> str:
    raw = (source or "").strip()
    if not raw:
        return ""
    if raw.startswith("/"):
        candidate = Path(raw).expanduser()
        if candidate.exists():
            resolved = candidate.resolve()
            try:
                rel = resolved.relative_to(app_root)
                return f"/{rel.as_posix()}"
            except ValueError:
                pass
        return raw.rstrip("/") or "/"
    return f"/{raw.strip('/')}"


def _resolve_skill_sources(app_root: Path) -> list[str]:
    raw = (os.getenv("DEEPAGENT_SKILLS") or "").strip()
    candidates = raw.split(",") if raw else ["/skills"]
    normalized = [_normalize_skill_source(item, app_root) for item in candidates]
    deduped: list[str] = []
    for source in normalized:
        if source and source not in deduped:
            deduped.append(source)
    return deduped or ["/skills"]


async def build_graph() -> tuple[object, Callable[[], Awaitable[None]]]:
    """
    Build graph and return an async cleanup callback.
    If REDIS_URL is set, keep AsyncRedisSaver open for the app lifetime.
    """
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        saver_ctx = AsyncRedisSaver.from_conn_string(
            redis_url=redis_url,
            ttl={"default_ttl": 60 * 60},
        )
        checkpointer = await saver_ctx.__aenter__()
        await checkpointer.setup()

        async def _cleanup_checkpointer() -> None:
            await saver_ctx.__aexit__(None, None, None)
    else:
        checkpointer = MemorySaver()

        async def _cleanup_checkpointer() -> None:
            return None

    tools = await _build_tools()
    app_root = Path(__file__).resolve().parent
    skills_sources = _resolve_skill_sources(app_root)
    graph = _create_agent_graph(tools, checkpointer, skills_sources)

    async def _cleanup() -> None:
        await _cleanup_checkpointer()

    return graph, _cleanup
