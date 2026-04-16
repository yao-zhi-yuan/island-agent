from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import asyncpg

from app.db import AsyncpgStoreRuntime


def _utcnow() -> datetime:
    return datetime.now(UTC)


class SandboxStore:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def init_schema(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS session_sandboxes (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    sandbox_id TEXT NOT NULL UNIQUE,
                    workspace_path TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    last_active_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_session_sandboxes_user_last_active
                ON session_sandboxes(user_id, last_active_at DESC)
                """
            )

    async def get_by_session(self, *, user_id: str, session_id: str) -> dict[str, Any]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT session_id, user_id, sandbox_id, workspace_path, status,
                       created_at, updated_at, last_active_at
                FROM session_sandboxes
                WHERE session_id=$1 AND user_id=$2
                """,
                session_id,
                user_id,
            )
        if row is None:
            raise KeyError("sandbox not found")
        return dict(row)

    async def upsert(
        self,
        *,
        user_id: str,
        session_id: str,
        sandbox_id: str,
        workspace_path: str,
        status: str = "active",
    ) -> dict[str, Any]:
        now = _utcnow()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO session_sandboxes(
                    session_id, user_id, sandbox_id, workspace_path, status, created_at, updated_at, last_active_at
                )
                VALUES($1, $2, $3, $4, $5, $6, $6, $6)
                ON CONFLICT (session_id) DO UPDATE
                SET user_id=EXCLUDED.user_id,
                    status=EXCLUDED.status,
                    updated_at=NOW(),
                    last_active_at=NOW()
                RETURNING session_id, user_id, sandbox_id, workspace_path, status,
                          created_at, updated_at, last_active_at
                """,
                session_id,
                user_id,
                sandbox_id,
                workspace_path,
                status,
                now,
            )
        return dict(row)

    async def touch(self, *, user_id: str, session_id: str, status: str = "active") -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE session_sandboxes
                SET status=$1, updated_at=NOW(), last_active_at=NOW()
                WHERE session_id=$2 AND user_id=$3
                """,
                status,
                session_id,
                user_id,
            )

    async def delete_by_session(self, *, user_id: str, session_id: str) -> dict[str, Any] | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                DELETE FROM session_sandboxes
                WHERE session_id=$1 AND user_id=$2
                RETURNING session_id, user_id, sandbox_id, workspace_path, status,
                          created_at, updated_at, last_active_at
                """,
                session_id,
                user_id,
            )
        return dict(row) if row is not None else None


async def _init_schema(store: SandboxStore) -> None:
    await store.init_schema()


_runtime = AsyncpgStoreRuntime[SandboxStore](
    dsn_envs=("SANDBOX_POSTGRES_DSN", "POSTGRES_DSN"),
    store_factory=SandboxStore,
    schema_initializer=_init_schema,
    pool_min_size=1,
    pool_max_size=5,
)


async def init_sandbox_store() -> None:
    await _runtime.init()


async def close_sandbox_store() -> None:
    await _runtime.close()


def get_sandbox_store() -> SandboxStore:
    return _runtime.get()


def get_sandbox_store_status() -> dict[str, Any]:
    return _runtime.status()
