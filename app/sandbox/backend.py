from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path
import re

from deepagents.backends.filesystem import FilesystemBackend
from deepagents.backends.protocol import (
    EditResult,
    ExecuteResponse,
    FileDownloadResponse,
    FileInfo,
    FileUploadResponse,
    GrepMatch,
    SandboxBackendProtocol,
    WriteResult,
)

from app.sandbox.context import get_sandbox_context, require_sandbox_context


class SessionSandboxBackend(SandboxBackendProtocol):
    """Resolve file/execute operations against the currently bound session sandbox."""

    def __init__(self) -> None:
        self._default_timeout = int(os.getenv("SANDBOX_EXEC_TIMEOUT_SECONDS", "120"))
        self._max_output_bytes = int(os.getenv("SANDBOX_EXEC_MAX_OUTPUT_BYTES", "100000"))
        self._max_file_size_mb = int(os.getenv("SANDBOX_MAX_FILE_MB", "10"))
        self._docker_image = os.getenv("SANDBOX_DOCKER_IMAGE", "python:3.13-slim")
        self._docker_network = os.getenv("SANDBOX_DOCKER_NETWORK", "bridge")
        self._docker_memory = os.getenv("SANDBOX_DOCKER_MEMORY", "1g")
        self._docker_cpus = os.getenv("SANDBOX_DOCKER_CPUS", "1.0")
        self._docker_pids_limit = int(os.getenv("SANDBOX_DOCKER_PIDS_LIMIT", "256"))
        self._docker_context = (os.getenv("SANDBOX_DOCKER_CONTEXT") or "").strip()
        self._docker_host = (os.getenv("SANDBOX_DOCKER_HOST") or "").strip()
        self._env_allowlist = [
            item.strip()
            for item in (os.getenv("SANDBOX_ENV_ALLOWLIST") or "").split(",")
            if item.strip()
        ]

    @property
    def id(self) -> str:
        context = get_sandbox_context()
        return context.sandbox_id if context is not None else "sandbox-unbound"

    def _workspace(self) -> Path:
        return require_sandbox_context().workspace_path

    def _fs(self) -> FilesystemBackend:
        return FilesystemBackend(
            root_dir=self._workspace(),
            virtual_mode=True,
            max_file_size_mb=self._max_file_size_mb,
        )

    def ls_info(self, path: str) -> list[FileInfo]:
        return self._fs().ls_info(path)

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        return self._fs().read(file_path, offset=offset, limit=limit)

    def grep_raw(self, pattern: str, path: str | None = None, glob: str | None = None) -> list[GrepMatch] | str:
        return self._fs().grep_raw(pattern, path=path, glob=glob)

    def glob_info(self, pattern: str, path: str = "/") -> list[FileInfo]:
        return self._fs().glob_info(pattern, path=path)

    def write(self, file_path: str, content: str) -> WriteResult:
        return self._fs().write(file_path, content)

    def edit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> EditResult:
        return self._fs().edit(file_path, old_string, new_string, replace_all=replace_all)

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        return self._fs().upload_files(files)

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        return self._fs().download_files(paths)

    def _docker_command(self, workspace: Path, command: str) -> list[str]:
        command = self._normalize_command_paths(workspace, command)
        docker_cmd = ["docker"]
        if self._docker_context:
            docker_cmd.extend(["--context", self._docker_context])
        docker_cmd.extend(
            [
                "run",
                "--rm",
                "--workdir",
                "/workspace",
                "--mount",
                f"type=bind,src={workspace},dst=/workspace",
                "--env",
                "HOME=/workspace",
                "--env",
                "TMPDIR=/workspace/.tmp",
                "--env",
                "XDG_CACHE_HOME=/workspace/.cache",
                "--env",
                "NPM_CONFIG_CACHE=/workspace/.npm",
                "--env",
                "npm_config_cache=/workspace/.npm",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--pids-limit",
                str(self._docker_pids_limit),
                "--memory",
                self._docker_memory,
                "--cpus",
                self._docker_cpus,
                "--tmpfs",
                "/tmp:rw,nosuid,size=64m",
            ]
        )
        if self._docker_network:
            docker_cmd.extend(["--network", self._docker_network])
        if hasattr(os, "getuid") and hasattr(os, "getgid"):
            docker_cmd.extend(["--user", f"{os.getuid()}:{os.getgid()}"])
        for key in self._env_allowlist:
            value = os.getenv(key)
            if value is not None:
                docker_cmd.extend(["--env", f"{key}={value}"])
        docker_cmd.extend([self._docker_image, "sh", "-lc", command])
        return docker_cmd

    def _normalize_command_paths(self, workspace: Path, command: str) -> str:
        host_workspace = str(workspace)
        normalized = command.replace(host_workspace, "/workspace")

        pattern = re.compile(r'(?P<quote>["\']?)(?P<path>/[^\s"\']+)(?P=quote)')

        def repl(match: re.Match[str]) -> str:
            quote = match.group("quote") or ""
            raw_path = match.group("path")
            if raw_path.startswith("/workspace/") or raw_path == "/workspace":
                return match.group(0)
            candidate = workspace / raw_path.lstrip("/")
            if candidate.exists():
                return f"{quote}/workspace{raw_path}{quote}"
            return match.group(0)

        return pattern.sub(repl, normalized)

    def execute(self, command: str, *, timeout: int | None = None) -> ExecuteResponse:
        effective_timeout = timeout if timeout is not None else self._default_timeout
        if effective_timeout <= 0:
            raise ValueError(f"timeout must be positive, got {effective_timeout}")

        context = require_sandbox_context()
        workspace = context.workspace_path
        docker_cmd = self._docker_command(workspace, command)
        exec_env = os.environ.copy()
        if self._docker_host:
            exec_env["DOCKER_HOST"] = self._docker_host

        try:
            result = subprocess.run(  # noqa: S603
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                cwd=str(workspace.parent),
                env=exec_env,
                check=False,
            )
            output = result.stdout
            if result.stderr:
                output = f"{output}\n[stderr]\n{result.stderr}" if output else f"[stderr]\n{result.stderr}"
            exit_code = result.returncode
        except subprocess.TimeoutExpired:
            output = f"Command timed out after {effective_timeout} seconds."
            exit_code = 124
        except FileNotFoundError:
            output = "Docker not found. Please install Docker and ensure `docker` is in PATH."
            exit_code = 127
        except Exception as exc:  # noqa: BLE001
            output = f"Failed to execute command in Docker session sandbox: {exc}"
            exit_code = 1

        truncated = False
        encoded = output.encode("utf-8", errors="replace")
        if len(encoded) > self._max_output_bytes:
            output = encoded[: self._max_output_bytes].decode("utf-8", errors="replace") + "\n...[truncated]"
            truncated = True

        header = (
            "[sandbox]"
            f" id={context.sandbox_id}"
            f" session_id={context.session_id}"
            " executor=docker"
            f" image={shlex.quote(self._docker_image)}"
            f" network={self._docker_network}"
            f" docker_context={self._docker_context or '-'}"
            f" docker_host={self._docker_host or '-'}"
            f" workspace={shlex.quote(str(workspace))}"
            f" timeout={effective_timeout}s\n"
        )
        return ExecuteResponse(output=header + output, exit_code=exit_code, truncated=truncated)
