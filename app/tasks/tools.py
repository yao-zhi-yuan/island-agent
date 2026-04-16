from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Literal

from app.auth.auth_context import get_effective_user_id
from app.sandbox import get_sandbox_context
from app.tasks.store import get_task_store, get_task_store_status


def _require_user_id() -> str:
    return get_effective_user_id()


def _parse_run_at(run_at_iso: str | None) -> datetime | None:
    if not run_at_iso:
        return None
    parsed = datetime.fromisoformat(run_at_iso.replace("Z", "+00:00"))
    return parsed.astimezone(UTC)


def _current_session_id() -> str | None:
    context = get_sandbox_context()
    if context is None:
        return None
    return context.session_id


async def create_scheduled_task(
    name: str,
    task_prompt: str,
    schedule_type: Literal["once", "interval"] = "once",
    run_at_iso: str | None = None,
    interval_seconds: int | None = None,
    session_id: str | None = None,
) -> str:
    """
    Create a scheduled task for current user.

    Args:
        name: Task name.
        task_prompt: Task execution prompt/content.
        schedule_type: "once" or "interval".
        run_at_iso: Required when schedule_type is "once", ISO datetime.
        interval_seconds: Required when schedule_type is "interval", >=10.
        session_id: Optional chat session id for reusing the same sandbox/workspace.
    """
    status = get_task_store_status()
    if not status.get("enabled"):
        return json.dumps(
            {"ok": False, "error": "task store not enabled, configure TASKS_POSTGRES_DSN/POSTGRES_DSN"},
            ensure_ascii=False,
        )

    user_id = _require_user_id()
    if schedule_type == "once":
        run_at = _parse_run_at(run_at_iso)
        if run_at is None:
            raise ValueError("run_at_iso is required for once tasks")
        if run_at <= datetime.now(UTC):
            raise ValueError("run_at_iso must be in the future")
        interval = None
    else:
        if interval_seconds is None or interval_seconds < 10:
            raise ValueError("interval_seconds must be >= 10 for interval tasks")
        run_at = None
        interval = interval_seconds

    task = await get_task_store().create_task(
        user_id=user_id,
        session_id=session_id or _current_session_id(),
        name=name,
        task_prompt=task_prompt,
        schedule_type=schedule_type,
        run_at=run_at,
        interval_seconds=interval,
    )
    return json.dumps({"ok": True, "task": task}, ensure_ascii=False, default=str)


async def delete_scheduled_task(task_id: str) -> str:
    """Delete a task by id for current user."""
    status = get_task_store_status()
    if not status.get("enabled"):
        return json.dumps(
            {"ok": False, "error": "task store not enabled, configure TASKS_POSTGRES_DSN/POSTGRES_DSN"},
            ensure_ascii=False,
        )
    user_id = _require_user_id()
    try:
        await get_task_store().delete_task(user_id=user_id, task_id=task_id)
        return json.dumps({"ok": True, "task_id": task_id}, ensure_ascii=False)
    except KeyError:
        return json.dumps({"ok": False, "error": "task not found", "task_id": task_id}, ensure_ascii=False)


async def query_scheduled_tasks(
    mode: Literal["tasks", "runs", "task_runs"] = "tasks",
    task_id: str | None = None,
    limit: int = 50,
) -> str:
    """
    Query scheduled tasks or run logs for current user.

    mode:
    - "tasks": list tasks
    - "runs": list all run logs
    - "task_runs": list run logs for one task_id
    """
    status = get_task_store_status()
    if not status.get("enabled"):
        return json.dumps(
            {"ok": False, "error": "task store not enabled, configure TASKS_POSTGRES_DSN/POSTGRES_DSN"},
            ensure_ascii=False,
        )
    user_id = _require_user_id()
    limit = max(1, min(limit, 200))
    store = get_task_store()

    if mode == "tasks":
        data = await store.list_tasks(user_id=user_id)
        return json.dumps({"ok": True, "mode": mode, "items": data}, ensure_ascii=False, default=str)

    if mode == "runs":
        data = await store.list_runs(user_id=user_id, task_id=None, limit=limit)
        return json.dumps({"ok": True, "mode": mode, "items": data}, ensure_ascii=False, default=str)

    if not task_id:
        raise ValueError("task_id is required when mode is 'task_runs'")
    data = await store.list_runs(user_id=user_id, task_id=task_id, limit=limit)
    return json.dumps({"ok": True, "mode": mode, "task_id": task_id, "items": data}, ensure_ascii=False, default=str)
