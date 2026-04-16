from typing import Optional
from pydantic import BaseModel, Field


class MetroParamVo(BaseModel):
    code: int = Field(..., description="状态码")
    msg: str = Field("", description="消息")
    data: Optional[dict] = Field(None, description="参数数据")
