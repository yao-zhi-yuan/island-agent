from __future__ import annotations

from typing import Any


SUPPORTED_LAYOUT_ROLES = ("ambient", "task", "accent")

SOURCE_RULES = [
    "layout_v1.single_room_rectangular",
    "layout_v1.role_based_minimal_placements",
]


def _as_float(value: Any) -> float:
    return float(value)


def _round_coord(value: float) -> float:
    return round(value, 2)


def _point(x: float, y: float, z: float) -> dict[str, float]:
    return {"x": _round_coord(x), "y": _round_coord(y), "z": _round_coord(z)}


def _safe_margin(total: float, preferred: float = 0.6) -> float:
    # 第 4 周第一批只做矩形单空间的保守边距，避免小房间点位贴墙。
    return min(preferred, max(total / 4, 0.2))


def _ambient_points(width: float, length: float, ceiling_height: float) -> list[dict[str, float]]:
    area = width * length

    if area <= 16:
        return [_point(width / 2, length / 2, ceiling_height)]

    if area <= 30:
        if length >= width:
            return [
                _point(width / 2, length / 3, ceiling_height),
                _point(width / 2, length * 2 / 3, ceiling_height),
            ]
        return [
            _point(width / 3, length / 2, ceiling_height),
            _point(width * 2 / 3, length / 2, ceiling_height),
        ]

    x_margin = _safe_margin(width)
    y_margin = _safe_margin(length)
    return [
        _point(x_margin, y_margin, ceiling_height),
        _point(width - x_margin, y_margin, ceiling_height),
        _point(x_margin, length - y_margin, ceiling_height),
        _point(width - x_margin, length - y_margin, ceiling_height),
    ]


def _task_points(width: float, length: float) -> list[dict[str, float]]:
    # 未接入家具信息前，任务照明先落在靠墙默认工作区，后续再由家具/桌面位置覆盖。
    return [_point(width * 0.28, length * 0.28, 0.75)]


def _accent_segment(width: float, length: float, ceiling_height: float) -> list[dict[str, float]]:
    z = max(ceiling_height - 0.2, 0)

    if length >= width:
        wall_offset = min(0.15, width / 5)
        y_margin = _safe_margin(length)
        return [
            _point(wall_offset, y_margin, z),
            _point(wall_offset, length - y_margin, z),
        ]

    wall_offset = min(0.15, length / 5)
    x_margin = _safe_margin(width)
    return [
        _point(x_margin, wall_offset, z),
        _point(width - x_margin, wall_offset, z),
    ]


def _circuit_for_role(role: str) -> dict[str, Any]:
    circuit_names = {
        "ambient": "主照明回路",
        "task": "任务照明回路",
        "accent": "氛围照明回路",
    }
    switch_groups = {
        "ambient": "main",
        "task": "work",
        "accent": "scene",
    }

    return {
        "circuit_id": f"circuit_{role}",
        "name": circuit_names.get(role, f"{role} 回路"),
        "roles": [role],
        "switch_group": switch_groups.get(role, role),
        "control": "switch",
    }


def _placement_for_fixture(
    *,
    fixture: dict[str, Any],
    width: float,
    length: float,
    ceiling_height: float,
    index: int,
) -> dict[str, Any] | None:
    role = fixture.get("role")
    if role == "ambient":
        return {
            "placement_id": f"placement_ambient_{index}",
            "role": role,
            "fixture_id": fixture.get("fixture_id"),
            "category": fixture.get("category"),
            "placement_type": "point",
            "points": _ambient_points(width, length, ceiling_height),
            "circuit_id": "circuit_ambient",
            "switch_group": "main",
            "reason": "按矩形房间尺寸生成基础主照明点位，第一批仅做中心或均匀布点。",
        }

    if role == "task":
        return {
            "placement_id": f"placement_task_{index}",
            "role": role,
            "fixture_id": fixture.get("fixture_id"),
            "category": fixture.get("category"),
            "placement_type": "point",
            "points": _task_points(width, length),
            "circuit_id": "circuit_task",
            "switch_group": "work",
            "reason": "未提供家具位置时，任务照明先落在默认靠墙工作区。",
        }

    if role == "accent":
        return {
            "placement_id": f"placement_accent_{index}",
            "role": role,
            "fixture_id": fixture.get("fixture_id"),
            "category": fixture.get("category"),
            "placement_type": "segment",
            "points": _accent_segment(width, length, ceiling_height),
            "circuit_id": "circuit_accent",
            "switch_group": "scene",
            "reason": "沿一侧长边墙生成单条氛围线段，第一批不做复杂造型。",
        }

    return None


def generate_single_room_layout(requirement_spec: dict[str, Any], fixture_selection: dict[str, Any]) -> dict[str, Any]:
    """生成第 4 周第一批最小布局结果。

    该函数是纯业务规则层：不读 DB、不写状态，只根据结构化需求和已选灯具生成 layout_plan。
    """
    dimensions = requirement_spec.get("dimensions") or {}
    width = _as_float(dimensions["width"])
    length = _as_float(dimensions["length"])
    ceiling_height = _as_float(requirement_spec["ceiling_height"])
    selected_fixtures = fixture_selection.get("selected_fixtures") or []

    placements: list[dict[str, Any]] = []
    unresolved_fixtures: list[dict[str, Any]] = []
    used_roles: list[str] = []

    for index, fixture in enumerate(selected_fixtures, start=1):
        role = fixture.get("role")
        placement = _placement_for_fixture(
            fixture=fixture,
            width=width,
            length=length,
            ceiling_height=ceiling_height,
            index=index,
        )
        if placement is None:
            unresolved_fixtures.append(
                {
                    "fixture_id": fixture.get("fixture_id"),
                    "role": role,
                    "reason": "第 4 周第一批只支持 ambient、task、accent 三类布局角色。",
                }
            )
            continue
        placements.append(placement)
        if role in SUPPORTED_LAYOUT_ROLES and role not in used_roles:
            used_roles.append(role)

    return {
        "status": "generated",
        "version": "layout_v1",
        "space_type": requirement_spec.get("space_type"),
        "coordinate_system": {
            "unit": "m",
            "origin": "room_lower_left_floor",
            "x_axis": "room_width",
            "y_axis": "room_length",
            "z_axis": "height",
        },
        "room": {
            "width": width,
            "length": length,
            "ceiling_height": ceiling_height,
        },
        "layout_basis": {
            "fixture_selection_version": fixture_selection.get("version"),
            "source_fixture_count": len(selected_fixtures),
            "layout_strategy": "single_room_rectangular_minimal",
        },
        "placements": placements,
        "circuit_suggestions": [_circuit_for_role(role) for role in used_roles],
        "unresolved_fixtures": unresolved_fixtures,
        "layout_warnings": [
            "未提供家具或障碍物信息，本次未执行对象避让。",
            "第一批布局只给出规则点位和回路建议，不代表照度仿真或施工图。",
        ],
        "source_rules": list(SOURCE_RULES),
    }
