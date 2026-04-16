from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppSettings:
    api_prefix: str
    api_router_prefix: str
    chat_endpoint_path: str
    agent_model: str
    agent_recursion_limit: int


def _normalize_prefix(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    return raw if raw.startswith("/") else f"/{raw}"


def _normalize_path(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return "/"
    return raw if raw.startswith("/") else f"/{raw}"


def load_settings() -> AppSettings:
    api_prefix = _normalize_prefix(os.getenv("APP_API_PREFIX", ""))
    api_router_prefix = _normalize_path(f"{api_prefix}/api" if api_prefix else "/api")
    chat_endpoint_path = _normalize_path(
        os.getenv("APP_CHAT_ENDPOINT_PATH", f"{api_prefix}/v1/chat" if api_prefix else "/v1/chat")
    )
    return AppSettings(
        api_prefix=api_prefix,
        api_router_prefix=api_router_prefix,
        chat_endpoint_path=chat_endpoint_path,
        agent_model=os.getenv("AGENT_MODEL", "qwen3.5-plus"),
        agent_recursion_limit=max(1, int(os.getenv("AGENT_RECURSION_LIMIT", "150"))),
    )


settings = load_settings()
