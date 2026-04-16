from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx
from pymilvus import CollectionSchema, DataType, FieldSchema, MilvusClient


def _env_int(name: str, default: int, *, minimum: int = 1, maximum: int = 100000) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, min(value, maximum))


def _escape_filter(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


class EpisodeVectorStore:
    def __init__(self) -> None:
        self._uri = (os.getenv("MEMORY_EPISODE_MILVUS_URL") or os.getenv("MEM0_MILVUS_URL") or "").strip()
        self._token = (os.getenv("MEMORY_EPISODE_MILVUS_TOKEN") or os.getenv("MEM0_MILVUS_TOKEN") or "").strip()
        self._db_name = (os.getenv("MEMORY_EPISODE_MILVUS_DB_NAME") or os.getenv("MEM0_MILVUS_DB_NAME") or "").strip()
        self._collection = (os.getenv("MEMORY_EPISODE_MILVUS_COLLECTION") or "memory_episodes").strip()
        self._dims = _env_int(
            "MEMORY_EPISODE_EMBEDDING_DIMS",
            _env_int("MEM0_MILVUS_EMBEDDING_DIMS", 1536, maximum=32768),
            maximum=32768,
        )
        self._embed_model = (
            os.getenv("MEMORY_EPISODE_EMBEDDER_MODEL")
            or os.getenv("MEM0_EMBEDDER_MODEL")
            or "text-embedding-v4"
        ).strip()
        self._embed_base_url = (
            os.getenv("DASHSCOPE_COMPAT_BASE_URL")
            or os.getenv("DASHSCOPE_BASE_URL")
            or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        ).rstrip("/")
        self._api_key = (os.getenv("DASHSCOPE_API_KEY") or "").strip()
        self._search_limit_cap = _env_int("MEMORY_EPISODE_VECTOR_LIMIT_CAP", 20, maximum=100)
        self._client: MilvusClient | None = None
        self._collection_ready = False
        self._enabled = bool(self._uri and self._api_key)

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def upsert_episode(
        self,
        *,
        episode_id: int,
        user_id: str,
        session_id: str | None,
        summary: str,
        archived: bool = False,
    ) -> None:
        if not self.enabled or not summary.strip():
            return
        await self._ensure_collection()
        embedding = (await self._embed_texts([summary]))[0]
        data = {
            "id": int(episode_id),
            "user_id": user_id,
            "session_id": session_id or "",
            "summary": summary,
            "archived": bool(archived),
            "vector": embedding,
        }
        await asyncio.to_thread(self._get_client().upsert, self._collection, [data])

    async def delete_episodes(self, episode_ids: list[int]) -> None:
        cleaned = sorted({int(item) for item in episode_ids if int(item) > 0})
        if not self.enabled or not cleaned:
            return
        await self._ensure_collection()
        await asyncio.to_thread(self._get_client().delete, self._collection, ids=cleaned)

    async def search(self, *, user_id: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
        if not self.enabled or not query.strip():
            return []
        await self._ensure_collection()
        embedding = (await self._embed_texts([query]))[0]
        filter_expr = f'user_id == "{_escape_filter(user_id)}" and archived == false'
        results = await asyncio.to_thread(
            self._get_client().search,
            self._collection,
            data=[embedding],
            filter=filter_expr,
            limit=max(1, min(limit, self._search_limit_cap)),
            output_fields=["summary", "user_id", "session_id", "archived"],
        )
        hits = results[0] if results else []
        items: list[dict[str, Any]] = []
        for hit in hits:
            entity = hit.get("entity") or {}
            summary = str(entity.get("summary", "")).strip()
            if not summary:
                continue
            raw_score = hit.get("distance")
            if raw_score is None:
                raw_score = hit.get("score")
            score = float(raw_score) if isinstance(raw_score, (int, float)) else 0.0
            items.append(
                {
                    "id": int(hit.get("id")),
                    "summary": summary,
                    "score": score,
                    "source": "vector",
                }
            )
        return items

    async def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        payload = {"model": self._embed_model, "input": texts}
        async with httpx.AsyncClient(timeout=float(os.getenv("MEMORY_EPISODE_EMBED_TIMEOUT_SECONDS", "30"))) as client:
            response = await client.post(
                f"{self._embed_base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        response.raise_for_status()
        body = response.json()
        data = body.get("data")
        if not isinstance(data, list) or len(data) != len(texts):
            raise RuntimeError(f"invalid embedding response: {body}")
        vectors: list[list[float]] = []
        for item in data:
            embedding = item.get("embedding")
            if not isinstance(embedding, list):
                raise RuntimeError(f"invalid embedding item: {item}")
            vectors.append([float(v) for v in embedding])
        return vectors

    def _get_client(self) -> MilvusClient:
        if self._client is None:
            self._client = MilvusClient(
                uri=self._uri,
                token=self._token,
                db_name=self._db_name,
            )
        return self._client

    async def _ensure_collection(self) -> None:
        if self._collection_ready or not self.enabled:
            return
        await asyncio.to_thread(self._ensure_collection_sync)
        self._collection_ready = True

    def _ensure_collection_sync(self) -> None:
        client = self._get_client()
        if client.has_collection(self._collection):
            return
        schema = CollectionSchema(
            fields=[
                FieldSchema("id", DataType.INT64, is_primary=True, auto_id=False),
                FieldSchema("user_id", DataType.VARCHAR, max_length=256),
                FieldSchema("session_id", DataType.VARCHAR, max_length=256),
                FieldSchema("summary", DataType.VARCHAR, max_length=8192),
                FieldSchema("archived", DataType.BOOL),
                FieldSchema("vector", DataType.FLOAT_VECTOR, dim=self._dims),
            ],
            description="Episode memory vectors for hybrid recall",
            enable_dynamic_field=False,
        )
        client.create_collection(
            collection_name=self._collection,
            schema=schema,
        )


_store = EpisodeVectorStore()


def get_episode_vector_store() -> EpisodeVectorStore:
    return _store
