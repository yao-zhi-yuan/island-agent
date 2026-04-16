from __future__ import annotations

import json

from app.auth.auth_context import get_effective_user_id
from app.lighting.fixtures import SUPPORTED_SPACE_TYPES, select_basic_fixture_families
from app.lighting.requirements import extract_requirement_spec, merge_requirement_spec
from app.lighting.schemas import ProjectState
from app.lighting.store import get_lighting_store, get_lighting_store_status
from app.sandbox import get_sandbox_context


def _current_session_id() -> str | None:
    context = get_sandbox_context()
    if context is None:
        return None
    return context.session_id


async def create_lighting_project_from_requirement(user_text: str, title: str | None = None) -> str:
    """
    从自然语言需求创建照明项目。

    Args:
        user_text: 用户原始照明设计请求。
        title: 可选项目标题。如未指定，则使用需求文本作为标题提示。
    """
    status = get_lighting_store_status()
    if not status.get("enabled"):
        return json.dumps(
            {"ok": False, "error": "lighting store not enabled, configure LIGHTING_POSTGRES_DSN/POSTGRES_DSN"},
            ensure_ascii=False,
        )

    cleaned_text = (user_text or "").strip()
    if not cleaned_text:
        raise ValueError("user_text is required")

    user_id = get_effective_user_id()
    session_id = _current_session_id()
    requirement_spec = extract_requirement_spec(cleaned_text)
    store = get_lighting_store()

    # 创建数据库项目lighting project
    project = await store.create_project(
        user_id=user_id,
        session_id=session_id,
        title=title,
        initial_requirement=cleaned_text,
    )
    state = ProjectState.model_validate(project["project_state"])
    state.stage = "requirement"
    state.requirement_spec = requirement_spec
    project = await store.update_project_state(
        user_id=user_id,
        project_id=str(project["id"]),
        project_state=state,
    )

    return json.dumps(
        {
            "ok": True,
            "project_id": project["id"],
            "title": project["title"],
            "session_id": project.get("session_id"),
            "requirement_spec": requirement_spec,
            "missing_fields": requirement_spec.get("missing_fields", []),
            "clarification_questions": requirement_spec.get("clarification_questions", []),
        },
        ensure_ascii=False,
        default=str,
    )


async def update_lighting_project_requirement(project_id: str, user_text: str) -> str:
    """
    从用户的跟进澄清更新现有照明项目的requirement_spec

    Args:
        project_id: 由create_lighting_project_from_requirement返回的现有照明项目ID。
        user_text: 用户的跟进澄清，例如房间大小或天花板高度。
    """
    status = get_lighting_store_status()
    if not status.get("enabled"):
        return json.dumps(
            {"ok": False, "error": "lighting store not enabled, configure LIGHTING_POSTGRES_DSN/POSTGRES_DSN"},
            ensure_ascii=False,
        )

    cleaned_project_id = (project_id or "").strip()
    cleaned_text = (user_text or "").strip()
    if not cleaned_project_id:
        raise ValueError("project_id is required")
    if not cleaned_text:
        raise ValueError("user_text is required")

    user_id = get_effective_user_id()
    store = get_lighting_store()
    project = await store.get_project(user_id=user_id, project_id=cleaned_project_id)
    state = ProjectState.model_validate(project["project_state"])

    # 后续澄清只合并用户明确补充的字段，避免把未提到的旧信息覆盖为空。
    state.stage = "requirement"
    state.requirement_spec = merge_requirement_spec(state.requirement_spec, cleaned_text)
    project = await store.update_project_state(
        user_id=user_id,
        project_id=cleaned_project_id,
        project_state=state,
    )

    requirement_spec = project["project_state"]["requirement_spec"]
    return json.dumps(
        {
            "ok": True,
            "project_id": project["id"],
            "title": project["title"],
            "session_id": project.get("session_id"),
            "requirement_spec": requirement_spec,
            "missing_fields": requirement_spec.get("missing_fields", []),
            "clarification_questions": requirement_spec.get("clarification_questions", []),
        },
        ensure_ascii=False,
        default=str,
    )


def _selection_missing_fields(requirement_spec: dict) -> list[str]:
    missing_fields: list[str] = []
    space_type = requirement_spec.get("space_type")
    dimensions = requirement_spec.get("dimensions")

    if not space_type or space_type not in SUPPORTED_SPACE_TYPES:
        missing_fields.append("space_type")
    if not isinstance(dimensions, dict) or not dimensions:
        missing_fields.append("room_size")
    if requirement_spec.get("ceiling_height") is None:
        missing_fields.append("ceiling_height")

    return missing_fields


async def select_fixtures_for_project(project_id: str) -> str:
    """
    从现有 ProjectState.requirement_spec 生成第一批最小灯具选型结果。

    第一批只写入 fixture_selection，不进入 layout、BOM 或 report。
    """
    status = get_lighting_store_status()
    if not status.get("enabled"):
        return json.dumps(
            {"ok": False, "error": "lighting store not enabled, configure LIGHTING_POSTGRES_DSN/POSTGRES_DSN"},
            ensure_ascii=False,
        )

    cleaned_project_id = (project_id or "").strip()
    if not cleaned_project_id:
        return json.dumps(
            {"ok": False, "error": "project_id is required"},
            ensure_ascii=False,
        )

    user_id = get_effective_user_id()
    store = get_lighting_store()
    try:
        project = await store.get_project(user_id=user_id, project_id=cleaned_project_id)
    except KeyError:
        return json.dumps(
            {"ok": False, "project_id": cleaned_project_id, "error": "lighting project not found"},
            ensure_ascii=False,
        )

    state = ProjectState.model_validate(project["project_state"])
    requirement_spec = state.requirement_spec or {}
    missing_fields = _selection_missing_fields(requirement_spec)
    if missing_fields:
        return json.dumps(
            {
                "ok": False,
                "project_id": cleaned_project_id,
                "missing_fields": missing_fields,
                "message": "需求信息不足，暂不能进入灯具选型。",
            },
            ensure_ascii=False,
        )

    space_type = requirement_spec["space_type"]
    style = requirement_spec.get("style")
    selection_result = select_basic_fixture_families(space_type=space_type, style=style)
    if not selection_result["selected_fixtures"]:
        return json.dumps(
            {
                "ok": False,
                "project_id": cleaned_project_id,
                "missing_fields": ["fixture_selection"],
                "message": "未找到可用的基础灯具族。",
            },
            ensure_ascii=False,
        )

    fixture_selection = {
        "status": "selected",
        "version": "selection_v1",
        "space_type": space_type,
        "selection_basis": {
            "style": style,
            "dimensions": requirement_spec.get("dimensions", {}),
            "ceiling_height": requirement_spec.get("ceiling_height"),
        },
        **selection_result,
    }

    state.stage = "selection"
    state.fixture_selection = fixture_selection
    project = await store.update_project_state(
        user_id=user_id,
        project_id=cleaned_project_id,
        project_state=state,
    )

    return json.dumps(
        {
            "ok": True,
            "project_id": project["id"],
            "stage": project["project_state"]["stage"],
            "fixture_selection": project["project_state"]["fixture_selection"],
        },
        ensure_ascii=False,
        default=str,
    )
