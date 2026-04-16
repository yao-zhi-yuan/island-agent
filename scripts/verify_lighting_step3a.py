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
from app.lighting.schemas import ProjectState
from app.lighting.store import close_lighting_store, get_lighting_store, init_lighting_store
from app.lighting.tools import select_fixtures_for_project


async def _create_project_with_spec(user_id: str, requirement_spec: dict) -> str:
    store = get_lighting_store()
    project = await store.create_project(
        user_id=user_id,
        session_id="step3a-session",
        title="Step 3A 验证项目",
        initial_requirement=requirement_spec.get("original_text"),
    )
    state = ProjectState.model_validate(project["project_state"])
    state.stage = "requirement"
    state.requirement_spec = requirement_spec
    project = await store.update_project_state(
        user_id=user_id,
        project_id=str(project["id"]),
        project_state=state,
    )
    return str(project["id"])


async def _select_and_fetch(user_id: str, project_id: str) -> tuple[dict, dict]:
    with bind_user_context(user_id):
        result_text = await select_fixtures_for_project(project_id)
    result = json.loads(result_text)
    project = await get_lighting_store().get_project(user_id=user_id, project_id=project_id)
    return result, project


def _roles(selection: dict) -> set[str]:
    return {item["role"] for item in selection.get("selected_fixtures", [])}


async def main() -> None:
    if not (os.getenv("LIGHTING_POSTGRES_DSN") or os.getenv("POSTGRES_DSN")):
        raise SystemExit("LIGHTING_POSTGRES_DSN or POSTGRES_DSN is required for Step 3A verification.")

    user_id = f"lighting-step3a-{uuid4().hex[:8]}"
    project_ids: list[str] = []

    await init_lighting_store()
    try:
        study_id = await _create_project_with_spec(
            user_id,
            {
                "original_text": "明亮书房灯光设计，3x4米，层高2.8米",
                "intent_type": "lighting_design",
                "space_type": "study",
                "style": "bright",
                "dimensions": {"width": 3.0, "length": 4.0, "unit": "m"},
                "ceiling_height": 2.8,
                "budget": None,
                "missing_fields": [],
                "clarification_questions": [],
            },
        )
        project_ids.append(study_id)
        study_result, study_project = await _select_and_fetch(user_id, study_id)
        assert study_result["ok"] is True, study_result
        assert study_result["stage"] == "selection"
        study_selection = study_project["project_state"]["fixture_selection"]
        assert _roles(study_selection) == {"ambient", "task"}
        assert study_selection["selected_fixtures"][0]["recommended_specs"]["color_temperature"] == "4000K"

        bedroom_id = await _create_project_with_spec(
            user_id,
            {
                "original_text": "温馨卧室灯光设计，3x5米，层高2.7米",
                "intent_type": "lighting_design",
                "space_type": "bedroom",
                "style": "warm",
                "dimensions": {"width": 3.0, "length": 5.0, "unit": "m"},
                "ceiling_height": 2.7,
                "budget": None,
                "missing_fields": [],
                "clarification_questions": [],
            },
        )
        project_ids.append(bedroom_id)
        bedroom_result, bedroom_project = await _select_and_fetch(user_id, bedroom_id)
        assert bedroom_result["ok"] is True, bedroom_result
        bedroom_selection = bedroom_project["project_state"]["fixture_selection"]
        assert _roles(bedroom_selection) == {"ambient", "accent"}
        assert bedroom_selection["selected_fixtures"][0]["recommended_specs"]["color_temperature"] == "3000K"

        dining_id = await _create_project_with_spec(
            user_id,
            {
                "original_text": "现代餐厅照明，12平方米，层高2.8米",
                "intent_type": "lighting_design",
                "space_type": "dining_room",
                "style": "modern",
                "dimensions": {"area": 12.0, "unit": "m"},
                "ceiling_height": 2.8,
                "budget": None,
                "missing_fields": [],
                "clarification_questions": [],
            },
        )
        project_ids.append(dining_id)
        dining_result, dining_project = await _select_and_fetch(user_id, dining_id)
        assert dining_result["ok"] is True, dining_result
        dining_selection = dining_project["project_state"]["fixture_selection"]
        assert _roles(dining_selection) == {"ambient"}
        assert dining_selection["unresolved_roles"] == []

        missing_height_id = await _create_project_with_spec(
            user_id,
            {
                "original_text": "温馨卧室灯光设计，3x5米",
                "intent_type": "lighting_design",
                "space_type": "bedroom",
                "style": "warm",
                "dimensions": {"width": 3.0, "length": 5.0, "unit": "m"},
                "ceiling_height": None,
                "budget": None,
                "missing_fields": ["ceiling_height"],
                "clarification_questions": ["请补充层高。"],
            },
        )
        project_ids.append(missing_height_id)
        missing_result, missing_project = await _select_and_fetch(user_id, missing_height_id)
        assert missing_result["ok"] is False, missing_result
        assert "ceiling_height" in missing_result["missing_fields"]
        assert missing_project["project_state"]["stage"] == "requirement"
        assert missing_project["project_state"]["fixture_selection"] == {}

        print("lighting Step 3A verification passed")
        print(f"user_id={user_id}")
        print(f"verified_projects={len(project_ids)}")
    finally:
        if project_ids:
            await get_lighting_store().pool.execute(
                "DELETE FROM lighting_projects WHERE user_id=$1 AND id=ANY($2::text[])",
                user_id,
                project_ids,
            )
        await close_lighting_store()


if __name__ == "__main__":
    asyncio.run(main())
