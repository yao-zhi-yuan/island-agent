from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
from pathlib import Path

from app.sandbox import get_sandbox_context

_PKG_RE = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+@[A-Za-z0-9._-]+$")


def _skills_dir() -> Path:
    context = get_sandbox_context()
    if context is not None:
        skills = context.workspace_path / "skills"
    else:
        skills = Path(__file__).resolve().parents[1] / "skills"
    skills.mkdir(parents=True, exist_ok=True)
    return skills


def _resolve_npx() -> str:
    configured = os.getenv("NPX_BIN", "").strip()
    if configured:
        return configured
    found = shutil.which("npx")
    if found:
        return found
    return "/opt/homebrew/opt/node@22/bin/npx"


async def install_skill_package(package: str) -> str:
    """Install a skill package into app/skills via `npx skills add`."""
    package = (package or "").strip()
    if not _PKG_RE.match(package):
        raise ValueError("invalid package format, expected owner/repo@skill-name")

    skills_dir = _skills_dir()
    skills_dir.mkdir(parents=True, exist_ok=True)
    work_home = skills_dir.parent / ".skills-home"
    work_home.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["HOME"] = str(work_home)
    env["TMPDIR"] = str(work_home / "tmp")
    env["NPM_CONFIG_CACHE"] = str(work_home / ".npm")
    env["npm_config_cache"] = str(work_home / ".npm")
    env["XDG_CACHE_HOME"] = str(work_home / ".cache")

    proc = await asyncio.create_subprocess_exec(
        _resolve_npx(),
        "--yes",
        "skills",
        "add",
        package,
        "-y",
        cwd=str(skills_dir),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    out = stdout.decode("utf-8", errors="replace")
    err = stderr.decode("utf-8", errors="replace")

    return json.dumps(
        {
            "ok": proc.returncode == 0,
            "package": package,
            "skills_dir": str(skills_dir),
            "exit_code": proc.returncode,
            "stdout": out[-12000:],
            "stderr": err[-12000:],
        },
        ensure_ascii=False,
    )


async def list_installed_skills() -> str:
    """List local skills found under app/skills."""
    skills_dir = _skills_dir()
    skills_dir.mkdir(parents=True, exist_ok=True)
    items: list[dict[str, str]] = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        items.append({"name": skill_md.parent.name, "path": str(skill_md.parent)})
    return json.dumps({"ok": True, "skills_dir": str(skills_dir), "items": items}, ensure_ascii=False)
