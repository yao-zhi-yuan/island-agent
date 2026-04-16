from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.auth.auth_context import bind_user_context
from app.lighting.store import close_lighting_store, get_lighting_store, init_lighting_store
from app.lighting.tools import create_lighting_project_from_requirement


# 这个脚本验证 2A 第一批：不经过 graph，不依赖 LLM，只确认确定性 tool 闭环正确。
async def main() -> None:
    if not (os.getenv("LIGHTING_POSTGRES_DSN") or os.getenv("POSTGRES_DSN")):
        raise SystemExit("LIGHTING_POSTGRES_DSN or POSTGRES_DSN is required for Step 2A verification.")

    project_id: str | None = None
    user_id = f"lighting-step2a-{uuid4().hex[:8]}"

    await init_lighting_store()
    try:
        with bind_user_context(user_id):
            result_text = await create_lighting_project_from_requirement("帮我设计一个温馨卧室灯光方案")
        result = json.loads(result_text)
        assert result["ok"] is True, result
        project_id = result["project_id"]
        requirement_spec = result["requirement_spec"]

        assert requirement_spec["original_text"] == "帮我设计一个温馨卧室灯光方案"
        assert requirement_spec["intent_type"] == "lighting_design"
        assert requirement_spec["space_type"] == "bedroom"
        assert requirement_spec["style"] == "warm"
        assert "room_size" in requirement_spec["missing_fields"]
        assert "ceiling_height" in requirement_spec["missing_fields"]

        project = await get_lighting_store().get_project(user_id=user_id, project_id=project_id)
        stored_spec = project["project_state"]["requirement_spec"]
        assert stored_spec == requirement_spec

        print("lighting Step 2A verification passed")
        print(f"project_id={project_id}")
        print(f"user_id={user_id}")
        print("missing_fields=" + ",".join(requirement_spec["missing_fields"]))
    finally:
        if project_id:
            await get_lighting_store().pool.execute(
                "DELETE FROM lighting_projects WHERE id=$1 AND user_id=$2",
                project_id,
                user_id,
            )
        await close_lighting_store()


if __name__ == "__main__":
    asyncio.run(main())
