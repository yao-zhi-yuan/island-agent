from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from typing import Any

from app.tasks.store import TaskStore


class TaskScheduler:
    def __init__(self, store: TaskStore, executor: Callable[[dict[str, Any]], Awaitable[str]]) -> None:
        self.store = store
        self.executor = executor
        self._task: asyncio.Task | None = None
        self._stopped = asyncio.Event()
        self._poll_interval = int(os.getenv("TASKS_POLL_SECONDS", "5"))

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stopped.clear()
        self._task = asyncio.create_task(self._run_loop(), name="task-scheduler")

    async def stop(self) -> None:
        self._stopped.set()
        if self._task is not None:
            await self._task
            self._task = None

    async def _run_loop(self) -> None:
        while not self._stopped.is_set():
            try:
                due = await self.store.claim_due_tasks(limit=20)
                for task in due:
                    await self._execute_task(task)
            except Exception as exc:
                print(f"[tasks] scheduler loop error: {exc}")
            if not self._stopped.is_set():
                await asyncio.sleep(self._poll_interval)

    async def _execute_task(self, task: dict[str, Any]) -> None:
        run_id = await self.store.create_run(task=task)
        success = True
        output: str | None = None
        error: str | None = None
        try:
            output = await self.executor(task)
        except Exception as exc:
            success = False
            error = str(exc)
        finally:
            await self.store.finish_run(
                run_id=run_id,
                success=success,
                output=output,
                error=error,
            )
            await self.store.finalize_task_after_run(task=task, success=success)
