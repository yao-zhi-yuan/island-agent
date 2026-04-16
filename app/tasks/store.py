from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import asyncpg
from app.db import AsyncpgStoreRuntime


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TaskStore:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def init_schema(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    session_id TEXT,
                    name TEXT NOT NULL,
                    task_prompt TEXT NOT NULL,
                    schedule_type TEXT NOT NULL,
                    run_at TIMESTAMPTZ,
                    interval_seconds INTEGER,
                    next_run_at TIMESTAMPTZ,
                    status TEXT NOT NULL DEFAULT 'active',
                    last_run_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scheduled_task_runs (
                    id BIGSERIAL PRIMARY KEY,
                    task_id TEXT NOT NULL REFERENCES scheduled_tasks(id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL,
                    scheduled_for TIMESTAMPTZ NOT NULL,
                    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    finished_at TIMESTAMPTZ,
                    status TEXT NOT NULL,
                    output TEXT,
                    error TEXT
                )
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_next_run
                ON scheduled_tasks(status, next_run_at)
                """
            )
            await conn.execute(
                """
                ALTER TABLE scheduled_tasks
                ADD COLUMN IF NOT EXISTS session_id TEXT
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_scheduled_task_runs_task
                ON scheduled_task_runs(task_id, started_at DESC)
                """
            )
            # Recover tasks left in running state after crash/restart.
            await conn.execute(
                "UPDATE scheduled_tasks SET status='active' WHERE status='running'"
            )

    async def create_task(
        self,
        *,
        user_id: str,
        session_id: str | None,
        name: str,
        task_prompt: str,
        schedule_type: str,
        run_at: datetime | None,
        interval_seconds: int | None,
    ) -> dict[str, Any]:
        task_id = str(uuid4())
        now = _utcnow()
        if schedule_type == "once":
            next_run_at = run_at
        else:
            next_run_at = now + timedelta(seconds=interval_seconds or 60)

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO scheduled_tasks(
                    id, user_id, session_id, name, task_prompt,schedule_type,
                    run_at, interval_seconds, next_run_at, status
                )
                VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,'active')
                """,
                task_id,
                user_id,
                session_id,
                name,
                task_prompt,
                schedule_type,
                run_at,
                interval_seconds,
                next_run_at,
            )
        return await self.get_task(user_id=user_id, task_id=task_id)

    async def list_tasks(self, *, user_id: str) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, session_id, name, task_prompt, schedule_type, run_at,
                       interval_seconds, next_run_at, status, last_run_at,
                       created_at, updated_at
                FROM scheduled_tasks
                WHERE user_id=$1
                ORDER BY created_at DESC
                """,
                user_id,
            )
        return [dict(r) for r in rows]

    async def get_task(self, *, user_id: str, task_id: str) -> dict[str, Any]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, session_id, name, task_prompt, schedule_type, run_at,
                       interval_seconds, next_run_at, status, last_run_at,
                       created_at, updated_at
                FROM scheduled_tasks
                WHERE id=$1 AND user_id=$2
                """,
                task_id,
                user_id,
            )
        if row is None:
            raise KeyError("task not found")
        return dict(row)

    async def set_task_status(self, *, user_id: str, task_id: str, status: str) -> None:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE scheduled_tasks
                SET status=$1, updated_at=NOW()
                WHERE id=$2 AND user_id=$3
                """,
                status,
                task_id,
                user_id,
            )
        if result.endswith("0"):
            raise KeyError("task not found")

    async def delete_task(self, *, user_id: str, task_id: str) -> None:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM scheduled_tasks WHERE id=$1 AND user_id=$2",
                task_id,
                user_id,
            )
        if result.endswith("0"):
            raise KeyError("task not found")

    async def list_runs(self, *, user_id: str, task_id: str | None, limit: int) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            if task_id:
                rows = await conn.fetch(
                    """
                    SELECT id, task_id, user_id, scheduled_for, started_at, finished_at, status, output, error
                    FROM scheduled_task_runs
                    WHERE user_id=$1 AND task_id=$2
                    ORDER BY id DESC
                    LIMIT $3
                    """,
                    user_id,
                    task_id,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, task_id, user_id, scheduled_for, started_at, finished_at, status, output, error
                    FROM scheduled_task_runs
                    WHERE user_id=$1
                    ORDER BY id DESC
                    LIMIT $2
                    """,
                    user_id,
                    limit,
                )
        return [dict(r) for r in rows]

    async def claim_due_tasks(self, *, limit: int = 20) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                WITH due AS (
                    SELECT id
                    FROM scheduled_tasks
                    WHERE status='active'
                      AND next_run_at IS NOT NULL
                      AND next_run_at <= NOW()
                    ORDER BY next_run_at ASC
                    LIMIT $1
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE scheduled_tasks t
                SET status='running', updated_at=NOW()
                FROM due
                WHERE t.id = due.id
                RETURNING t.*
                """,
                limit,
            )
        return [dict(r) for r in rows]

    async def create_run(self, *, task: dict[str, Any]) -> int:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO scheduled_task_runs(task_id, user_id, scheduled_for, status)
                VALUES($1,$2,$3,'running')
                RETURNING id
                """,
                task["id"],
                task["user_id"],
                task["next_run_at"],
            )
        return int(row["id"])

    async def finish_run(
        self,
        *,
        run_id: int,
        success: bool,
        output: str | None,
        error: str | None,
    ) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE scheduled_task_runs
                SET status=$1, output=$2, error=$3, finished_at=NOW()
                WHERE id=$4
                """,
                "success" if success else "failed",
                output,
                error,
                run_id,
            )

    async def finalize_task_after_run(self, *, task: dict[str, Any], success: bool) -> None:
        now = _utcnow()
        if task["schedule_type"] == "once":
            next_status = "completed" if success else "failed"
            next_run_at = None
        else:
            interval = int(task.get("interval_seconds") or 60)
            next_status = "active"
            next_run_at = now + timedelta(seconds=interval)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE scheduled_tasks
                SET status=$1, next_run_at=$2, last_run_at=NOW(), updated_at=NOW()
                WHERE id=$3
                """,
                next_status,
                next_run_at,
                task["id"],
            )


async def _init_schema(store: TaskStore) -> None:
    await store.init_schema()


_runtime = AsyncpgStoreRuntime[TaskStore](
    dsn_envs=("TASKS_POSTGRES_DSN", "POSTGRES_DSN"),
    store_factory=TaskStore,
    schema_initializer=_init_schema,
    pool_min_size=1,
    pool_max_size=5,
)


async def init_task_store() -> None:
    await _runtime.init()


async def close_task_store() -> None:
    await _runtime.close()


def get_task_store() -> TaskStore:
    return _runtime.get()


def get_task_store_status() -> dict[str, Any]:
    return _runtime.status()
