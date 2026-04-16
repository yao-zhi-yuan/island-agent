from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.auth.auth_context import get_effective_user_id
from app.memory.store import get_memory_store, get_memory_store_status

router = APIRouter(prefix="/memory", tags=["memory"])


def _require_store():
    status = get_memory_store_status()
    if not status.get("enabled"):
        raise HTTPException(status_code=503, detail=status.get("error") or "memory store not enabled")
    return get_memory_store()


def _current_user_id() -> str:
    return get_effective_user_id()


def _normalize_scope(scope_type: str, scope_id: str | None) -> tuple[str, str, str]:
    normalized_type = (scope_type or "global").strip().lower()
    if normalized_type not in {"global", "agent", "user"}:
        raise HTTPException(status_code=400, detail="scope_type must be one of: global, agent, user")
    if normalized_type == "global":
        return "global", "", ""
    if normalized_type == "user":
        return "user", (_current_user_id()).strip(), _current_user_id()
    return "agent", (scope_id or "copilot-agent").strip(), _current_user_id()


class CreateInstructionRequest(BaseModel):
    scope_type: str = Field(default="global")
    scope_id: str | None = Field(default=None, max_length=200)
    content: str = Field(min_length=1, max_length=2000)
    priority: int = Field(default=100, ge=1, le=10000)
    enabled: bool = True


class CreateProfileRequest(BaseModel):
    category: str = Field(default="preference", min_length=1, max_length=100)
    memory_key: str | None = Field(default=None, max_length=200)
    memory_value: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1, max_length=2000)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class StoreStatusResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool | None = None
    error: str | None = None


class MemoryInstructionResponse(BaseModel):
    id: int
    user_id: str
    scope_type: str
    scope_id: str
    content: str
    priority: int
    enabled: bool
    created_at: datetime
    updated_at: datetime


class MemoryProfileResponse(BaseModel):
    id: int
    user_id: str
    category: str
    memory_key: str
    memory_value: str
    content: str
    confidence: float
    source_ref: str | None = None
    created_at: datetime
    updated_at: datetime


class MemoryEpisodeResponse(BaseModel):
    id: int
    user_id: str
    session_id: str | None = None
    summary: str
    source_user_message: str | None = None
    source_assistant_message: str | None = None
    importance: int
    metadata: dict[str, Any]
    archived: bool
    ttl_at: datetime | None = None
    created_at: datetime


class MemoryRecallLogResponse(BaseModel):
    id: int
    user_id: str
    session_id: str | None = None
    query: str
    instruction_count: int
    profile_count: int
    episode_count: int
    detail: dict[str, Any]
    created_at: datetime


class DeleteInstructionResponse(BaseModel):
    ok: bool
    instruction: MemoryInstructionResponse


class DeleteProfileResponse(BaseModel):
    ok: bool
    profile: MemoryProfileResponse


@router.get(
    "/status",
    response_model=StoreStatusResponse,
    summary="查看记忆模块状态",
    description="返回记忆存储当前是否启用及错误信息。",
)
def memory_status() -> dict[str, Any]:
    return get_memory_store_status()


@router.get(
    "/instructions",
    response_model=list[MemoryInstructionResponse],
    summary="查询记忆指令",
    description="按 global/agent/user 作用域查询当前用户可见的 instruction 记忆。",
)
async def list_instructions(
    scope_type: str = Query(default="global", description="作用域类型：global / agent / user。"),
    scope_id: str | None = Query(default=None, description="agent 作用域下的作用域标识。"),
) -> list[dict[str, Any]]:
    store = _require_store()
    normalized_type, normalized_id, owner_user_id = _normalize_scope(scope_type, scope_id)
    return await store.list_instructions(scope_type=normalized_type, scope_id=normalized_id, user_id=owner_user_id)


