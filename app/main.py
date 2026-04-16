from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse

from ag_ui_langgraph import add_langgraph_fastapi_endpoint

load_dotenv()

from app.agent import ForwardingLangGraphAgent, extract_graph_output_text
from app.auth.auth_context import (
    auth_user_context_middleware,
    bind_user_context,
    get_effective_user_id,
    get_request_user_id,
)
from app.asr.api import router as asr_router
from app.chat.api import router as chat_router
from app.chat.store import close_chat_store, init_chat_store
from app.config.settings import settings
from app.files.api import router as files_router
from app.graph import build_graph

# 1️⃣lighting 第 1 周只接入 store 生命周期和 REST router，不接入 graph/tools/prompt。
from app.lighting import close_lighting_store, init_lighting_store
from app.lighting.api import router as lighting_router

from app.memory.api import router as memory_router
from app.memory import close_memory_store, init_memory_store
from app.memory.compactor import MemoryCompactor
from app.observability import build_langchain_config, propagate_langfuse_attributes, shutdown_langfuse
from app.sandbox import bind_sandbox_context, close_sandbox_store, get_sandbox_manager, init_sandbox_store
from app.tasks.api import router as task_router
from app.tasks.scheduler import TaskScheduler
from app.tasks.store import close_task_store, get_task_store, get_task_store_status, init_task_store

# AI 思考的最大深度，防止卡死。
AGENT_RECURSION_LIMIT = settings.agent_recursion_limit

# 工具函数：拼接网址
def _join_prefix(path: str) -> str:
    prefix = settings.api_prefix.rstrip("/")
    if not prefix:
        return path
    if path == "/":
        return prefix or "/"
    return f"{prefix}{path}"

# 工具函数：启动时打印网址
def _print_startup_endpoints() -> None:
    public_base = (os.getenv("APP_PUBLIC_BASE_URL") or "http://127.0.0.1:8000").rstrip("/")
    docs_path = app.docs_url or "/docs"
    redoc_path = app.redoc_url or "/redoc"
    openapi_path = app.openapi_url or "/openapi.json"
    chat_page_path = _join_prefix("/chat")
    print(f"[startup] Swagger UI: {public_base}{docs_path}")
    print(f"[startup] ReDoc: {public_base}{redoc_path}")
    print(f"[startup] OpenAPI JSON: {public_base}{openapi_path}")
    print(f"[startup] H5 Chat: {public_base}{chat_page_path}")
    print(f"[startup] AGUI Chat Endpoint: {public_base}{settings.chat_endpoint_path}")

# 生命周期
@asynccontextmanager
async def lifespan(app: FastAPI):
    graph, cleanup = await build_graph()
    agent = ForwardingLangGraphAgent(
        name="copilot-agent",
        graph=graph,
        config=build_langchain_config({"recursion_limit": AGENT_RECURSION_LIMIT}),
    )
    app.state.agent = agent

    #数据库初始化
    await init_chat_store()
    await init_memory_store()
    await init_sandbox_store()
    await init_task_store()
    # 1️⃣lifespan 是 FastAPI 的应用生命周期；这里初始化 lighting store，启动时建表并准备连接池。
    await init_lighting_store()
    # 用户记忆模型压缩器
    memory_compactor = MemoryCompactor()
    await memory_compactor.start()

    scheduler: TaskScheduler | None = None
    if get_task_store_status().get("enabled"):

        async def run_task_with_agent(task: dict[str, Any]) -> str:
            session_id = str(task.get("session_id") or f"task-{task['id']}")
            sandbox_context = await get_sandbox_manager().ensure_session(
                user_id=str(task["user_id"]),
                session_id=session_id,
            )
            config: dict[str, Any] = build_langchain_config({"recursion_limit": AGENT_RECURSION_LIMIT})
            if session_id:
                config["configurable"] = {"thread_id": session_id}

            with (
                bind_user_context(str(task["user_id"])),
                bind_sandbox_context(sandbox_context),
                propagate_langfuse_attributes(
                    user_id=str(task["user_id"]),
                    session_id=session_id,
                    trace_name="scheduled-task",
                    metadata={"trigger": "task", "task_id": str(task["id"])},
                ),
            ):
                result = await graph.ainvoke(
                    {"messages": [{"role": "user", "content": str(task["task_prompt"])}]},
                    config=config,
                )
                output = extract_graph_output_text(result)
                return output

        scheduler = TaskScheduler(get_task_store(), run_task_with_agent)
        await scheduler.start()

    add_langgraph_fastapi_endpoint(app, agent=agent, path=settings.chat_endpoint_path)
    _print_startup_endpoints()

    try:
        yield
    finally:
        if scheduler is not None:
            await scheduler.stop()
        await memory_compactor.stop()
        await close_chat_store()
        await close_memory_store()
        await close_sandbox_store()
        await close_task_store()
        # 1️⃣关闭连接池，避免应用退出时留下数据库连接。
        await close_lighting_store()
        shutdown_langfuse()
        await cleanup()

