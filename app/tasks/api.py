from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.auth.auth_context import get_request_user_id
from app.tasks.store import get_task_store, get_task_store_status

router = APIRouter(prefix="/tasks", tags=["tasks"])


class CreateTaskRequest(BaseModel):
    session_id: str | None = None
    name: str = Field(min_length=1, max_length=100)
    task_prompt: str = Field(min_length=1, max_length=4000)
    schedule_type: Literal["once", "interval"] = "once"
    run_at: datetime | None = None
    interval_seconds: int | None = Field(default=None, ge=10, le=7 * 24 * 3600)


def _require_user_id() -> str:
    user_id = get_request_user_id()
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing authenticated user_id")
    return user_id


class StoreStatusResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool | None = None
    error: str | None = None


class TaskResponse(BaseModel):
    id: str
    user_id: str
    session_id: str | None = None
    name: str
    task_prompt: str
    schedule_type: str
    run_at: datetime | None = None
    interval_seconds: int | None = None
    next_run_at: datetime | None = None
    status: str
    last_run_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class TaskRunResponse(BaseModel):
    id: int
    task_id: str
    user_id: str
    scheduled_for: datetime
    started_at: datetime
    finished_at: datetime | None = None
    status: str
    output: str | None = None
    error: str | None = None


class OkResponse(BaseModel):
    ok: bool


@router.get(
    "/status",
    response_model=StoreStatusResponse,
    summary="查看任务模块状态",
    description="返回定时任务存储当前是否启用及错误信息。",
)
def task_module_status() -> dict[str, Any]:
    return get_task_store_status()


@router.post(
    "",
    response_model=TaskResponse,
    summary="创建定时任务",
    description="创建一次性任务或间隔任务。一次性任务必须传 run_at，间隔任务必须传 interval_seconds。",
)
async def create_task(body: CreateTaskRequest) -> dict[str, Any]:
    user_id = _require_user_id()
    if body.schedule_type == "once":
        if body.run_at is None:
            raise HTTPException(status_code=400, detail="run_at is required for once tasks")
        run_at = body.run_at.astimezone(UTC)
        if run_at <= datetime.now(UTC):
            raise HTTPException(status_code=400, detail="run_at must be in the future")
        interval_seconds = None
    else:
        if body.interval_seconds is None:
            raise HTTPException(status_code=400, detail="interval_seconds is required for interval tasks")
        run_at = None
        interval_seconds = body.interval_seconds

    store = get_task_store()
    return await store.create_task(
        user_id=user_id,
        session_id=body.session_id,
        name=body.name,
        task_prompt=body.task_prompt,
        schedule_type=body.schedule_type,
        run_at=run_at,
        interval_seconds=interval_seconds,
    )


@router.get(
    "",
    response_model=list[TaskResponse],
    summary="查询任务列表",
    description="返回当前用户的全部定时任务。",
)
async def list_tasks() -> list[dict[str, Any]]:
    user_id = _require_user_id()
    return await get_task_store().list_tasks(user_id=user_id)


@router.get(
    "/runs",
    response_model=list[TaskRunResponse],
    summary="查询全部任务执行记录",
    description="返回当前用户最近的任务执行记录。",
)
async def list_runs(
    limit: int = Query(default=50, ge=1, le=200, description="返回执行记录条数上限，最大 200。"),
) -> list[dict[str, Any]]:
    user_id = _require_user_id()
    return await get_task_store().list_runs(user_id=user_id, task_id=None, limit=limit)


@router.get(
    "/{task_id}/runs",
    response_model=list[TaskRunResponse],
    summary="查询单个任务执行记录",
    description="返回指定任务最近的执行记录。",
)
async def list_task_runs(
    task_id: str,
    limit: int = Query(default=50, ge=1, le=200, description="返回执行记录条数上限，最大 200。"),
) -> list[dict[str, Any]]:
    user_id = _require_user_id()
    return await get_task_store().list_runs(user_id=user_id, task_id=task_id, limit=limit)


@router.post(
    "/{task_id}/pause",
    response_model=TaskResponse,
    summary="暂停任务",
    description="将任务状态切换为 paused，暂停后不会继续调度执行。",
)
async def pause_task(task_id: str) -> dict[str, Any]:
    user_id = _require_user_id()
    store = get_task_store()
    try:
        await store.set_task_status(user_id=user_id, task_id=task_id, status="paused")
        return await store.get_task(user_id=user_id, task_id=task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found") from None


@router.post(
    "/{task_id}/resume",
    response_model=TaskResponse,
    summary="恢复任务",
    description="将任务状态切换为 active，使其恢复调度。",
)
async def resume_task(task_id: str) -> dict[str, Any]:
    user_id = _require_user_id()
    store = get_task_store()
    try:
        await store.set_task_status(user_id=user_id, task_id=task_id, status="active")
        return await store.get_task(user_id=user_id, task_id=task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found") from None


@router.delete(
    "/{task_id}",
    response_model=OkResponse,
    summary="删除任务",
    description="删除指定任务及其执行记录。",
)
async def delete_task(task_id: str) -> dict[str, Any]:
    user_id = _require_user_id()
    store = get_task_store()
    try:
        await store.delete_task(user_id=user_id, task_id=task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found") from None
    return {"ok": True}
