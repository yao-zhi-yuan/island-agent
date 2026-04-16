from __future__ import annotations

import os
import re
import shutil
import tempfile
from pathlib import Path
from uuid import uuid4

from app.sandbox.context import SandboxContext
from app.sandbox.store import get_sandbox_store, get_sandbox_store_status


def _slug(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")
    return normalized or "default"


class SandboxManager:
    def __init__(self) -> None:
        configured_root = (os.getenv("SANDBOX_ROOT_DIR") or "").strip()
        if configured_root:
            self._root = Path(configured_root).expanduser().resolve()
        else:
            self._root = (Path(tempfile.gettempdir()) / "copilot-agent-sandboxes").resolve()
        self._seed_skills_root = (Path(__file__).resolve().parents[1] / "skills").resolve()

    @property
    def root_dir(self) -> Path:
        self._root.mkdir(parents=True, exist_ok=True)
        return self._root

    def _workspace_path(self, user_id: str, session_id: str, sandbox_id: str) -> Path:
        return self.root_dir / _slug(user_id) / _slug(session_id) / sandbox_id

    def _seed_workspace(self, workspace_path: Path) -> None:
        workspace_path.mkdir(parents=True, exist_ok=True)
        for name in (".tmp", ".cache", ".npm"):
            (workspace_path / name).mkdir(parents=True, exist_ok=True)

        skills_dst = workspace_path / "skills"
        skills_dst.mkdir(parents=True, exist_ok=True)
        if self._seed_skills_root.is_dir():
            for item in self._seed_skills_root.iterdir():
                target = skills_dst / item.name
                if item.is_dir():
                    shutil.copytree(item, target, dirs_exist_ok=True)
                elif item.is_file() and not target.exists():
                    shutil.copy2(item, target)

    async def ensure_session(self, *, user_id: str, session_id: str) -> SandboxContext:
        sandbox_id: str
        workspace_path: Path

        status = get_sandbox_store_status()
        if status.get("enabled"):
            store = get_sandbox_store()
            try:
                row = await store.get_by_session(user_id=user_id, session_id=session_id)
                sandbox_id = str(row["sandbox_id"])
                workspace_path = Path(str(row["workspace_path"])).expanduser().resolve()
                await store.touch(user_id=user_id, session_id=session_id)
            except KeyError:
                sandbox_id = f"sbx-{uuid4().hex[:12]}"
                workspace_path = self._workspace_path(user_id, session_id, sandbox_id)
                await store.upsert(
                    user_id=user_id,
                    session_id=session_id,
                    sandbox_id=sandbox_id,
                    workspace_path=str(workspace_path),
                )
        else:
            sandbox_id = f"sbx-{_slug(session_id)}"
            workspace_path = self._workspace_path(user_id, session_id, sandbox_id)

        self._seed_workspace(workspace_path)
        return SandboxContext(
            session_id=session_id,
            user_id=user_id,
            sandbox_id=sandbox_id,
            workspace_path=workspace_path,
        )

    async def delete_session(self, *, user_id: str, session_id: str) -> None:
        status = get_sandbox_store_status()
        workspace_path: Path | None = None
        if status.get("enabled"):
            deleted = await get_sandbox_store().delete_by_session(user_id=user_id, session_id=session_id)
            if deleted is not None:
                workspace_path = Path(str(deleted["workspace_path"])).expanduser().resolve()
        if workspace_path is None:
            workspace_path = None
            base = self.root_dir / _slug(user_id) / _slug(session_id)
            if base.exists():
                workspace_path = base
        if workspace_path and workspace_path.exists():
            shutil.rmtree(workspace_path, ignore_errors=True)

    def current(self) -> SandboxContext | None:
        return get_sandbox_context()


_manager = SandboxManager()


def get_sandbox_manager() -> SandboxManager:
    return _manager
