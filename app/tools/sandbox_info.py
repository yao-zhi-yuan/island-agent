from __future__ import annotations

import json

from app.sandbox import get_sandbox_context


async def get_current_sandbox_info() -> str:
    """Return sandbox binding information for the current session."""
    context = get_sandbox_context()
    if context is None:
        return json.dumps({"ok": False, "error": "sandbox context not bound"}, ensure_ascii=False)
    return json.dumps(
        {
            "ok": True,
            "session_id": context.session_id,
            "user_id": context.user_id,
            "sandbox_id": context.sandbox_id,
            "virtual_root": "/",
            "workspace_path": "/workspace",
            "skills_path": "/skills",
            "path_rules": [
                "File tools use virtual paths rooted at /, for example /quick_sort.py.",
                "Command execution runs inside Docker with workdir=/workspace.",
                "When executing a file created at /quick_sort.py, use python /workspace/quick_sort.py or python quick_sort.py.",
            ],
        },
        ensure_ascii=False,
    )
