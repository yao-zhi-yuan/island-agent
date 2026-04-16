from pydantic import BaseModel, Field
from typing import Optional


class HospitalAgentVo(BaseModel):
    """
    Response model for the hospital agent design.
    """
    roomInfo: list[dict] = Field(..., description="房间信息")
    planList: list[dict] = Field(..., description="设计方案列表")
    outer_poly: Optional[str] = Field(None, description="外部多边形")
    code: int = Field(..., description="相应的状态码")
    msg: str = Field("", description="消息")
    outputType: int = Field(0, description="0 方案 1 对话")
