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
from app.lighting.tools import generate_layout_for_project, select_fixtures_for_project


async def _create_project_with_spec(user_id: str, requirement_spec: dict) -> str:
    store = get_lighting_store()
    project = await store.create_project(
        user_id=user_id,
        session_id="step4a-session",
        title="Step 4A 验证项目",
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


async def _select_layout_and_fetch(user_id: str, project_id: str) -> tuple[dict, dict, dict]:
    with bind_user_context(user_id):
        selection_text = await select_fixtures_for_project(project_id)
        layout_text = await generate_layout_for_project(project_id)
    selection_result = json.loads(selection_text)
    layout_result = json.loads(layout_text)
    project = await get_lighting_store().get_project(user_id=user_id, project_id=project_id)
    return selection_result, layout_result, project


async def _layout_and_fetch(user_id: str, project_id: str) -> tuple[dict, dict]:
    with bind_user_context(user_id):
        layout_text = await generate_layout_for_project(project_id)
    layout_result = json.loads(layout_text)
    project = await get_lighting_store().get_project(user_id=user_id, project_id=project_id)
    return layout_result, project


def _placement_roles(layout_plan: dict) -> set[str]:
    return {item["role"] for item in layout_plan.get("placements", [])}


def _assert_generated_layout(project: dict, expected_roles: set[str]) -> dict:
    state = project["project_state"]
    layout_plan = state["layout_plan"]

    assert state["stage"] == "layout"
    assert layout_plan["status"] == "generated"
    assert layout_plan["version"] == "layout_v1"
    assert layout_plan["placements"], layout_plan
    assert _placement_roles(layout_plan) == expected_roles
    assert layout_plan["circuit_suggestions"], layout_plan
    return layout_plan


async def main() -> None:
    if not (os.getenv("LIGHTING_POSTGRES_DSN") or os.getenv("POSTGRES_DSN")):
        raise SystemExit("LIGHTING_POSTGRES_DSN or POSTGRES_DSN is required for Step 4A verification.")

    user_id = f"lighting-step4a-{uuid4().hex[:8]}"
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
        study_selection, study_layout, study_project = await _select_layout_and_fetch(user_id, study_id)
        assert study_selection["ok"] is True, study_selection
        assert study_layout["ok"] is True, study_layout
        study_plan = _assert_generated_layout(study_project, {"ambient", "task"})
        assert len(study_plan["placements"]) == 2

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
        bedroom_selection, bedroom_layout, bedroom_project = await _select_layout_and_fetch(user_id, bedroom_id)
        assert bedroom_selection["ok"] is True, bedroom_selection
        assert bedroom_layout["ok"] is True, bedroom_layout
        bedroom_plan = _assert_generated_layout(bedroom_project, {"ambient", "accent"})
        accent_placement = next(item for item in bedroom_plan["placements"] if item["role"] == "accent")
        assert accent_placement["placement_type"] == "segment"
        assert len(accent_placement["points"]) == 2

        dining_id = await _create_project_with_spec(
            user_id,
            {
                "original_text": "现代餐厅照明，3x4米，层高2.8米",
                "intent_type": "lighting_design",
                "space_type": "dining_room",
                "style": "modern",
                "dimensions": {"width": 3.0, "length": 4.0, "unit": "m"},
                "ceiling_height": 2.8,
                "budget": None,
                "missing_fields": [],
                "clarification_questions": [],
            },
        )
        project_ids.append(dining_id)
        dining_selection, dining_layout, dining_project = await _select_layout_and_fetch(user_id, dining_id)
        assert dining_selection["ok"] is True, dining_selection
        assert dining_layout["ok"] is True, dining_layout
        dining_plan = _assert_generated_layout(dining_project, {"ambient"})
        assert dining_plan["placements"][0]["points"]

        area_only_id = await _create_project_with_spec(
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
        project_ids.append(area_only_id)
        area_selection, area_layout, area_project = await _select_layout_and_fetch(user_id, area_only_id)
        assert area_selection["ok"] is True, area_selection
        assert area_layout["ok"] is False, area_layout
        assert "dimensions.width" in area_layout["missing_fields"]
        assert "dimensions.length" in area_layout["missing_fields"]
        assert area_project["project_state"]["stage"] == "selection"
        assert area_project["project_state"]["layout_plan"] == {}

        no_selection_id = await _create_project_with_spec(
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
        project_ids.append(no_selection_id)
        no_selection_layout, no_selection_project = await _layout_and_fetch(user_id, no_selection_id)
        assert no_selection_layout["ok"] is False, no_selection_layout
        assert "fixture_selection.status" in no_selection_layout["missing_fields"]
        assert "fixture_selection.selected_fixtures" in no_selection_layout["missing_fields"]
        assert no_selection_project["project_state"]["stage"] == "requirement"
        assert no_selection_project["project_state"]["layout_plan"] == {}

        print("lighting Step 4A verification passed")
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
