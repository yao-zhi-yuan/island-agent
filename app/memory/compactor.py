from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime, timedelta
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.memory.episode_vector import get_episode_vector_store
from app.memory.store import get_memory_store, get_memory_store_status
from app.model.llm import build_qwen_llm


def _env_int(name: str, default: int, *, minimum: int = 1, maximum: int = 100000) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, min(value, maximum))


def _extract_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                text = item.strip()
                if text:
                    parts.append(text)
                continue
            if isinstance(item, dict):
                text = str(item.get("text", "")).strip()
                if text:
                    parts.append(text)
        return "\n".join(parts).strip()
    return str(content or "").strip()


class MemoryCompactor:
    def __init__(self) -> None:
        self.interval_seconds = _env_int("MEMORY_COMPACTION_INTERVAL_SECONDS", 3600)
        self.min_items = _env_int("MEMORY_COMPACTION_MIN_ITEMS", 8, maximum=100)
        self.min_age_hours = _env_int("MEMORY_COMPACTION_MIN_AGE_HOURS", 12, maximum=24 * 365)
        self.max_source_items = _env_int("MEMORY_COMPACTION_MAX_SOURCE_ITEMS", 12, maximum=100)
        self.source_user_limit = _env_int("MEMORY_COMPACTION_USER_LIMIT", 200, maximum=5000)
        self.summary_max_chars = _env_int("MEMORY_COMPACTION_SUMMARY_MAX_CHARS", 400, maximum=4000)
        self.archive_ttl_days = _env_int("MEMORY_COMPACTION_ARCHIVE_TTL_DAYS", 30, maximum=3650)
        self.enabled = (os.getenv("MEMORY_COMPACTION_ENABLED", "1") or "1") != "0"
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._model = None

    async def start(self) -> None:
        if not self.enabled or self._task is not None:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop(), name="memory-compactor")

    async def stop(self) -> None:
        task = self._task
        if task is None:
            return
        self._stop_event.set()
        try:
            await task
        finally:
            self._task = None

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                await self.run_once()
            except Exception as exc:  # noqa: BLE001
                print(f"[memory] compaction loop failed: {exc}")
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.interval_seconds)
            except TimeoutError:
                continue

    async def run_once(self) -> None:
        if not self.enabled or not get_memory_store_status().get("enabled"):
            return
        users = await get_memory_store().list_active_episode_users(limit=self.source_user_limit)
        for user_id in users:
            if self._stop_event.is_set():
                return
            await self._compact_user(user_id)

    async def _compact_user(self, user_id: str) -> None:
        store = get_memory_store()
        candidates = await store.list_episode_compaction_candidates(
            user_id=user_id,
            limit=self.max_source_items,
            min_age_hours=self.min_age_hours,
        )
        filtered = [row for row in candidates if not bool((row.get("metadata") or {}).get("auto_compacted"))]
        if len(filtered) < self.min_items:
            return

        summary = await self._summarize_episodes(filtered)
        if not summary:
            return

        source_ids = [int(row["id"]) for row in filtered if row.get("id") is not None]
        ttl_at = datetime.now(UTC) + timedelta(days=self.archive_ttl_days) if self.archive_ttl_days > 0 else None

        episode = await store.add_episode(
            user_id=user_id,
            session_id=None,
            summary=summary[: self.summary_max_chars].strip(),
            source_user_message=None,
            source_assistant_message=None,
            importance=2,
            metadata={
                "auto_compacted": True,
                "model": "qwen3-max",
                "source_episode_ids": source_ids,
            },
        )
        try:
            await get_episode_vector_store().upsert_episode(
                episode_id=int(episode["id"]),
                user_id=user_id,
                session_id=None,
                summary=str(episode["summary"]),
                archived=False,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[memory] compacted episode vector upsert failed: {exc}")
        archived_count = await store.archive_episodes(user_id=user_id, episode_ids=source_ids, ttl_at=ttl_at)
        if archived_count > 0:
            try:
                await get_episode_vector_store().delete_episodes(source_ids)
            except Exception as exc:  # noqa: BLE001
                print(f"[memory] archived episode vector delete failed: {exc}")
        await store.log_audit(
            user_id=user_id,
            session_id=None,
            memory_type="episode",
            action="compact",
            status="ok",
            detail={
                "summary_id": episode.get("id"),
                "source_count": len(source_ids),
                "archived_count": archived_count,
                "model": "qwen3-max",
            },
        )
        print(
            "[memory] compacted episodes",
            {
                "user_id": user_id,
                "source_count": len(source_ids),
                "archived_count": archived_count,
                "summary_id": episode.get("id"),
            },
        )

    async def _summarize_episodes(self, candidates: list[dict[str, Any]]) -> str | None:
        model = self._get_model()
        if model is None:
            return None

        bullet_lines: list[str] = []
        for idx, row in enumerate(candidates, start=1):
            created_at = row.get("created_at")
            ts = created_at.isoformat() if hasattr(created_at, "isoformat") else ""
            bullet_lines.append(f"{idx}. time={ts} summary={str(row.get('summary', '')).strip()}")
        prompt = (
            "请将以下多条历史经验压缩为一条可跨会话复用的长期经验。\n"
            "要求：\n"
            "1. 只保留稳定、可复用、低噪声的信息；\n"
            "2. 删除重复表达和一次性细节；\n"
            "3. 不要编造；\n"
            "4. 输出纯文本，2到5条短句，总长度不超过300字。\n\n"
            "待压缩经验：\n"
            + "\n".join(bullet_lines)
        )
        try:
            response = await model.ainvoke(
                [
                    SystemMessage(content="你是一个长期记忆压缩器，负责把多条历史经验压缩成可复用的高质量摘要。"),
                    HumanMessage(content=prompt),
                ]
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[memory] compaction model failed: {exc}")
            return None

        text = _extract_text_content(getattr(response, "content", response))
        return text or None

    def _get_model(self):  # noqa: ANN001
        if self._model is not None:
            return self._model
        try:
            self._model = build_qwen_llm("qwen3-max")
        except Exception as exc:  # noqa: BLE001
            print(f"[memory] compaction model init failed: {exc}")
            return None
        return self._model
