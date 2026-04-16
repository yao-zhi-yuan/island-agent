from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.auth.auth_context import get_effective_user_id
from app.lighting.schemas import (
    CreateLightingProjectRequest,
    LightingProjectResponse,
    UpdateProjectStateRequest,
)
from app.lighting.store import get_lighting_store, get_lighting_store_status

# router 是 FastAPI 的路由分组；这里把 lighting 相关接口统一挂到 /api/lighting 下。
router = APIRouter(prefix="/lighting", tags=["lighting"])


def _require_store():
    # 如果没有配置 LIGHTING_POSTGRES_DSN/POSTGRES_DSN，store 会处于 disabled。
    # 这里直接返回 503，让调用方知道是后端存储未启用，而不是业务数据不存在。
    status = get_lighting_store_status()
    if not status.get("enabled"):
        raise HTTPException(status_code=503, detail=status.get("error") or "lighting store not enabled")
    return get_lighting_store()


def _current_user_id() -> str:
    # 当前仓库通过请求上下文解析 user_id；lighting 依赖它做项目级数据隔离。
    return get_effective_user_id()


@router.post(
    "/projects",
    response_model=LightingProjectResponse,
    summary="创建照明设计项目",
    description="创建一个照明设计项目，并初始化可持久化的 ProjectState。",
)
async def create_lighting_project(body: CreateLightingProjectRequest) -> dict[str, Any]:
    # 创建项目只初始化最小状态，不在这里做选型、布局或校验，避免 Step 1A 越界。
    store = _require_store()
    return await store.create_project(
        user_id=_current_user_id(),
        session_id=body.session_id,
        title=body.title,
        initial_requirement=body.initial_requirement,
    )


@router.get(
    "/projects/{project_id}",
    response_model=LightingProjectResponse,
    summary="查询照明设计项目",
    description="查询当前用户下的单个照明设计项目和 ProjectState。",
)
async def get_lighting_project(project_id: str) -> dict[str, Any]:
    store = _require_store()
    try:
        return await store.get_project(user_id=_current_user_id(), project_id=project_id)
    except KeyError:
        # 不区分“项目不存在”和“不是当前用户的项目”，避免泄露其他用户项目是否存在。
        raise HTTPException(status_code=404, detail="lighting project not found") from None


@router.patch(
    "/projects/{project_id}/state",
    response_model=LightingProjectResponse,
    summary="更新照明设计项目状态",
    description="持久化更新单个照明设计项目的 ProjectState。",
)
async def update_lighting_project_state(
    project_id: str,
    body: UpdateProjectStateRequest,
) -> dict[str, Any]:
    # 这是第 1 周最小闭环的关键接口：证明 ProjectState 可以被更新并持久化。
    store = _require_store()
    try:
        return await store.update_project_state(
            user_id=_current_user_id(),
            project_id=project_id,
            project_state=body.project_state,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="lighting project not found") from None
