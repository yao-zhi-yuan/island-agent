from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

import asyncpg

from app.db import AsyncpgStoreRuntime


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[\u4e00-\u9fff]+|[A-Za-z0-9_./:-]+", (text or "").lower()) if token}


def _parse_json_object(value: Any) -> dict[str, Any]:
    """把数据库 JSONB 字段统一转成 dict。

    asyncpg 在不同 JSON codec 配置下，JSONB 可能返回 dict，也可能返回 JSON 字符串。
    API 响应模型要求这些字段是 dict，所以 store 层在出库时先做兼容转换。
    """

    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    return {}


class MemoryStore:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def init_schema(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_instructions (
                    id BIGSERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL DEFAULT '',
                    scope_type TEXT NOT NULL DEFAULT 'global',
                    scope_id TEXT NOT NULL DEFAULT '',
                    content TEXT NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 100,
                    enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            await conn.execute("ALTER TABLE memory_instructions ADD COLUMN IF NOT EXISTS user_id TEXT NOT NULL DEFAULT ''")
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_profiles (
                    id BIGSERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    memory_key TEXT NOT NULL,
                    memory_value TEXT NOT NULL,
                    content TEXT NOT NULL,
                    confidence DOUBLE PRECISION NOT NULL DEFAULT 1.0,
                    source_ref TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE(user_id, category, memory_key)
                )
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_episodes (
                    id BIGSERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    session_id TEXT,
                    summary TEXT NOT NULL,
                    source_user_message TEXT,
                    source_assistant_message TEXT,
                    importance INTEGER NOT NULL DEFAULT 1,
                    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    archived BOOLEAN NOT NULL DEFAULT FALSE,
                    ttl_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            await conn.execute(
                "ALTER TABLE memory_episodes ADD COLUMN IF NOT EXISTS archived BOOLEAN NOT NULL DEFAULT FALSE"
            )
            await conn.execute("ALTER TABLE memory_episodes ADD COLUMN IF NOT EXISTS ttl_at TIMESTAMPTZ")
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_audit_logs (
                    id BIGSERIAL PRIMARY KEY,
                    user_id TEXT,
                    session_id TEXT,
                    memory_type TEXT NOT NULL,
                    action TEXT NOT NULL,
                    status TEXT NOT NULL,
                    detail JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_recall_logs (
                    id BIGSERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    session_id TEXT,
                    query TEXT NOT NULL,
                    instruction_count INTEGER NOT NULL DEFAULT 0,
                    profile_count INTEGER NOT NULL DEFAULT 0,
                    episode_count INTEGER NOT NULL DEFAULT 0,
                    detail JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_memory_profiles_user_updated
                ON memory_profiles(user_id, updated_at DESC)
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_memory_episodes_user_created
                ON memory_episodes(user_id, created_at DESC)
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_memory_instructions_scope_priority
                ON memory_instructions(user_id, scope_type, scope_id, priority ASC)
                """
            )

    async def list_instructions(
        self,
        *,
        scope_type: str = "global",
        scope_id: str = "",
        user_id: str = "",
    ) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, scope_type, scope_id, content, priority, enabled, created_at, updated_at
                FROM memory_instructions
                WHERE enabled=TRUE AND scope_type=$1 AND scope_id=$2 AND user_id=$3
                ORDER BY priority ASC, id ASC
                """,
                scope_type,
                scope_id,
                user_id,
            )
        return [dict(row) for row in rows]

    async def list_instructions_for_scopes(self, scopes: list[tuple[str, str, str]]) -> list[dict[str, Any]]:
        if not scopes:
            return []
        clauses: list[str] = []
        args: list[Any] = []
        arg_index = 1
        for scope_type, scope_id, user_id in scopes:
            clauses.append(
                f"(scope_type=${arg_index} AND scope_id=${arg_index + 1} AND user_id=${arg_index + 2})"
            )
            args.extend([scope_type, scope_id, user_id])
            arg_index += 3
        where = " OR ".join(clauses)
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT id, user_id, scope_type, scope_id, content, priority, enabled, created_at, updated_at
                FROM memory_instructions
                WHERE enabled=TRUE AND ({where})
                ORDER BY priority ASC, id ASC
                """,
                *args,
            )
        return [dict(row) for row in rows]

    async def add_instruction(
        self,
        *,
        user_id: str,
        scope_type: str,
        scope_id: str,
        content: str,
        priority: int = 100,
        enabled: bool = True,
    ) -> dict[str, Any]:
        async with self.pool.acquire() as conn:
            if scope_type in {"agent", "user"}:
                await conn.execute(
                    """
                    DELETE FROM memory_instructions
                    WHERE user_id=$1 AND scope_type=$2
                    """,
                    user_id,
                    scope_type,
                )
            row = await conn.fetchrow(
                """
                INSERT INTO memory_instructions(user_id, scope_type, scope_id, content, priority, enabled)
                VALUES($1, $2, $3, $4, $5, $6)
                RETURNING id, user_id, scope_type, scope_id, content, priority, enabled, created_at, updated_at
                """,
                user_id,
                scope_type,
                scope_id,
                content,
                priority,
                enabled,
            )
        item = dict(row)
        item["metadata"] = _parse_json_object(item.get("metadata"))
        return item

    async def delete_instruction(self, *, instruction_id: int, user_id: str = "") -> dict[str, Any] | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                DELETE FROM memory_instructions
                WHERE id=$1 AND (user_id=$2 OR user_id='')
                RETURNING id, user_id, scope_type, scope_id, content, priority, enabled, created_at, updated_at
                """,
                instruction_id,
                user_id,
            )
        return dict(row) if row is not None else None

    async def upsert_profile(
        self,
        *,
        user_id: str,
        category: str,
        memory_key: str,
        memory_value: str,
        content: str,
        confidence: float,
        source_ref: str | None = None,
    ) -> dict[str, Any]:
        now = _utcnow()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO memory_profiles(
                    user_id, category, memory_key, memory_value, content, confidence, source_ref, created_at, updated_at
                )
                VALUES($1, $2, $3, $4, $5, $6, $7, $8, $8)
                ON CONFLICT(user_id, category, memory_key) DO UPDATE
                SET memory_value=EXCLUDED.memory_value,
                    content=EXCLUDED.content,
                    confidence=EXCLUDED.confidence,
                    source_ref=EXCLUDED.source_ref,
                    updated_at=EXCLUDED.updated_at
                RETURNING id, user_id, category, memory_key, memory_value, content, confidence, source_ref, created_at, updated_at
                """,
                user_id,
                category,
                memory_key,
                memory_value,
                content,
                confidence,
                source_ref,
                now,
            )
        return dict(row)

    async def list_profiles(
        self,
        *,
        user_id: str,
        limit: int = 100,
        categories: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        where = "WHERE user_id=$1"
        args: list[Any] = [user_id]
        if categories:
            where += " AND category = ANY($2::text[])"
            args.append(categories)
            limit_arg_index = 3
        else:
            limit_arg_index = 2
        args.append(max(1, min(limit, 500)))
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT id, user_id, category, memory_key, memory_value, content, confidence, source_ref, created_at, updated_at
                FROM memory_profiles
                {where}
                ORDER BY updated_at DESC, id DESC
                LIMIT ${limit_arg_index}
                """,
                *args,
            )
        return [dict(row) for row in rows]

    async def add_profile(
        self,
        *,
        user_id: str,
        category: str,
        memory_key: str,
        memory_value: str,
        content: str,
        confidence: float = 1.0,
        source_ref: str | None = None,
    ) -> dict[str, Any]:
        return await self.upsert_profile(
            user_id=user_id,
            category=category,
            memory_key=memory_key,
            memory_value=memory_value,
            content=content,
            confidence=confidence,
            source_ref=source_ref,
        )

    async def delete_profile(self, *, user_id: str, profile_id: int) -> dict[str, Any] | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                DELETE FROM memory_profiles
                WHERE id=$1 AND user_id=$2
                RETURNING id, user_id, category, memory_key, memory_value, content, confidence, source_ref, created_at, updated_at
                """,
                profile_id,
                user_id,
            )
        return dict(row) if row is not None else None

    async def search_profiles_fallback(self, *, user_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        tokens = list(_tokenize(query))[:8]
        if not tokens:
            return await self.list_profiles(user_id=user_id, limit=limit)
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, category, memory_key, memory_value, content, confidence, source_ref, created_at, updated_at
                FROM memory_profiles
                WHERE user_id=$1
                ORDER BY updated_at DESC, id DESC
                LIMIT 200
                """,
                user_id,
            )
        scored: list[tuple[float, dict[str, Any]]] = []
        for row in rows:
            item = dict(row)
            haystack = " ".join(
                [
                    str(item.get("category", "")),
                    str(item.get("memory_key", "")),
                    str(item.get("memory_value", "")),
                    str(item.get("content", "")),
                ]
            ).lower()
            score = 0.0
            for token in tokens:
                if token in haystack:
                    score += 1.0
            if score <= 0:
                continue
            score += float(item.get("confidence") or 0)
            scored.append((score, item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored[:limit]]

    async def add_episode(
        self,
        *,
        user_id: str,
        session_id: str | None,
        summary: str,
        source_user_message: str | None,
        source_assistant_message: str | None,
        importance: int = 1,
        metadata: dict[str, Any] | None = None,
        archived: bool = False,
        ttl_at: datetime | None = None,
    ) -> dict[str, Any]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO memory_episodes(
                    user_id, session_id, summary, source_user_message, source_assistant_message,
                    importance, metadata, archived, ttl_at
                )
                VALUES($1, $2, $3, $4, $5, $6, $7::jsonb, $8, $9)
                RETURNING id, user_id, session_id, summary, source_user_message, source_assistant_message,
                          importance, metadata, archived, ttl_at, created_at
                """,
                user_id,
                session_id,
                summary,
                source_user_message,
                source_assistant_message,
                importance,
                json.dumps(metadata or {}, ensure_ascii=False),
                archived,
                ttl_at,
            )
        item = dict(row)
        item["metadata"] = _parse_json_object(item.get("metadata"))
        return item

    async def search_episodes(self, *, user_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        tokens = _tokenize(query)
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, session_id, summary, source_user_message, source_assistant_message,
                       importance, metadata, archived, ttl_at, created_at
                FROM memory_episodes
                WHERE user_id=$1
                  AND archived=FALSE
                  AND (ttl_at IS NULL OR ttl_at > NOW())
                ORDER BY created_at DESC
                LIMIT 200
                """,
                user_id,
            )
        scored: list[tuple[float, dict[str, Any]]] = []
        for row in rows:
            item = dict(row)
            item["metadata"] = _parse_json_object(item.get("metadata"))
            haystack = " ".join(
                [
                    str(item.get("summary", "")),
                    str(item.get("source_user_message", "")),
                    str(item.get("source_assistant_message", "")),
                ]
            ).lower()
            score = float(item.get("importance") or 0)
            if query and query.lower() in haystack:
                score += 4.0
            if tokens:
                for token in tokens:
                    if token in haystack:
                        score += 1.0
            age_seconds = max((_utcnow() - item["created_at"]).total_seconds(), 1.0)
            score += min(2.0, 86400.0 / age_seconds)
            if score <= 0:
                continue
            item["_score"] = score
            scored.append((score, item))
        scored.sort(key=lambda pair: (pair[0], pair[1]["created_at"]), reverse=True)
        return [item for _, item in scored[:limit]]

    async def list_episodes(self, *, user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, session_id, summary, source_user_message, source_assistant_message,
                       importance, metadata, archived, ttl_at, created_at
                FROM memory_episodes
                WHERE user_id=$1
                ORDER BY created_at DESC, id DESC
                LIMIT $2
                """,
                user_id,
                max(1, min(limit, 500)),
            )
        items = [dict(row) for row in rows]
        for item in items:
            item["metadata"] = _parse_json_object(item.get("metadata"))
        return items

    async def list_active_episode_users(self, *, limit: int = 200) -> list[str]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT user_id
                FROM memory_episodes
                WHERE archived=FALSE AND (ttl_at IS NULL OR ttl_at > NOW())
                ORDER BY user_id ASC
                LIMIT $1
                """,
                max(1, min(limit, 1000)),
            )
        return [str(row["user_id"]) for row in rows if row.get("user_id")]

    async def list_episode_compaction_candidates(
        self,
        *,
        user_id: str,
        limit: int = 20,
        min_age_hours: int = 12,
    ) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, session_id, summary, source_user_message, source_assistant_message,
                       importance, metadata, archived, ttl_at, created_at
                FROM memory_episodes
                WHERE user_id=$1
                  AND archived=FALSE
                  AND (ttl_at IS NULL OR ttl_at > NOW())
                  AND created_at <= NOW() - ($2::text || ' hours')::interval
                ORDER BY created_at DESC, id DESC
                LIMIT $3
                """,
                user_id,
                str(max(1, min(min_age_hours, 24 * 365))),
                max(1, min(limit, 200)),
            )
        items = [dict(row) for row in rows]
        for item in items:
            item["metadata"] = _parse_json_object(item.get("metadata"))
        return items

    async def archive_episodes(
        self,
        *,
        user_id: str,
        episode_ids: list[int],
        ttl_at: datetime | None = None,
    ) -> int:
        cleaned_ids = sorted({int(item) for item in episode_ids if int(item) > 0})
        if not cleaned_ids:
            return 0
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE memory_episodes
                SET archived=TRUE, ttl_at=COALESCE($3, ttl_at)
                WHERE user_id=$1 AND id = ANY($2::bigint[])
                """,
                user_id,
                cleaned_ids,
                ttl_at,
            )
        return int(str(result).split()[-1])

    async def list_recall_logs(self, *, user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, session_id, query, instruction_count, profile_count, episode_count, detail, created_at
                FROM memory_recall_logs
                WHERE user_id=$1
                ORDER BY created_at DESC, id DESC
                LIMIT $2
                """,
                user_id,
                max(1, min(limit, 500)),
            )
        items = [dict(row) for row in rows]
        for item in items:
            item["detail"] = _parse_json_object(item.get("detail"))
        return items

    async def log_audit(
        self,
        *,
        memory_type: str,
        action: str,
        status: str,
        detail: dict[str, Any],
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO memory_audit_logs(user_id, session_id, memory_type, action, status, detail)
                VALUES($1, $2, $3, $4, $5, $6::jsonb)
                """,
                user_id,
                session_id,
                memory_type,
                action,
                status,
                json.dumps(detail, ensure_ascii=False),
            )

    async def log_recall(
        self,
        *,
        user_id: str,
        session_id: str | None,
        query: str,
        instruction_count: int,
        profile_count: int,
        episode_count: int,
        detail: dict[str, Any],
    ) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO memory_recall_logs(
                    user_id, session_id, query, instruction_count, profile_count, episode_count, detail
                )
                VALUES($1, $2, $3, $4, $5, $6, $7::jsonb)
                """,
                user_id,
                session_id,
                query,
                instruction_count,
                profile_count,
                episode_count,
                json.dumps(detail, ensure_ascii=False),
            )


async def _init_schema(store: MemoryStore) -> None:
    await store.init_schema()


_runtime = AsyncpgStoreRuntime[MemoryStore](
    dsn_envs=("MEMORY_POSTGRES_DSN", "POSTGRES_DSN"),
    store_factory=MemoryStore,
    schema_initializer=_init_schema,
    pool_min_size=1,
    pool_max_size=5,
)


async def init_memory_store() -> None:
    await _runtime.init()


async def close_memory_store() -> None:
    await _runtime.close()


def get_memory_store() -> MemoryStore:
    return _runtime.get()


def get_memory_store_status() -> dict[str, Any]:
    return _runtime.status()
