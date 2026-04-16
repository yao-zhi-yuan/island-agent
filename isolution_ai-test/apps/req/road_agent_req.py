from pydantic import BaseModel, Field, model_validator
from typing import Literal


class Light(BaseModel):
    type: Literal["LED", "Na"] = Field(..., description="灯具类型")
    count: int = Field(..., description="灯具数量")
    lumens: int = Field(..., description="光通量")

class Lane(BaseModel):
    type: Literal["机动车道", "辅道", "非机动车道", "人行道", "绿化带", "水泥墩"] = Field(..., description="车道类型")
    count: Literal[0, 1, 2, 3, 4, 5, 6, 8, 10] = Field(..., description="条数")
    width: float = Field(..., description="宽度")

class Inputs(BaseModel):
    level: Literal["快速路", "主干路", "次干路", "支路"] = Field(..., description="道路等级")
    length: float = Field(0.0, description="道路长度（公里）")
    lanes: list[Lane] = Field(..., description="车道列表")
    assembleMethod: Literal["双侧对称", "双侧交错", "中心对称", "单侧", "单侧右", "单侧左"] = Field(..., description="布灯方式")
    lightArmType: Literal["平行臂", "高低臂", "单臂"] = Field(..., description="灯臂类型")
    subLightFlag: bool = Field(False, description="是否有辅助照明灯")
    subLightArmType: Literal["高低臂", "单臂", ""] = Field("", description="辅助照明灯臂类型")
    lightPole: bool = Field(True, description="是否有灯杆")
    planType: Literal["灯具改造", "新建道路", "EMC"] = Field(..., description="方案类型")
    lights: list[Light] = Field([], description="改造灯具列表")
    lightNum: int = Field(0, description="灯具数量(灯具改造)")
    tag: str = Field("", description="标签")
    text: str = Field("", description="设计要求")
    splitType: Literal["", "中央分隔带", "侧分隔带", "中央分隔带+侧分隔带", "无分隔带"] = Field("", description="隔离带类型")
    lightRoadGap: float = Field(0.0, description="灯杆距路沿石间距")
    lightPoleHeight: float = Field(0.0, description="灯杆高度")
    mainLightHeight: float = Field(0.0, description="主灯高度")
    subLightHeight: float = Field(0.0, description="辅灯高度")
    mainLightArmLength: float = Field(0.0, description="主灯臂长度")
    subLightArmLength: float = Field(0.0, description="辅灯臂长度")
    mainLightArmAngle: float = Field(0.0, description="主灯臂仰角")
    subLightArmAngle: float = Field(0.0, description="辅灯臂仰角")
    mainLightAngle: float = Field(0.0, description="主灯灯头仰角")
    subLightAngle: float = Field(0.0, description="辅灯灯头仰角")
    lightMaintenanceFactor: float = Field(0.7, description="灯具维护系数")
    lightGap: float = Field(0.0, description="灯具间距")
    
class RoadAgentReq(BaseModel):
    inputs: Inputs
    user: str = Field(..., description="用户ID")