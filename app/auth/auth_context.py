from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar, Token
from collections.abc import Iterator
from typing import Any

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse

_REQUEST_USER_ID: ContextVar[str | None] = ContextVar("request_user_id", default=None)


def _default_user_id() -> str:
    return os.getenv("DEFAULT_USER_ID", "demo-user")


def get_request_user_id() -> str | None:
    return _REQUEST_USER_ID.get()


def get_effective_user_id() -> str:
    return get_request_user_id() or _default_user_id()


def _set_request_user_id(user_id: str | None) -> Token:
    return _REQUEST_USER_ID.set(user_id)


def _reset_request_user_id(token: Token) -> None:
    _REQUEST_USER_ID.reset(token)


@contextmanager
def bind_user_context(user_id: str | None) -> Iterator[None]:
    token = _set_request_user_id(user_id)
    try:
        yield
    finally:
        _reset_request_user_id(token)


def _parse_auth_header(header_value: str | None) -> str | None:
    if not header_value:
        return None
    parts = header_value.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    # Tolerate accidental "Bearer bearer <jwt>" input.
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token or None


def _decode_jwt(token: str) -> dict[str, Any]:
    verify = os.getenv("JWT_VERIFY", "1").strip().lower() not in {"0", "false", "no"}
    algorithms_raw = os.getenv("JWT_ALGORITHMS", "HS256")
    algorithms = [a.strip() for a in algorithms_raw.split(",") if a.strip()]
    if not algorithms:
        algorithms = ["HS256"]

    if verify:
        secret = os.getenv("JWT_SECRET")
        if secret:
            return jwt.decode(token, key=secret, algorithms=algorithms)
        # Dev-friendly fallback: decode claims without signature verification
        # when JWT_VERIFY is enabled but JWT_SECRET is missing.
        return jwt.decode(
            token,
            options={
                "verify_signature": False,
                "verify_exp": False,
                "verify_nbf": False,
                "verify_iat": False,
                "verify_aud": False,
                "verify_iss": False,
            },
            algorithms=algorithms,
        )

    return jwt.decode(
        token,
        options={
            "verify_signature": False,
            "verify_exp": False,
            "verify_nbf": False,
            "verify_iat": False,
            "verify_aud": False,
            "verify_iss": False,
        },
        algorithms=algorithms,
    )


def _extract_user_id(claims: dict[str, Any]) -> str | None:
    primary = os.getenv("JWT_USER_ID_CLAIM", "user_id").strip()
    claims_env = os.getenv("JWT_USER_ID_CLAIMS", "").strip()
    candidates: list[str] = []
    if claims_env:
        candidates.extend([c.strip() for c in claims_env.split(",") if c.strip()])
    if primary:
        candidates.append(primary)
    # Common fallback claim names in enterprise JWTs.
    candidates.extend(["sub", "user_id", "id", "uid", "userId", "loginName", "tenantId"])

    seen: set[str] = set()
    for key in candidates:
        if key in seen:
            continue
        seen.add(key)
        value = claims.get(key)
        if value is not None and str(value).strip():
            return str(value)
    return None



async def auth_user_context_middleware(request: Request, call_next):
    """此中间件可配置，进入智能体的入口参数"""
    auth_header = request.headers.get("authorization")
    bearer = _parse_auth_header(auth_header)
    request_user_id: str | None = _default_user_id()

    if bearer:
        try:
            claims = _decode_jwt(bearer)
            request_user_id = _extract_user_id(claims)
            if not request_user_id:
                return JSONResponse({"detail": "JWT missing user id claim."}, status_code=401)
        except Exception as exc:
            return JSONResponse({"detail": f"Invalid JWT: {exc}"}, status_code=401)

    user_token = _set_request_user_id(request_user_id)
    try:
        return await call_next(request)
    finally:
        _reset_request_user_id(user_token)
