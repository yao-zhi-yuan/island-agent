from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import asyncpg

from app.db import AsyncpgStoreRuntime
from app.lighting.schemas import ProjectState


# store 层负责和数据库打交道；API 层不直接写 SQL。
# 这样后续 Agent tools、REST API、验证脚本都可以复用同一套持久化逻辑。
def _utcnow() -> datetime:
    return datetime.now(UTC)


def _normalize_title(title: str | None, fallback_content: str | None = None) -> str:
    raw = (title or "").strip()
    if not raw:
        raw = (fallback_content or "").strip() # 去掉前后空格、换行
    if not raw: # 备用内容也为空
        return "未命名设计项目"
    return raw[:120]

# 入库
def _project_state_to_json(project_state: ProjectState | dict[str, Any]) -> str:
    # JSONB 是 PostgreSQL 的 JSON 类型，适合保存会持续演进的项目状态。
    # 写入前先通过 ProjectState 校验，避免把不符合契约的数据直接塞进库里。
    if isinstance(project_state, ProjectState):
        data = project_state.model_dump(mode="json")
    else:
        data = ProjectState.model_validate(project_state).model_dump(mode="json")
    return json.dumps(data, ensure_ascii=False)

# 读库
def _parse_project_state(value: Any) -> dict[str, Any]:
    # asyncpg 读 JSONB 时通常已经是 dict；这里兼容字符串形态，便于测试或未来迁移。
    if value is None:
        return ProjectState().model_dump(mode="json")
    if isinstance(value, str):
        value = json.loads(value)
    return ProjectState.model_validate(value).model_dump(mode="json")


class LightingStore:
    """lighting 业务的数据库访问对象。

    当前只实现 Step 1A 必需的三件事：创建项目、查询项目、更新 ProjectState。
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    async def init_schema(self) -> None:
        async with self.pool.acquire() as conn:
            # Step 1A 只建一张项目主表。
            # project_state 用 JSONB 承载多阶段状态，避免第一周就拆出过多业务表。
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS lighting_projects (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    session_id TEXT,
                    title TEXT NOT NULL,
                    project_state JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
            # 按 user_id 建索引，是为了后续按当前用户查询项目时保持隔离和性能。
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_lighting_projects_user_updated
                ON lighting_projects(user_id, updated_at DESC)
                """
            )
            

    async def create_project(
        self,
        *,
        user_id: str,
        session_id: str | None,
        title: str | None,
        initial_requirement: str | None = None,
    ) -> dict[str, Any]:
        """创建照明设计项目，并生成第一份 ProjectState。"""

        project_id = str(uuid4())
        now = _utcnow()
        state = ProjectState()
        if initial_requirement and initial_requirement.strip():
            # 先把原始需求放进 requirement_spec，后续 Agent/Tool 可以在此基础上继续结构化。
            state.requirement_spec["initial_requirement"] = initial_requirement.strip()
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO lighting_projects(
                    id, user_id, session_id, title, project_state, created_at, updated_at
                )
                VALUES($1, $2, $3, $4, $5::jsonb, $6, $6)
                """,
                project_id,
                user_id,
                session_id,
                _normalize_title(title, initial_requirement),
                _project_state_to_json(state),
                now,
            )
        return await self.get_project(user_id=user_id, project_id=project_id)

    async def get_project(self, *, user_id: str, project_id: str) -> dict[str, Any]:
        """按 user_id + project_id 查询项目。

        user_id 隔离很重要：同一个 project_id 只有所属用户能读到，其他用户会表现为 not found。
        """

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, session_id, title, project_state, created_at, updated_at
                FROM lighting_projects
                WHERE id=$1 AND user_id=$2
                """,
                project_id,
                user_id,
            )
        if row is None:
            # 这里抛 KeyError，交给 API 层翻译成 HTTP 404，和现有 chat/task store 风格一致。
            raise KeyError("lighting project not found")
        item = dict(row)
        item["project_state"] = _parse_project_state(item.get("project_state"))
        return item

    async def update_project_state(
        self,
        *,
        user_id: str,
        project_id: str,
        project_state: ProjectState,
    ) -> dict[str, Any]:
        """持久化更新 ProjectState。

        PATCH state 是第一周闭环的核心接口：它证明项目状态可以被外部更新并完整读回。
        """

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE lighting_projects
                SET project_state=$1::jsonb, updated_at=NOW()
                WHERE id=$2 AND user_id=$3
                RETURNING id, user_id, session_id, title, project_state, created_at, updated_at
                """,
                _project_state_to_json(project_state),
                project_id,
                user_id,
            )
        if row is None:
            raise KeyError("lighting project not found")
        item = dict(row)
        item["project_state"] = _parse_project_state(item.get("project_state"))
        return item


async def _init_schema(store: LightingStore) -> None:
    await store.init_schema()


# runtime 是仓库已有的 store 生命周期管理器。
# 它统一处理 DSN 读取、连接池创建、schema 初始化和模块启停状态，lighting 直接复用，不重复造轮子。
_runtime = AsyncpgStoreRuntime[LightingStore](
    dsn_envs=("LIGHTING_POSTGRES_DSN", "POSTGRES_DSN"),
    store_factory=LightingStore,
    schema_initializer=_init_schema,
    pool_min_size=1,
    pool_max_size=5,
)


async def init_lighting_store() -> None:
    await _runtime.init()


async def close_lighting_store() -> None:
    await _runtime.close()


def get_lighting_store() -> LightingStore:
    return _runtime.get()


def get_lighting_store_status() -> dict[str, Any]:
    return _runtime.status()
