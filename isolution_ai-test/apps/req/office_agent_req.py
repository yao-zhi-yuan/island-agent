from pydantic import BaseModel, Field, model_validator
from typing import Literal, Optional


class OfficeInputs(BaseModel):
    model_config = {"populate_by_name": True}

    officeType: Literal[
        "独立办公室", "开放办公区", "多功能会议厅", "会议室"
    ] = Field(
        ..., description="办公空间类型", alias="roomType"
    )

    # Dimensions
    # Using specific names but allowing aliases for consistency
    officeLength: float = Field(
        0.0, description="空间长度（米）", alias="length"
    )
    officeWidth: float = Field(
        0.0, description="空间宽度（米）", alias="width"
    )
    officeHeight: float = Field(
        0.0, description="空间高度（米）", alias="height"
    )

    # Common parameters
    tag: str = Field("", description="标签", alias="tags")
    text: str = Field("", description="设计要求", alias="text")
    sdlGap: Optional[float] = Field(None, description="天幕缝隙", alias="sdlGap")

    @model_validator(mode="after")
    def validate_dimensions(self):
        """Validate dimensions"""
        if self.officeLength <= 0 or self.officeWidth <= 0 or self.officeHeight <= 0:
            raise ValueError("Dimensions must be positive")

        # Enforce officeLength as the longer dimension (X axis) for other types
        # Skip for Meeting Rooms to respect user-specified orientation
        if self.officeType not in ["会议室"] and self.officeLength < self.officeWidth:
            self.officeLength, self.officeWidth = self.officeWidth, self.officeLength
        # Enforce officeWidth as the longer dimension (Y axis) for Meeting Rooms
        if self.officeType == "会议室":
            if self.officeLength > self.officeWidth:
                self.officeLength, self.officeWidth = self.officeWidth, self.officeLength

            # Always normalize tag for Meeting Room
            if self.tag:
                if "SDL" in self.tag or "天幕" in self.tag:
                    self.tag = "SDL 天幕方案"
                elif "品质光" in self.tag:
                    self.tag = "品质光方案"
                elif "舒适光" in self.tag:
                    self.tag = "舒适光方案"
                else:
                    self.tag = "品质光方案"
        return self


class OfficeAgentReq(BaseModel):
    inputs: OfficeInputs
    user: str = Field(..., description="用户ID")