@router.post(
    "/instructions",
    response_model=MemoryInstructionResponse,
    summary="新增记忆指令",
    description="新增系统级、Agent 级或用户级长期规则。agent/user 级会覆盖同用户的旧规则。",
)
async def create_instruction(body: CreateInstructionRequest) -> dict[str, Any]:
    store = _require_store()
    normalized_type, normalized_id, owner_user_id = _normalize_scope(body.scope_type, body.scope_id)
    item = await store.add_instruction(
        user_id=owner_user_id,
        scope_type=normalized_type,
        scope_id=normalized_id,
        content=body.content.strip(),
        priority=body.priority,
        enabled=body.enabled,
    )
    await store.log_audit(
        memory_type="instruction",
        action="insert",
        status="ok",
        detail={"id": item["id"], "scope_type": normalized_type, "scope_id": normalized_id, "user_id": owner_user_id},
        user_id=_current_user_id(),
        session_id=None,
    )
    return item


@router.delete(
    "/instructions/{instruction_id}",
    response_model=DeleteInstructionResponse,
    summary="删除记忆指令",
    description="删除一条 instruction 记忆记录。",
)
async def delete_instruction(instruction_id: int) -> dict[str, Any]:
    store = _require_store()
    item = await store.delete_instruction(instruction_id=instruction_id, user_id=_current_user_id())
    if item is None:
        raise HTTPException(status_code=404, detail="instruction not found")
    return {"ok": True, "instruction": item}


@router.get(
    "/profiles",
    response_model=list[MemoryProfileResponse],
    summary="查询用户画像",
    description="返回当前 user_id 的 profile 记忆记录。",
)
async def list_profiles(
    limit: int = Query(default=100, ge=1, le=500, description="返回记录条数上限，最大 500。"),
) -> list[dict[str, Any]]:
    store = _require_store()
    return await store.list_profiles(user_id=_current_user_id(), limit=limit)


@router.post(
    "/profiles",
    response_model=MemoryProfileResponse,
    summary="新增用户画像",
    description="手动新增一条 profile 记忆，可用于写入偏好、身份特征或稳定事实。",
)
async def create_profile(body: CreateProfileRequest) -> dict[str, Any]:
    store = _require_store()
    memory_key = (body.memory_key or "").strip()
    if not memory_key:
        digest = hashlib.sha1(f"{body.category}:{body.memory_value}".encode("utf-8")).hexdigest()[:12]
        memory_key = f"manual_{digest}"
    item = await store.add_profile(
        user_id=_current_user_id(),
        category=body.category.strip(),
        memory_key=memory_key,
        memory_value=body.memory_value.strip(),
        content=body.content.strip(),
        confidence=body.confidence,
        source_ref="manual",
    )
    await store.log_audit(
        memory_type="profile",
        action="insert",
        status="ok",
        detail={"id": item["id"], "memory_key": item["memory_key"]},
        user_id=_current_user_id(),
        session_id=None,
    )
    return item


@router.delete(
    "/profiles/{profile_id}",
    response_model=DeleteProfileResponse,
    summary="删除用户画像",
    description="删除指定的 profile 记忆。",
)
async def delete_profile(profile_id: int) -> dict[str, Any]:
    store = _require_store()
    item = await store.delete_profile(user_id=_current_user_id(), profile_id=profile_id)
    if item is None:
        raise HTTPException(status_code=404, detail="profile not found")
    return {"ok": True, "profile": item}


@router.get(
    "/episodes",
    response_model=list[MemoryEpisodeResponse],
    summary="查询经验记忆",
    description="返回当前用户的 episode 记忆，用于查看历史经验摘要。",
)
async def list_episodes(
    limit: int = Query(default=100, ge=1, le=500, description="返回记录条数上限，最大 500。"),
) -> list[dict[str, Any]]:
    store = _require_store()
    return await store.list_episodes(user_id=_current_user_id(), limit=limit)


@router.get(
    "/recalls",
    response_model=list[MemoryRecallLogResponse],
    summary="查询记忆召回日志",
    description="返回运行时记忆召回日志，用于排查模型为什么召回了哪些记忆。",
)
async def list_recalls(
    limit: int = Query(default=100, ge=1, le=500, description="返回日志条数上限，最大 500。"),
) -> list[dict[str, Any]]:
    store = _require_store()
    return await store.list_recall_logs(user_id=_current_user_id(), limit=limit)
