from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.auth.auth_context import get_effective_user_id
from app.chat.store import get_chat_store, get_chat_store_status
from app.sandbox import get_sandbox_manager, get_sandbox_store, get_sandbox_store_status

router = APIRouter(prefix="/chat", tags=["chat"])


def _resolve_user_id() -> str:
    return get_effective_user_id()


class CreateSessionRequest(BaseModel):
    title: str | None = Field(default=None, max_length=60)


class StoreStatusResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool | None = None
    error: str | None = None


class ChatSessionResponse(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None = None


class ChatMessageResponse(BaseModel):
    id: int | str
    session_id: str
    user_id: str
    role: str
    content: str
    created_at: datetime


class DeleteSessionResponse(BaseModel):
    ok: bool
    session_id: str


class SandboxSessionResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    session_id: str
    user_id: str
    sandbox_id: str
    workspace_path: str
    status: str
    persistent: bool


@router.get(
    "/status",
    response_model=StoreStatusResponse,
    summary="查看聊天模块状态",
    description="返回聊天存储当前是否启用及错误信息，便于排查 PostgreSQL 连接问题。",
)
def chat_status() -> dict[str, Any]:
    return get_chat_store_status()


@router.post(
    "/sessions",
    response_model=ChatSessionResponse,
    summary="创建会话",
    description="创建一个新的聊天会话，后续前端可使用返回的 session_id 继续对话。",
)
async def create_session(body: CreateSessionRequest) -> dict[str, Any]:
    status = get_chat_store_status()
    if not status.get("enabled"):
        raise HTTPException(status_code=503, detail=status.get("error") or "chat store not enabled")
    return await get_chat_store().create_session(user_id=_resolve_user_id(), title=body.title)


@router.get(
    "/sessions",
    response_model=list[ChatSessionResponse],
    summary="查询会话列表",
    description="返回当前 user_id 下的全部聊天会话，按最近消息时间倒序排列。",
)
async def list_sessions() -> list[dict[str, Any]]:
    status = get_chat_store_status()
    if not status.get("enabled"):
        return []
    return await get_chat_store().list_sessions(user_id=_resolve_user_id())


@router.get(
    "/sessions/{session_id}/messages",
    response_model=list[ChatMessageResponse],
    summary="查询会话消息",
    description="返回指定会话的消息记录，默认按时间正序返回最近 limit 条。",
)
async def list_session_messages(
    session_id: str,
    limit: int = Query(default=200, ge=1, le=1000, description="返回消息条数上限，最大 1000。"),
) -> list[dict[str, Any]]:
    status = get_chat_store_status()
    if not status.get("enabled"):
        return []
    user_id = _resolve_user_id()
    try:
        await get_chat_store().get_session(user_id=user_id, session_id=session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="session not found") from None
    return await get_chat_store().list_messages(user_id=user_id, session_id=session_id, limit=limit)


@router.delete(
    "/sessions/{session_id}",
    response_model=DeleteSessionResponse,
    summary="删除会话",
    description="删除会话、消息记录以及关联的 session sandbox。",
)
async def delete_session(session_id: str) -> dict[str, Any]:
    status = get_chat_store_status()
    if not status.get("enabled"):
        raise HTTPException(status_code=503, detail=status.get("error") or "chat store not enabled")
    user_id = _resolve_user_id()
    try:
        await get_chat_store().delete_session(user_id=user_id, session_id=session_id)
        await get_sandbox_manager().delete_session(user_id=user_id, session_id=session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="session not found") from None
    return {"ok": True, "session_id": session_id}


@router.get(
    "/sessions/{session_id}/sandbox",
    response_model=SandboxSessionResponse,
    summary="查询会话沙箱信息",
    description="返回当前会话绑定的 sandbox/workspace 信息，便于文件和执行环境排查。",
)
async def get_session_sandbox(session_id: str) -> dict[str, Any]:
    user_id = _resolve_user_id()
    try:
        await get_chat_store().get_session(user_id=user_id, session_id=session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="session not found") from None

    sandbox_status = get_sandbox_store_status()
    if not sandbox_status.get("enabled"):
        context = await get_sandbox_manager().ensure_session(user_id=user_id, session_id=session_id)
        return {
            "session_id": context.session_id,
            "user_id": context.user_id,
            "sandbox_id": context.sandbox_id,
            "workspace_path": str(context.workspace_path),
            "status": "active",
            "persistent": False,
        }
    try:
        item = await get_sandbox_store().get_by_session(user_id=user_id, session_id=session_id)
    except KeyError:
        context = await get_sandbox_manager().ensure_session(user_id=user_id, session_id=session_id)
        return {
            "session_id": context.session_id,
            "user_id": context.user_id,
            "sandbox_id": context.sandbox_id,
            "workspace_path": str(context.workspace_path),
            "status": "active",
            "persistent": True,
        }
    item["persistent"] = True
    return item
