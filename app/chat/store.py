from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import asyncpg

from app.db import AsyncpgStoreRuntime


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _normalize_title(title: str | None, fallback_content: str | None = None) -> str:
    raw = (title or "").strip()
    if not raw:
        raw = (fallback_content or "").strip()
    if not raw:
        return "新会话"
    return raw[:60]


class ChatStore:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def init_schema(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    last_message_at TIMESTAMPTZ
                )
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id BIGSERIAL PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_last_msg
                ON chat_sessions(user_id, last_message_at DESC, updated_at DESC)
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id
                ON chat_messages(session_id, id ASC)
                """
            )

    async def create_session(self, *, user_id: str, title: str | None = None) -> dict[str, Any]:
        session_id = str(uuid4())
        now = _utcnow()
        normalized = _normalize_title(title)
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO chat_sessions(id, user_id, title, created_at, updated_at)
                VALUES($1, $2, $3, $4, $4)
                """,
                session_id,
                user_id,
                normalized,
                now,
            )
        return await self.get_session(user_id=user_id, session_id=session_id)

    async def get_session(self, *, user_id: str, session_id: str) -> dict[str, Any]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, title, created_at, updated_at, last_message_at
                FROM chat_sessions
                WHERE id=$1 AND user_id=$2
                """,
                session_id,
                user_id,
            )
        if row is None:
            raise KeyError("session not found")
        return dict(row)

    async def ensure_session(self, *, user_id: str, session_id: str, title_hint: str | None = None) -> dict[str, Any]:
        async with self.pool.acquire() as conn:
            exists = await conn.fetchrow(
                "SELECT id, title FROM chat_sessions WHERE id=$1 AND user_id=$2",
                session_id,
                user_id,
            )
            if exists is None:
                title = _normalize_title(None, title_hint)
                now = _utcnow()
                await conn.execute(
                    """
                    INSERT INTO chat_sessions(id, user_id, title, created_at, updated_at)
                    VALUES($1, $2, $3, $4, $4)
                    """,
                    session_id,
                    user_id,
                    title,
                    now,
                )
            elif (exists["title"] == "新会话") and title_hint:
                await conn.execute(
                    """
                    UPDATE chat_sessions
                    SET title=$1, updated_at=NOW()
                    WHERE id=$2 AND user_id=$3
                    """,
                    _normalize_title(None, title_hint),
                    session_id,
                    user_id,
                )
        return await self.get_session(user_id=user_id, session_id=session_id)

    async def list_sessions(self, *, user_id: str) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, title, created_at, updated_at, last_message_at
                FROM chat_sessions
                WHERE user_id=$1
                ORDER BY COALESCE(last_message_at, created_at) DESC
                """,
                user_id,
            )
        return [dict(r) for r in rows]

    async def list_messages(self, *, user_id: str, session_id: str, limit: int = 200) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, session_id, user_id, role, content, created_at
                FROM chat_messages
                WHERE user_id=$1 AND session_id=$2
                ORDER BY id DESC
                LIMIT $3
                """,
                user_id,
                session_id,
                max(1, min(limit, 1000)),
            )
        return [dict(r) for r in reversed(rows)]

    async def delete_session(self, *, user_id: str, session_id: str) -> None:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM chat_sessions WHERE id=$1 AND user_id=$2",
                session_id,
                user_id,
            )
        if result.endswith("0"):
            raise KeyError("session not found")

    async def append_message(
        self,
        *,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        dedupe_tail: bool = False,
    ) -> dict[str, Any]:
        now = _utcnow()
        async with self.pool.acquire() as conn:
            if dedupe_tail:
                tail = await conn.fetchrow(
                    """
                    SELECT id, session_id, user_id, role, content, created_at
                    FROM chat_messages
                    WHERE session_id=$1 AND user_id=$2
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    session_id,
                    user_id,
                )
                if tail is not None:
                    same = str(tail["role"]) == role and str(tail["content"]) == content
                    if same:
                        return dict(tail)

            row = await conn.fetchrow(
                """
                INSERT INTO chat_messages(session_id, user_id, role, content, created_at)
                VALUES($1, $2, $3, $4, $5)
                RETURNING id, session_id, user_id, role, content, created_at
                """,
                session_id,
                user_id,
                role,
                content,
                now,
            )
            await conn.execute(
                """
                UPDATE chat_sessions
                SET last_message_at=$1, updated_at=$1
                WHERE id=$2 AND user_id=$3
                """,
                now,
                session_id,
                user_id,
            )
        message = dict(row)
        return message


async def _init_schema(store: ChatStore) -> None:
    await store.init_schema()


_runtime = AsyncpgStoreRuntime[ChatStore](
    dsn_envs=("CHAT_POSTGRES_DSN", "POSTGRES_DSN"),
    store_factory=ChatStore,
    schema_initializer=_init_schema,
    pool_min_size=1,
    pool_max_size=5,
)


async def init_chat_store() -> None:
    await _runtime.init()


async def close_chat_store() -> None:
    await _runtime.close()


def get_chat_store() -> ChatStore:
    return _runtime.get()


def get_chat_store_status() -> dict[str, Any]:
    return _runtime.status()