app = FastAPI(
    title="Copilot Agent API",
    description=(
        "通用 Agent Harness 的 REST/OpenAPI 文档。\n\n"
        f"- Swagger UI: `{_join_prefix('/docs')}`\n"
        f"- ReDoc: `{_join_prefix('/redoc')}`\n"
        f"- OpenAPI JSON: `{_join_prefix('/openapi.json')}`\n\n"
        "说明：会话、记忆、任务、ASR、文件上传等 REST 接口适合直接联调；"
        "AGUI 聊天入口是协议型/流式接口，更适合按协议说明接入。"
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url=_join_prefix("/docs"),
    redoc_url=_join_prefix("/redoc"),
    openapi_url=_join_prefix("/openapi.json"),
    swagger_ui_parameters={"defaultModelsExpandDepth": -1, "displayRequestDuration": True},
    openapi_tags=[
        {"name": "system", "description": "系统与调试接口，例如健康检查和当前用户信息。"},
        {"name": "chat", "description": "会话与消息管理接口。"},
        {"name": "memory", "description": "长期记忆、用户画像、记忆回溯查询接口。"},
        {"name": "tasks", "description": "定时任务创建、查询、暂停、恢复、删除接口。"},
        {"name": "lighting", "description": "照明设计项目与 ProjectState 管理接口。"},# 1️⃣
        {"name": "asr", "description": "语音转文字接口，接收音频文件并返回识别文本。"},
        {"name": "files", "description": "文件上传接口，目前用于 Excel 文件上传。"},
    ],
)
app.middleware("http")(auth_user_context_middleware)

app.include_router(asr_router, prefix=settings.api_router_prefix)
app.include_router(task_router, prefix=settings.api_router_prefix)
app.include_router(chat_router, prefix=settings.api_router_prefix)
app.include_router(memory_router, prefix=settings.api_router_prefix)
app.include_router(files_router, prefix=settings.api_router_prefix)
# 1️⃣注册后，lighting 的三个最小闭环接口会出现在 /api/lighting/... 下。
app.include_router(lighting_router, prefix=settings.api_router_prefix)
@app.get(_join_prefix("/"), tags=["system"], summary="根接口", description="服务根路径探活接口。")
def read_root() -> dict[str, str]:
    return {"message": "Hello from FastAPI"}


@app.get(_join_prefix("/health"), tags=["system"], summary="健康检查", description="用于容器或网关探测服务是否存活。")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get(_join_prefix("/chat"), include_in_schema=False)
def chat_page() -> FileResponse:
    frontend_path = Path(__file__).resolve().parent / "frontend" / "index.html"
    return FileResponse(frontend_path)


@app.get(
    _join_prefix("/debug/whoami"),
    tags=["system"],
    summary="查看当前请求身份",
    description="返回请求中解析到的 user_id 与系统实际生效的 user_id，便于前后端联调鉴权。",
)
def debug_whoami() -> dict[str, str | None]:
    user_id = get_request_user_id()
    claim_name = os.getenv("JWT_USER_ID_CLAIM", "user_id")
    return {
        "user_id": user_id,
        "effective_user_id": get_effective_user_id(),
        "claim_name": claim_name,
    }
