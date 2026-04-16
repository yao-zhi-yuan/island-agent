from pydantic import BaseModel, Field, model_validator
from typing import Literal, Optional


# 请求编程下面的参数了
# 外部字段 -> 内部字段映射示例见 alias

# curl -v -X POST http://127.0.0.1:9001/metro_agent \
#   -H "Content-Type: application/json" \
#   -d '{"inputs":{"customerServiceLength":3.6,"customerServiceWidth":2.5,"height":7.0,"innerCorridorWidth":16.5,"outerCorridorWidth":19.5,"outerCorridorWidth2":3.0,"roomType":"站厅","shapeChoose":"类型二","stationLength":112.0,"tags":"tags","text":"text"},"user":"32"}'

class Inputs(BaseModel):
    model_config = {"populate_by_name": True}

    roomType: Literal[
        "customerService", "stationHall", "platform", "controlRoom",
        "客服中心", "站厅", "站台", "控制室"
    ] = Field(
        0, description="空间类型", alias="roomType"
    )

    # accept incoming name 'height'
    roomHeight: float = Field(
        0.0, description="空间高度（米）", alias="height"
    )

    # accept incoming name 'stationLength'
    roomLength: float = Field(
        0.0, description="空间长度（米）", alias="stationLength"
    )

    # accept incoming name 'stationWidth'
    roomWidth: float = Field(
        0.0, description="空间宽度（米）", alias="stationWidth"
    )

    customerServiceWidth: float = Field(
        0.0, description="客服空间宽度（米）", alias="customerServiceWidth"
    )

    customerServiceLength: float = Field(
        0.0, description="客服空间长度（米）", alias="customerServiceLength"
    )

    # accept incoming name 'innerCorridorWidth'
    innerPassWidth: float = Field(
        0, description="站厅内通道宽度（米）", alias="innerCorridorWidth"
    )

    # internal field; computed from shapeChoose when needed
    outerPassWidth_1: float = Field(
        0.0, description="站厅外通道宽度", alias="outerCorridorWidth2"
    )

    # accept incoming name 'outerCorridorWidth'
    outerPassWidth_2: float = Field(
        0.0, description="站厅外通道宽度",
        alias="outerCorridorWidth",
    )

    # accept incoming 'shapeChoose' to infer outerPassWidth_1
    shapeChoose: Optional[str] = Field(None, alias="shapeChoose")

    tag: str = Field("", description="标签", alias="tags")
    text: str = Field("", description="设计要求", alias="text")

    @model_validator(mode="after")
    def normalize_and_validate(self):
        """Normalize and validate fields after model creation"""
        if self.roomWidth <= 0:
            self.roomWidth = self.outerPassWidth_1 + self.outerPassWidth_2 + self.innerPassWidth
        if self.roomWidth <= 0:
            raise ValueError("空间宽度必须大于0")
        return self


class MetroAgentReq(BaseModel):
    inputs: Inputs
    user: str = Field(..., description="用户ID")
