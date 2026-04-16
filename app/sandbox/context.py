from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SandboxContext:
    session_id: str
    user_id: str
    sandbox_id: str
    workspace_path: Path


_SANDBOX_CONTEXT: ContextVar[SandboxContext | None] = ContextVar("sandbox_context", default=None)


def get_sandbox_context() -> SandboxContext | None:
    return _SANDBOX_CONTEXT.get()


def require_sandbox_context() -> SandboxContext:
    context = get_sandbox_context()
    if context is None:
        raise RuntimeError("Sandbox context is not bound to the current run.")
    return context


def _set_sandbox_context(context: SandboxContext | None) -> Token:
    return _SANDBOX_CONTEXT.set(context)


def _reset_sandbox_context(token: Token) -> None:
    _SANDBOX_CONTEXT.reset(token)


@contextmanager
def bind_sandbox_context(context: SandboxContext | None) -> Iterator[None]:
    token = _set_sandbox_context(context)
    try:
        yield
    finally:
        _reset_sandbox_context(token)
