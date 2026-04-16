from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.auth.auth_context import get_effective_user_id
from app.sandbox import get_sandbox_manager

router = APIRouter(prefix="/files", tags=["files"])

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
_ALLOWED_SUFFIXES = {".xlsx", ".xlsm"}


def _safe_filename(filename: str) -> str:
    raw = Path(filename or "upload.xlsx").name
    suffix = Path(raw).suffix.lower()
    stem = Path(raw).stem or "upload"
    cleaned_stem = _SAFE_NAME_RE.sub("_", stem).strip("._")
    return f"{cleaned_stem or 'upload'}{suffix}"


class UploadExcelResponse(BaseModel):
    ok: bool
    filename: str
    file_path: str
    mime_type: str
    size: int
    session_id: str


@router.post(
    "/excel/upload",
    response_model=UploadExcelResponse,
    summary="上传 Excel 文件",
    description="上传 `.xlsx/.xlsm` 文件到当前 session 对应的 sandbox `/uploads` 目录。",
)
async def upload_excel_file(
    file: Annotated[UploadFile, File(description="Excel 文件，仅支持 .xlsx / .xlsm。")],
    session_id: Annotated[str, Form(description="聊天会话 ID，用于绑定当前 session sandbox。")],
) -> dict[str, str | int | bool]:
    user_id = get_effective_user_id()
    filename = _safe_filename(file.filename or "")
    suffix = Path(filename).suffix.lower()
    if suffix not in _ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="Only .xlsx and .xlsm Excel files are supported.")

    data = await file.read()
    max_bytes = 10 * 1024 * 1024
    if not data:
        raise HTTPException(status_code=400, detail="File is empty.")
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail="File is too large, max 10MB.")

    sandbox = await get_sandbox_manager().ensure_session(user_id=user_id, session_id=session_id)
    upload_dir = sandbox.workspace_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    target = upload_dir / filename
    if target.exists():
        stem = target.stem[:60]
        target = upload_dir / f"{stem}_{uuid4().hex[:8]}{suffix}"
    target.write_bytes(data)

    return {
        "ok": True,
        "filename": target.name,
        "file_path": f"/uploads/{target.name}",
        "mime_type": file.content_type or "",
        "size": len(data),
        "session_id": session_id,
    }
