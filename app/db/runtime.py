from __future__ import annotations

import os
from typing import Any, Awaitable, Callable, Generic, TypeVar

import asyncpg

T = TypeVar("T")


class AsyncpgStoreRuntime(Generic[T]):
    """Generic lifecycle manager for asyncpg-backed stores."""

    def __init__(
        self,
        *,
        dsn_envs: tuple[str, ...],
        store_factory: Callable[[asyncpg.Pool], T],
        schema_initializer: Callable[[T], Awaitable[None]],
        pool_min_size: int = 1,
        pool_max_size: int = 5,
    ) -> None:
        self._dsn_envs = dsn_envs
        self._store_factory = store_factory
        self._schema_initializer = schema_initializer
        self._pool_min_size = pool_min_size
        self._pool_max_size = pool_max_size
        self._store: T | None = None
        self._status: dict[str, Any] = {"enabled": False, "ok": None, "error": None}

    def _resolve_dsn(self) -> str | None:
        for key in self._dsn_envs:
            value = os.getenv(key)
            if value:
                return value
        return None

    async def init(self) -> None:
        dsn = self._resolve_dsn()
        if not dsn:
            self._status.update(
                {
                    "enabled": False,
                    "ok": None,
                    "error": f"{'/'.join(self._dsn_envs)} not configured",
                }
            )
            return

        try:
            pool = await asyncpg.create_pool(
                dsn=dsn,
                min_size=self._pool_min_size,
                max_size=self._pool_max_size,
            )
            store = self._store_factory(pool)
            await self._schema_initializer(store)
            self._store = store
            self._status.update({"enabled": True, "ok": True, "error": None})
        except Exception as exc:
            self._store = None
            self._status.update({"enabled": False, "ok": False, "error": str(exc)})
            raise

    async def close(self) -> None:
        if self._store is None:
            return
        pool = getattr(self._store, "pool", None)
        if pool is not None:
            await pool.close()
        self._store = None

    def get(self) -> T:
        if self._store is None:
            raise RuntimeError("store not initialized")
        return self._store

    def status(self) -> dict[str, Any]:
        return dict(self._status)
