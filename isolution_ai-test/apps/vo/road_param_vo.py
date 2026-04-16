
from typing import Optional
from pydantic import BaseModel, Field


class Data(BaseModel):
    lightRoadGap: float = Field(0.5, description="灯杆距路沿石间距")
    lightPoleHeight: float = Field(0.0, description="灯杆高度")
    mainLightHeight: float = Field(0.0, description="主灯高度")
    subLightHeight: float = Field(0.0, description="辅灯高度")
    mainLightArmLength: float = Field(0.0, description="主灯臂长度")
    subLightArmLength: float = Field(0.0, description="辅灯臂长度")
    mainLightArmAngle: float = Field(0.0, description="主灯臂仰角")
    subLightArmAngle: float = Field(0.0, description="辅灯臂仰角")
    lightGap: float = Field(0.0, description="灯具间距")
    length: float = Field(0.0, description="道路长度（公里）")

class RoadParamVo(BaseModel):
    """
    Response model for the road agent design.
    """
    code: int = Field(..., description="相应的状态码")
    msg: str = Field("", description="消息")
    data: Optional[Data] = Field(None, description="参数")
