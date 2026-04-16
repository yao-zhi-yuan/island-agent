from __future__ import annotations

from typing import Any


SUPPORTED_SPACE_TYPES = ("bedroom", "living_room", "dining_room", "study", "office")

_ALL_STYLE_TAGS = ("warm", "modern", "minimal", "bright", "unknown")

FIXTURE_FAMILIES: list[dict[str, Any]] = [
    {
        "fixture_id": "ambient_ceiling_basic",
        "name": "基础主照明",
        "category": "ceiling_light",
        "roles": ("ambient",),
        "space_types": SUPPORTED_SPACE_TYPES,
        "style_tags": _ALL_STYLE_TAGS,
        "default_specs": {
            "color_temperature": "3500K",
            "mounting": "ceiling",
        },
        "reason": "该空间需要一组均匀的基础照明。",
    },
    {
        "fixture_id": "task_desk_light_basic",
        "name": "基础桌面任务照明",
        "category": "task_light",
        "roles": ("task",),
        "space_types": ("bedroom", "study", "office"),
        "style_tags": _ALL_STYLE_TAGS,
        "default_specs": {
            "color_temperature": "3500K",
            "mounting": "desk",
        },
        "reason": "书写、阅读或办公区域需要局部任务照明。",
    },
    {
        "fixture_id": "accent_strip_basic",
        "name": "基础氛围灯带",
        "category": "linear_strip",
        "roles": ("accent",),
        "space_types": ("bedroom", "living_room", "dining_room"),
        "style_tags": _ALL_STYLE_TAGS,
        "default_specs": {
            "color_temperature": "3500K",
            "mounting": "indirect",
        },
        "reason": "辅助氛围光可增强空间层次和舒适感。",
    },
]

_SPACE_ROLE_RULES: dict[str, tuple[str, ...]] = {
    "bedroom": ("ambient", "accent"),
    "living_room": ("ambient", "accent"),
    "dining_room": ("ambient",),
    "study": ("ambient", "task"),
    "office": ("ambient", "task"),
}

_STYLE_COLOR_TEMPERATURES = {
    "warm": "3000K",
    "bright": "4000K",
    "modern": "4000K",
    "minimal": "4000K",
}

SOURCE_RULES = [
    "selection_v1.indoor_basic_roles",
    "selection_v1.style_color_temperature",
]


def get_required_roles(space_type: str) -> list[str]:
    return list(_SPACE_ROLE_RULES.get(space_type, ()))


def get_style_color_temperature(style: str | None) -> str:
    if not style:
        return "3500K"
    return _STYLE_COLOR_TEMPERATURES.get(style, "3500K")


def find_fixture_family(role: str, space_type: str, style: str | None = None) -> dict[str, Any] | None:
    style_tag = style or "unknown"
    for family in FIXTURE_FAMILIES:
        if role not in family["roles"]:
            continue
        if space_type not in family["space_types"]:
            continue
        if style_tag not in family["style_tags"]:
            continue
        return family
    return None


def build_fixture_recommendation(
    *,
    role: str,
    family: dict[str, Any],
    color_temperature: str,
) -> dict[str, Any]:
    recommended_specs = dict(family["default_specs"])
    recommended_specs["color_temperature"] = color_temperature

    return {
        "role": role,
        "fixture_id": family["fixture_id"],
        "name": family["name"],
        "category": family["category"],
        "recommended_specs": recommended_specs,
        "reason": family["reason"],
    }


def select_basic_fixture_families(space_type: str, style: str | None = None) -> dict[str, Any]:
    selected_fixtures: list[dict[str, Any]] = []
    unresolved_roles: list[str] = []
    color_temperature = get_style_color_temperature(style)

    for role in get_required_roles(space_type):
        family = find_fixture_family(role, space_type, style)
        if family is None:
            unresolved_roles.append(role)
            continue
        selected_fixtures.append(
            build_fixture_recommendation(
                role=role,
                family=family,
                color_temperature=color_temperature,
            )
        )

    return {
        "selected_fixtures": selected_fixtures,
        "unresolved_roles": unresolved_roles,
        "selection_warnings": [],
        "source_rules": list(SOURCE_RULES),
    }
