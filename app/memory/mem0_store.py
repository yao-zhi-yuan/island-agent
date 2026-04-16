from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from langgraph.store.base import (
    BaseStore,
    GetOp,
    Item,
    ListNamespacesOp,
    MatchCondition,
    Op,
    PutOp,
    Result,
    SearchItem,
    SearchOp,
)
from mem0 import Memory
from app.auth.auth_context import get_request_user_id


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        raw = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return _now_utc()
    return _now_utc()


def _apply_operator(value: Any, operator: str, op_value: Any) -> bool:
    if operator == "$eq":
        return value == op_value
    if operator == "$gt":
        return float(value) > float(op_value)
    if operator == "$gte":
        return float(value) >= float(op_value)
    if operator == "$lt":
        return float(value) < float(op_value)
    if operator == "$lte":
        return float(value) <= float(op_value)
    if operator == "$ne":
        return value != op_value
    raise ValueError(f"Unsupported operator: {operator}")


def _compare_values(item_value: Any, filter_value: Any) -> bool:
    if isinstance(filter_value, dict):
        if any(k.startswith("$") for k in filter_value):
            return all(
                _apply_operator(item_value, op_key, op_value)
                for op_key, op_value in filter_value.items()
            )
        if not isinstance(item_value, dict):
            return False
        return all(_compare_values(item_value.get(k), v) for k, v in filter_value.items())
    if isinstance(filter_value, (list, tuple)):
        return (
            isinstance(item_value, (list, tuple))
            and len(item_value) == len(filter_value)
            and all(_compare_values(iv, fv) for iv, fv in zip(item_value, filter_value, strict=False))
        )
    return item_value == filter_value


def _does_match(match_condition: MatchCondition, key: tuple[str, ...]) -> bool:
    match_type = match_condition.match_type
    path = match_condition.path
    if len(key) < len(path):
        return False

    if match_type == "prefix":
        for k_elem, p_elem in zip(key, path, strict=False):
            if p_elem == "*":
                continue
            if k_elem != p_elem:
                return False
        return True
    if match_type == "suffix":
        for k_elem, p_elem in zip(reversed(key), reversed(path), strict=False):
            if p_elem == "*":
                continue
            if k_elem != p_elem:
                return False
        return True
    raise ValueError(f"Unsupported match type: {match_type}")


def _load_json_env(name: str) -> dict[str, Any]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{name} must be valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{name} must decode to a JSON object.")
    return parsed


def _build_local_mem0_config() -> dict[str, Any]:
    vector_config = {
        "url": os.getenv("MEM0_MILVUS_URL", "http://localhost:19530"),
        "collection_name": os.getenv("MEM0_MILVUS_COLLECTION", "mem0"),
        "embedding_model_dims": int(os.getenv("MEM0_MILVUS_EMBEDDING_DIMS", "1536")),
        "db_name": os.getenv("MEM0_MILVUS_DB_NAME", ""),
        # mem0 telemetry re-creates Milvus config and passes token explicitly.
        # Keep token as string to avoid pydantic rejecting None.
        "token": os.getenv("MEM0_MILVUS_TOKEN", ""),
    }

    llm_provider = os.getenv("MEM0_LLM_PROVIDER", "openai")
    embedder_provider = os.getenv("MEM0_EMBEDDER_PROVIDER", "openai")

    llm_config = _load_json_env("MEM0_LLM_CONFIG_JSON")
    embedder_config = _load_json_env("MEM0_EMBEDDER_CONFIG_JSON")

    if llm_provider == "openai":
        llm_config.setdefault("api_key", os.getenv("DASHSCOPE_API_KEY"))
        llm_config.setdefault("openai_base_url", os.getenv("DASHSCOPE_BASE_URL"))
        llm_config.setdefault("model", os.getenv("MEM0_LLM_MODEL", "gpt-4.1-nano-2025-04-14"))
    if embedder_provider == "openai":
        embedder_config.setdefault("api_key", os.getenv("DASHSCOPE_API_KEY"))
        embedder_config.setdefault("openai_base_url", os.getenv("DASHSCOPE_BASE_URL"))
        embedder_config.setdefault("model", os.getenv("MEM0_EMBEDDER_MODEL", "text-embedding-v4"))
        embedder_config.setdefault("embedding_dims", vector_config["embedding_model_dims"])

    # history_db_path = os.getenv("MEM0_HISTORY_DB_PATH", os.path.expanduser("~/.mem0/history.db"))

    return {
        "vector_store": {"provider": "milvus", "config": vector_config},
        "llm": {"provider": llm_provider, "config": llm_config},
        "embedder": {"provider": embedder_provider, "config": embedder_config},
        "version": "v1.1",
    }
        # "history_db_path": history_db_path,
        # "graph_store": {"provider": "neo4j", "config": None},
        # Keep graph disabled for minimal local setup.


