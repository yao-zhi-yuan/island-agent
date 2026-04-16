from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# 这里集中定义 lighting 模块的 Pydantic schema。
# Pydantic schema 可以理解为“接口和状态的数据契约”：API 入参、出参、数据库读回的数据都按它校验。
class ProjectState(BaseModel):
    """照明设计项目的最小状态容器。

    Step 1A 只负责把状态持久化跑通，所以各阶段先保留为 dict。
    后续接入选型、布局、校验工具时，再逐步把这些 dict 收紧成更严格的结构。
    """

    # 当前项目推进到哪个阶段；第一周默认停在需求阶段。
    stage: str = Field(default="requirement", min_length=1, max_length=50)
    # 用户需求结构化结果，例如空间类型、风格、预算等。
    requirement_spec: dict[str, Any] = Field(default_factory=dict) # default_factory=dict默认创建空字典，千万不能写 default={}（Pydantic 安全规范）
    # 空间几何信息，例如长宽高、坐标系、功能区等。
    geometry_spec: dict[str, Any] = Field(default_factory=dict)
    # 设计策略，例如目标照度、色温、显指、预算等级等。
    design_strategy: dict[str, Any] = Field(default_factory=dict)
    # Selection Tool 写入的设备/灯具选型结果。
    # 第 3 周第一批只约定最小结构：status、version、selection_basis、
    # selected_fixtures、unresolved_roles、selection_warnings、source_rules。
    fixture_selection: dict[str, Any] = Field(default_factory=dict)
    # 后续 Layout Tool 写入的灯位坐标和布局结果。
    layout_plan: dict[str, Any] = Field(default_factory=dict)
    # 后续 Validation/Critic 写入的质量校验结果。
    quality_report: dict[str, Any] = Field(default_factory=dict)
    # 后续报告、BOM、图纸等交付物的引用信息。
    delivery_package: dict[str, Any] = Field(default_factory=dict)


class CreateLightingProjectRequest(BaseModel):
    """创建项目的最小入参。

    session_id 用于把设计项目和一次聊天会话关联起来，但不强制要求。
    initial_requirement 会被保存进 ProjectState，方便后续 Agent 接着处理。
    """

    session_id: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=120)
    initial_requirement: str | None = Field(default=None, max_length=4000)


class UpdateProjectStateRequest(BaseModel):
    """PATCH state 的请求体。

    Step 1A 的核心验收点就是：外部传入一个 ProjectState，服务端能完整持久化并读回。
    """

    project_state: ProjectState


class LightingProjectResponse(BaseModel):
    """照明项目 API 的统一响应。

    返回 project_state 是为了让前端、验证脚本或后续 Agent 都能拿到同一份权威项目状态。
    """

    id: str
    # user_id 用于多用户数据隔离：每个用户只能读写自己的项目。
    user_id: str
    session_id: str | None = None
    title: str
    project_state: ProjectState
    created_at: datetime
    updated_at: datetime
