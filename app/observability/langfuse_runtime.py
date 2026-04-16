from __future__ import annotations

import os
from contextlib import nullcontext
from typing import Any

from langfuse import Langfuse, get_client, propagate_attributes
from langfuse.langchain import CallbackHandler

_handler: CallbackHandler | None = None
_initialized = False


def is_langfuse_enabled() -> bool:
    """Return whether Langfuse tracing is configured."""
    return bool(
        (os.getenv("LANGFUSE_PUBLIC_KEY") or "").strip()
        and (os.getenv("LANGFUSE_SECRET_KEY") or "").strip()
    )


def _base_url() -> str | None:
    return (
        (os.getenv("LANGFUSE_BASE_URL") or "").strip()
        or (os.getenv("LANGFUSE_HOST") or "").strip()
        or None
    )


def _ensure_langfuse() -> None:
    global _initialized
    if _initialized or not is_langfuse_enabled():
        return

    Langfuse(
        public_key=(os.getenv("LANGFUSE_PUBLIC_KEY") or "").strip() or None,
        secret_key=(os.getenv("LANGFUSE_SECRET_KEY") or "").strip() or None,
        base_url=_base_url(),
        tracing_enabled=(os.getenv("LANGFUSE_TRACING_ENABLED", "true").strip().lower() != "false"),
    )
    _initialized = True


def _get_handler() -> CallbackHandler | None:
    global _handler
    if not is_langfuse_enabled():
        return None
    _ensure_langfuse()
    if _handler is None:
        _handler = CallbackHandler(public_key=(os.getenv("LANGFUSE_PUBLIC_KEY") or "").strip() or None)
    return _handler


def build_langchain_config(base: dict[str, Any] | None = None) -> dict[str, Any]:
    """Attach Langfuse callback handler to a runnable config."""
    config = dict(base or {})
    handler = _get_handler()
    if handler is None:
        return config

    callbacks = list(config.get("callbacks") or [])
    if all(cb is not handler for cb in callbacks):
        callbacks.append(handler)
    config["callbacks"] = callbacks
    return config


def propagate_langfuse_attributes(
    *,
    user_id: str | None = None,
    session_id: str | None = None,
    trace_name: str | None = None,
    metadata: dict[str, str] | None = None,
):
    """Propagate trace attributes for all observations created in the current context."""
    if not is_langfuse_enabled():
        return nullcontext()
    _ensure_langfuse()
    return propagate_attributes(
        user_id=user_id,
        session_id=session_id,
        trace_name=trace_name,
        metadata=metadata,
    )


def shutdown_langfuse() -> None:
    """Flush and close the Langfuse client."""
    if not is_langfuse_enabled():
        return
    _ensure_langfuse()
    client = get_client(public_key=(os.getenv("LANGFUSE_PUBLIC_KEY") or "").strip() or None)
    client.flush()
    client.shutdown()
