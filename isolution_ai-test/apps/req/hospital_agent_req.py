from pydantic import BaseModel, Field, model_validator
from typing import Literal, Optional


class HospitalInputs(BaseModel):
    model_config = {"populate_by_name": True}

    roomType: Literal[
        "病房", "诊疗室", "护士站", "走廊"
    ] = Field(..., description="房间类型")

    # Dimensions
    width: Optional[float] = Field(None, description="房间宽度（米）")
    length: Optional[float] = Field(None, description="房间长度（米）")
    height: float = Field(3.0, description="房间高度（米）")

    # Layout parameters
    bedNum: Optional[int] = Field(0, description="病床数量")
    hasToilet: Optional[int] = Field(0, description="是否有卫生间 (0: 否, 1: 是)")
    roomPolyType: Optional[Literal["L", "U", "一"]] = Field(None, description="房间形状类型")

    # Size parameters for complex shapes
    size1: Optional[float] = Field(None, description="尺寸 1", alias="size_1")
    size2: Optional[float] = Field(None, description="尺寸 2", alias="size_2")
    size3: Optional[float] = Field(None, description="尺寸 3", alias="size_3")
    size4: Optional[float] = Field(None, description="尺寸 4", alias="size_4")
    size5: Optional[float] = Field(None, description="尺寸 5", alias="size_5")
    size6: Optional[float] = Field(None, description="尺寸 6", alias="size_6")

    sdlGap: Optional[float] = Field(0.1, description="天幕间距", alias="sdlGap")

    # Common parameters
    tags: str = Field("", description="标签")
    text: str = Field("", description="设计要求")

    # Computed fields for nurse station
    roomPolyLS: Optional[list] = Field(None, description="房间多边形列表", exclude=True)
    outerPoly: Optional[list] = Field(None, description="外部多边形", exclude=True)
    nurseW: Optional[float] = Field(None, description="护士站宽度", exclude=True)

    @model_validator(mode="after")
    def validate_dimensions(self):
        """Validate dimensions"""
        if not self.width:
            self.width = 0.0
        if not self.length:
            self.length = 0.0
        if not self.height:
            self.height = 3.0
        if self.roomType == "病房":
            if self.bedNum not in [1, 2, 3]:
                raise ValueError("病床数请输入1~3")
            if self.bedNum == 1 and self.length < 5:
                raise ValueError("单人间长度不能小于5m")
            if self.width < 3.5:
                raise ValueError("房间宽度不能小于3.5m")
            if not self.hasToilet and self.length < 2.5 * self.bedNum:
                raise ValueError("房间长度过小")
            if self.hasToilet and self.length < 2.5 * self.bedNum + 2:
                raise ValueError("房间长度过小")
            if "节律" in self.tags:
                self.tags = "节律光方案"
            elif "疗愈" in self.tags:
                self.tags = "疗愈光方案"
            elif "品质" in self.tags:
                self.tags = "品质光方案"
            else:
                self.tags = "品质光方案"
        elif self.roomType == "诊疗室":
            if self.width < 3:
                raise ValueError("房间宽度不能小于3m")
            if self.length < 4:
                raise ValueError("房间长度不能小于4m")
            if "清澈" in self.tags:
                self.tags = "清澈光方案"
            elif "舒适" in self.tags:
                self.tags = "舒适光方案"
            else:
                self.tags = "舒适光方案"
            if self.length < self.width:
                self.length, self.width = self.width, self.length

        elif self.roomType == "护士站":
            if self.roomPolyType:
                s1, s2, s3, s4, s5, s6 = (
                    self.size1 or 0.0,
                    self.size2 or 0.0,
                    self.size3 or 0.0,
                    self.size4 or 0.0,
                    self.size5 or 0.0,
                    self.size6 or 0.0,
                )
                
                room_poly_ls = []
                outer_poly = []
                nurse_w, nurse_h = 0.0, 0.0
                if self.roomPolyType == "一":
                    self.width = s3 + s5
                    self.length = s1 + s2 + s4
                    
                    room_poly_ls.append({
                        "type": "护士站",
                        "poly": [[s1, 0], [s1 + s2, 0], [s1 + s2, s3], [s1, s3]]
                    })
                    room_poly_ls.append({
                        "type": "过道",
                        "poly": [[0, s3], [self.length, s3], [self.length, self.width], [0, self.width]]
                    })
                    outer_poly = [
                        [0, s3], [s1, s3], [s1, 0], [s1 + s2, 0], [s1 + s2, s3],
                        [s1 + s2 + s4, s3], [s1 + s2 + s4, s3 + s5], [0, s3 + s5]
                    ]
                elif self.roomPolyType == "L":
                    nurse_w, nurse_h = s2, s4
                    self.width = s4 + s5
                    self.length = s1 + s2 + s3
                    
                    room_poly_ls.append({
                        "type": "护士站",
                        "poly": [[s1, 0], [s1 + s2, 0], [s1 + s2, s4], [s1, s4]]
                    })
                    room_poly_ls.append({
                        "type": "过道",
                        "poly": [[0, s4], [s1 + s2, s4], [s1 + s2, 0], [self.length, 0], [self.length, self.width], [0, self.width]]
                    })
                    outer_poly = [
                        [0, s4], [s1, s4], [s1, 0], [s1 + s2 + s3, 0], [s1 + s2 + s3, s4 + s5], [0, s4 + s5]
                    ]
                elif self.roomPolyType == "U":
                    self.width = s2 + s5 + s6
                    self.length = s1 + s3 + s4
                    
                    room_poly_ls.append({
                        "type": "护士站",
                        "poly": [[s1, s2], [s1 + s3, s2], [s1 + s3, s2 + s5], [s1, s2 + s5]]
                    })
                    room_poly_ls.append({
                        "type": "过道",
                        "poly": [[0, 0], [s1, 0], [s1, s2 + s5], [s1 + s3, s2 + s5], [s1 + s3, 0], [self.length, 0], [self.length, self.width], [0, self.width]]
                    })
                    outer_poly = [
                        [0, 0], [s1, 0], [s1, s2], [s1 + s3, s2], [s1 + s3, 0], [s1 + s3 + s4, 0],
                        [s1 + s3 + s4, s2 + s5 + s6], [0, s2 + s5 + s6]
                    ]
                for room_poly in room_poly_ls:
                    if room_poly["type"] == "护士站":
                        nurse_poly = room_poly["poly"]
                        nurse_w = round(nurse_poly[2][0] - nurse_poly[0][0], 1)
                        nurse_h = round(nurse_poly[2][1] - nurse_poly[0][1], 1)

                if nurse_w < 4:
                    raise ValueError("护士站长度不能小于4m")
                if nurse_h < 2:
                    raise ValueError("护士站宽度不能小于2m")
                self.roomPolyLS = room_poly_ls
                self.outerPoly = outer_poly
                self.nurseW = nurse_w
            
            if "节律" in self.tags:
                self.tags = "节律光方案"
            else:
                self.tags = "节律光方案"
        elif self.roomType == "走廊":
            if "舒适" in self.tags:
                self.tags = "舒适光方案"
            elif "节能" in self.tags:
                self.tags = "节能光方案"
            else:
                self.tags = "舒适光方案"
            if self.width < 1.5:
                raise ValueError("走廊宽度不能小于1.5m")
            if self.length < 5:
                raise ValueError("走廊长度不能小于5m")
        if self.width <= 0 or self.length <= 0 or self.height <= 0:
            raise ValueError("Dimensions must be positive")
        return self


class HospitalAgentReq(BaseModel):
    inputs: HospitalInputs
    user: str = Field(..., description="用户ID")