class Mem0Store(BaseStore):
    """LangGraph BaseStore adapter backed by local mem0 + Milvus."""

    def __init__(
        self,
        *,
        user_id: str | None = None,
        agent_id: str | None = None,
        run_id: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self._scope_user_id = user_id or os.getenv("MEM0_USER_ID", "default-user")
        self._scope_agent_id = agent_id or os.getenv("MEM0_AGENT_ID")
        self._scope_run_id = run_id or os.getenv("MEM0_RUN_ID")
        self._memory = Memory.from_config(config or _build_local_mem0_config())

    def _scope_kwargs(self) -> dict[str, str]:
        payload: dict[str, str] = {}
        current_user_id = get_request_user_id() or self._scope_user_id
        if current_user_id:
            payload["user_id"] = current_user_id
        if self._scope_agent_id:
            payload["agent_id"] = self._scope_agent_id
        if self._scope_run_id:
            payload["run_id"] = self._scope_run_id
        return payload

    @staticmethod
    def _meta(namespace: tuple[str, ...], key: str, value: dict[str, Any]) -> dict[str, Any]:
        return {"lg_namespace": list(namespace), "lg_key": key, "lg_value": value}

    @staticmethod
    def _extract_records(resp: dict[str, Any] | list[Any] | None) -> list[dict[str, Any]]:
        if resp is None:
            return []
        if isinstance(resp, list):
            return [r for r in resp if isinstance(r, dict)]
        results = resp.get("results")
        if isinstance(results, list):
            return [r for r in results if isinstance(r, dict)]
        if isinstance(resp, dict) and ("id" in resp or "memory_id" in resp):
            return [resp]
        return []

    @staticmethod
    def _record_id(record: dict[str, Any]) -> str:
        rid = record.get("id") or record.get("memory_id")
        return str(rid) if rid else ""

    def _record_to_item(self, record: dict[str, Any]) -> Item:
        metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
        namespace_raw = metadata.get("lg_namespace")
        namespace = tuple(str(x) for x in namespace_raw) if isinstance(namespace_raw, list) else tuple()
        key = str(metadata.get("lg_key") or self._record_id(record))
        value = metadata.get("lg_value")
        if not isinstance(value, dict):
            fallback_text = record.get("memory") or record.get("text") or ""
            value = {"text": fallback_text}

        created_at = _parse_dt(record.get("created_at"))
        updated_at = _parse_dt(record.get("updated_at"))
        return Item(
            value=value,
            key=key,
            namespace=namespace,
            created_at=created_at,
            updated_at=updated_at,
        )

    def _find_by_namespace_key(self, namespace: tuple[str, ...], key: str) -> list[dict[str, Any]]:
        records = self._extract_records(self._memory.get_all(limit=1000, **self._scope_kwargs()))
        target_ns = list(namespace)
        return [
            r
            for r in records
            if isinstance(r.get("metadata"), dict)
            and r["metadata"].get("lg_namespace") == target_ns
            and r["metadata"].get("lg_key") == key
        ]

    def _matches_search(self, item: Item, op: SearchOp) -> bool:
        if len(item.namespace) < len(op.namespace_prefix):
            return False
        if item.namespace[: len(op.namespace_prefix)] != op.namespace_prefix:
            return False
        if not op.filter:
            return True
        return all(_compare_values(item.value.get(k), v) for k, v in op.filter.items())

    def _search_sync(self, op: SearchOp) -> list[SearchItem]:
        if op.query:
            records = self._extract_records(
                self._memory.search(op.query, limit=op.offset + op.limit, **self._scope_kwargs())
            )
        else:
            records = self._extract_records(
                self._memory.get_all(limit=max(op.offset + op.limit, 100), **self._scope_kwargs())
            )

        matched: list[SearchItem] = []
        for record in records:
            item = self._record_to_item(record)
            if not self._matches_search(item, op):
                continue
            score_raw = record.get("score")
            score = float(score_raw) if isinstance(score_raw, (int, float)) else None
            matched.append(
                SearchItem(
                    namespace=item.namespace,
                    key=item.key,
                    value=item.value,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                    score=score,
                )
            )
        return matched[op.offset : op.offset + op.limit]

    def _list_namespaces_sync(self, op: ListNamespacesOp) -> list[tuple[str, ...]]:
        records = self._extract_records(self._memory.get_all(limit=1000, **self._scope_kwargs()))
        namespaces = {
            tuple(str(x) for x in r["metadata"].get("lg_namespace", []))
            for r in records
            if isinstance(r.get("metadata"), dict)
        }
        filtered = list(namespaces)
        if op.match_conditions:
            filtered = [
                ns for ns in filtered if all(_does_match(condition, ns) for condition in op.match_conditions)
            ]
        if op.max_depth is not None:
            filtered = sorted({ns[: op.max_depth] for ns in filtered})
        else:
            filtered = sorted(filtered)
        return filtered[op.offset : op.offset + op.limit]

    def _put_sync(self, op: PutOp) -> None:
        existing = self._find_by_namespace_key(op.namespace, op.key)
        for record in existing:
            rid = self._record_id(record)
            if rid:
                self._memory.delete(rid)

        if op.value is None:
            return

        text = json.dumps(op.value)
        metadata = self._meta(op.namespace, op.key, op.value)
        self._memory.add(text, infer=False, metadata=metadata, **self._scope_kwargs())

    def batch(self, ops: Iterable[Op]) -> list[Result]:
        results: list[Result] = []
        put_ops: dict[tuple[tuple[str, ...], str], PutOp] = {}

        for op in ops:
            if isinstance(op, GetOp):
                matches = self._find_by_namespace_key(op.namespace, op.key)
                results.append(self._record_to_item(matches[0]) if matches else None)
            elif isinstance(op, SearchOp):
                results.append(self._search_sync(op))
            elif isinstance(op, ListNamespacesOp):
                results.append(self._list_namespaces_sync(op))
            elif isinstance(op, PutOp):
                put_ops[(op.namespace, op.key)] = op
                results.append(None)
            else:
                raise ValueError(f"Unsupported op type: {type(op)}")

        for op in put_ops.values():
            self._put_sync(op)
        return results

    async def abatch(self, ops: Iterable[Op]) -> list[Result]:
        return await asyncio.to_thread(self.batch, list(ops))
