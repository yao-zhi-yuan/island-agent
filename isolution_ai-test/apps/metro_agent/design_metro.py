from copy import deepcopy
from apps.req.metro_agent_req import Inputs, MetroAgentReq
from apps.metro_agent.prod_selector import metro_selector
from apps.metro_agent.asset_info import assets_info
from apps.metro_agent.control_room_selector import ControlRoomDesign

class DesignMetro:

    def __init__(self, plan_type):
        self.design_concept_dict = {
            "SDL方案": "服务台并非只是照亮空间，它更是乘客流通的关键要素。这款灯具运用欧普特殊光谱的SDL，能够根据站点特色输出定制光色。当乘客出入站有疑问需寻求帮助时，可以为他们快速定位识别到客服中心的位置，彩色光让距离有效性得到很大提升，为客服中心营造出炫而不俗、均匀明亮的光环境，下出光柔和明亮，满足沟通需求，舒适无眩光，有利于工作人员与乘客的沟通交流。",
            "清晰光": "站厅通道的照明需求非常明确，要保证乘客的通行安全，光环境舒适明亮。在满足基本功能需求下，灯具的布置形式有序列性或者秩序感，可以起到很好的指引性，让通行更加流畅。",
            "高效光": "站厅通道的照明需求非常明确，要保证乘客的通行安全，光环境舒适明亮。在满足基本功能需求下，灯具的布置形式有序列性或者秩序感，可以起到很好的指引性，让通行更加流畅。" ,    
            "品质光": "控制室由于工作类型，工作时间长，精力高度集中，容易出现焦虑、疲惫。所以采用专业光谱缓解情绪，调节节律，促进夜班工作人员的睡眠问题。",
            "节律光": "控制室由于工作类型，工作时间长，精力高度集中，容易出现焦虑、疲惫。所以采用专业光谱缓解情绪，调节节律，促进夜班工作人员的睡眠问题。",
        }
        chosen_type = plan_type if plan_type in self.design_concept_dict else "清晰光"
        self.planInfo = {
            "id": 1,
            "name": chosen_type,
            "designConcept": self.design_concept_dict[chosen_type],
            "sellingKeywords": "欧普清晰光",
            "sellingDescription": "高效指引、提升通行辨识度",
            "designConceptCustomer": self.design_concept_dict["SDL方案"],
            "sellingKeywordsCustomer": "欧普特色光（SDL）",
            "sellingDescriptionCustomer": "城市名片打造，高效辨识",
        }

    def _get_product_info(self, category1, series, power=None, color_temp=None, installation=None, opening=None):
        """获取产品的完整信息
        
        Args:
            category1: 一级分类名称 (e.g., "线形灯具", "筒灯", "模组", "低压灯带")
            series: 系列名称
            power: 功率(w)
            color_temp: 色温(k)
            installation: 安装方式 ("嵌装" or "吊线")
            opening: 开孔尺寸 (for 筒灯)
            
        Returns:
            dict: 包含 materialCode, lumen, efficiency, ra 的字典，如果未找到返回 None
        """
        try:
            if category1 == "线形灯具":
                result = metro_selector.select_linear_fixture(
                    series=series,
                    power=power,
                    color_temp=color_temp,
                    installation=installation
                )
            elif category1 == "筒灯":
                result = metro_selector.select_recessed_downlight(
                    series=series,
                    power=power,
                    color_temp=color_temp,
                    opening=opening
                )
            elif category1 == "模组":
                result = metro_selector.select_module(
                    series=series,
                    color_temp_range=color_temp
                )
            elif category1 == "低压灯带":
                result = metro_selector.select_led_strip(
                    series=series,
                    color_temp_range=color_temp
                )
            else:
                return None

            if len(result) > 0:
                prod = result.iloc[0]

                # 获取基本参数
                lumen = float(prod["光通量(lm)"]) if prod.get("光通量(lm)") and str(prod.get("光通量(lm)")) != "nan" else None
                efficiency = float(prod["光效(lm/w)"]) if prod.get("光效(lm/w)") and str(prod.get("光效(lm/w)")) != "nan" else None

                # 尝试从产品数据中获取功率（如果调用时未提供）
                if power is None:
                    power = float(prod["功率(w)"]) if prod.get("功率(w)") and str(prod.get("功率(w)")) != "nan" else None

                # 如果光通量为空，但有光效和功率，则计算光通量
                # lumen = efficiency × power
                if lumen is None and efficiency is not None and power is not None:
                    lumen = efficiency * power
                    print(f"计算光通量: {efficiency} lm/W × {power} W = {lumen} lm")

                # 返回完整产品信息（包括power）
                return {
                    "materialCode": str(prod["物料号"]),
                    "power": power,  # 添加功率信息
                    "lumen": lumen,
                    "efficiency": efficiency,
                    "ra": int(prod["显色指数(ra)"]) if prod.get("显色指数(ra)") and str(prod.get("显色指数(ra)")) != "nan" else None,
                }
            else:
                return None
        except Exception as e:
            print(f"Error getting product info: {e}")
            return None

    def design_customer_service(self, roomList, data: Inputs):
        """客服中心灯具打点"""

        # 客服中心是在站厅内通道的objects中，而不是独立房间
        # 先找到站厅内通道房间
        inner_pass = next((room for room in roomList if room.get("name") == "站厅内通道"), None)
        if not inner_pass:
            planInfo = deepcopy(self.planInfo)
            planInfo["products"] = []
            return planInfo

        # 从objects中找到客服中心的位置
        customer_service_obj = None
        for obj in inner_pass.get("objects", []):
            if (obj.get("type") == "客服中心"):
                customer_service_obj = obj
                break

        if not customer_service_obj or not customer_service_obj.get("locations"):
            planInfo = deepcopy(self.planInfo)
            planInfo["products"] = []
            return planInfo

        # 从客服中心的location获取位置信息
        loc = customer_service_obj["locations"][0]
        center_x = loc["x"]
        center_y = loc["y"]
        width = loc["w"]   # customerServiceLength
        height = loc["h"]  # customerServiceWidth

        # 计算边界（基于中心点和尺寸）
        x_min = center_x - width / 2
        x_max = center_x + width / 2
        y_min = center_y - height / 2
        y_max = center_y + height / 2

        # 上发光位置（在四边对称放置）
        upper_locs = [
            {
                "x": (x_max + x_min) / 2,
                "y": y_min + 0.25,
                "z": data.roomHeight - 1.4,
                "w": data.customerServiceLength,
                "h": 0.15,
                "l": 0.1,
                "rotation": [0, 0, 0],
            },
            {
                "x": (x_max + x_min) / 2,
                "y": y_max - 0.25,
                "z": data.roomHeight - 1.4,
                "w": data.customerServiceLength,
                "h": 0.15,
                "l": 0.1,
                "rotation": [0, 0, 0],
            },
            {
                "x": x_min + 0.25,
                "y": (y_max + y_min) / 2,
                "z": data.roomHeight - 1.4,
                "w": max(0.1, data.customerServiceWidth - 1),
                "h": 0.15,
                "l": 0.1,
                "rotation": [0, 0, 90],
            },
            {
                "x": x_max - 0.25,
                "y": (y_max + y_min) / 2,
                "z": data.roomHeight - 1.4,
                "w": max(0.1, data.customerServiceWidth - 1),
                "h": 0.15,
                "l": 0.1,
                "rotation": [0, 0, 90],
            },
        ]
        # 一米一个
        upper_locs = [
            {
                "x": x_min + i,
                "y": y_min + 0.25,
                "z": data.roomHeight - 1.3,
                "w": 1.0,
                "h": 0.15,
                "l": 0.1,
                "rotation": [180, 0, 0],
            } for i in range(int(data.customerServiceLength+1))
        ] + [
            {
                "x": x_min + i,
                "y": y_max - 0.25,
                "z": data.roomHeight - 1.3,
                "w": 1.0,
                "h": 0.15,
                "l": 0.1,
                "rotation": [180, 0, 0],
            } for i in range(int(data.customerServiceLength+1))
        ] + [
            {
                "x": x_min + 0.25,
                "y": y_min + j,
                "z": data.roomHeight - 1.3,
                "w": 1.0,
                "h": 0.15,
                "l": 0.1,
                "rotation": [180, 0, 90],
            } for j in range(1, int(data.customerServiceWidth+1))
        ] + [
            {
                "x": x_max - 0.25,
                "y": y_min + j,
                "z": data.roomHeight - 1.3,
                "w": 1.0,
                "h": 0.15,
                "l": 0.1,
                "rotation": [180, 0, 90],
            } for j in range(1, int(data.customerServiceWidth+1))
        ]
        # 获取SDL模组的完整产品信息
        module_info = self._get_product_info(
            category1="模组",
            series="天幕",
            color_temp="1800-12000"
        )

        upper_lights = {
            "materialCode": module_info["materialCode"] if module_info else None,
            "power": module_info["power"] if module_info else None,
            "lumen": module_info["lumen"] if module_info else None,
            "lmEff": module_info["efficiency"] if module_info else None,
            "CRI": module_info["ra"] if module_info else None,
            "category1": "模组",
            "category2": "条形模组",
            "series": "天幕",
            "algoKeyword": "天幕灯具",
            "location": upper_locs,
            "angle": [0, 0, 0, 0, 1, 0],
            "colorTemperature": "1800-12000",
            "dynamicSize": True,
            "count": int(
                (data.customerServiceLength + data.customerServiceWidth) * 2
                - 1
                + 0.9999
            ),
            "area": "客服中心",
        }
        lower_locs = [
            {
                "x": x_min + i,
                "y": y_min + 0.25,
                "z": data.roomHeight - 1.4,
                "w": 1.0,
                "h": 0.15,
                "l": 0.1,
                "rotation": [0, 0, 0],
            } for i in range(int(data.customerServiceLength+1))
        ] + [
            {
                "x": x_min + i,
                "y": y_max - 0.25,
                "z": data.roomHeight - 1.4,
                "w": 1.0,
                "h": 0.15,
                "l": 0.1,
                "rotation": [0, 0, 0],
            } for i in range(int(data.customerServiceLength+1))
        ] + [
            {
                "x": x_min + 0.25,
                "y": y_min + j,
                "z": data.roomHeight - 1.4,
                "w": 1.0,
                "h": 0.15,
                "l": 0.1,
                "rotation": [0, 0, 90],
            } for j in range(1, int(data.customerServiceWidth+1))
        ] + [
            {
                "x": x_max - 0.25,
                "y": y_min + j,
                "z": data.roomHeight - 1.4,
                "w": 1.0,
                "h": 0.15,
                "l": 0.1,
                "rotation": [0, 0, 90],
            } for j in range(1, int(data.customerServiceWidth+1))
        ]

        # 下发光（使用相同的位置示例,使用低压灯带, 光跃 Ray）
        module_info = self._get_product_info(
            category1="低压灯带",
            series="光跃 Ray",
            color_temp="1800-12000"
        )   
        lower_lights = {
            "materialCode": module_info["materialCode"] if module_info else None,
            "power": module_info["power"] if module_info else None,
            "lumen": module_info["lumen"] if module_info else None,
            "lmEff": module_info["efficiency"] if module_info else None,
            "CRI": module_info["ra"] if module_info else None,
            "category1": "低压灯带",
            "category2": "SMD低压灯带",
            "series": "光跃 Ray",
            "algoKeyword": "天幕灯具",
            "location": lower_locs,
            "angle": [0, 0, 0, 0, 0, 1],
            "colorTemperature": "4000",
            "dynamicSize": True,
            "count": int(
                (data.customerServiceLength + data.customerServiceWidth) * 2
                - 1
                + 0.9999
            ),
            "area": "客服中心"
        }

        planInfo = deepcopy(self.planInfo)
        planInfo["products"] = [upper_lights, lower_lights]

        return planInfo

    def design_station_hall(self, roomList, data: Inputs):
        """站厅通道灯具打点

                根据方案类型布置线形灯和筒灯:
                - 清晰光: 只布置线形灯(恒型40W):
                        通道宽<=9米时，站厅内通道居中布置两条线型灯，1.2米每条，排成一字型; 
                        通道宽≥9米横向布置两条线型灯，每增加3米对应增加1排线型灯）
                - 高效光: 线形灯(恒18W) + 筒灯(佳8W)
        """

        products = []

        # 处理所有通道房间
        corridor_rooms = [
            room
            for room in roomList
            if room.get("name") in ["站厅外通道1", "站厅外通道2", "站厅内通道"]
        ]
        margin = 1.5
        for room in corridor_rooms:
            # room_name = room.get("name", "")
            room_name = "站厅"
            rect = room.get("rectangle", {})

            x_min = 0 + margin
            x_max = data.roomLength - margin
            y_min = rect.get("y_min", 0)
            y_max = rect.get("y_max", 0)

            # 检查通道是否存在（ymax > 0）
            if y_max <= 0:
                print(f"跳过不存在的通道: {room.get('name', '')}, y_max={y_max}")
                continue

            # 计算通道尺寸
            # 注意：在station_hall_rooms.json中，X是长度方向，Y是宽度方向
            corridor_length = x_max - x_min  # X方向是长度
            corridor_width = y_max - y_min   # Y方向是宽度

            # 根据宽度计算行数 (每4m一排，每增加3m增加一排)
            num_rows = 1
            if corridor_width > 4:
                num_rows = 1 + int((corridor_width - 4) / 3)

            # 计算灯具间距
            # 默认水平间距：点线/通道方案使用3.0m；但“清晰光”默认1.2m（可在调用时通过
            # data.linear_fixture_spacing 自定义）。如果提供通用覆盖可使用 data.fixture_spacing。
            default_spacing = 3.0
            if self.planInfo.get("name") == "清晰光":
                # 清晰光默认更密的间距（1.2m），可通过 data.linear_fixture_spacing 自定义
                spacing = getattr(data, 'linear_fixture_spacing', None)
                if spacing is None:
                    spacing = 1.2
            else:
                spacing = getattr(data, 'fixture_spacing', default_spacing)

            try:
                fixture_spacing = float(spacing)
            except Exception:
                fixture_spacing = default_spacing

            # 计算每排灯具数量（向上取整，至少1个）
            num_fixtures_per_row = max(
                1,
                int(corridor_length / fixture_spacing) + 1
            )

            # 计算行间距（在Y方向，即宽度方向）
            if num_rows == 1:
                row_y_positions = [corridor_width / 2]
            else:
                row_spacing = corridor_width / (num_rows + 1)
                row_y_positions = [
                    row_spacing * (i + 1) for i in range(num_rows)
                ]

            # 根据方案类型生成灯具点位
            if self.planInfo["name"] in ["清晰光"]:
                # 方案1: 只布置线形灯 (恒型18W, 嵌入式)
                linear_locs = []
                for row_idx, row_y in enumerate(row_y_positions):
                    for i in range(num_fixtures_per_row):
                        linear_locs.append({
                            "x": x_min + i * fixture_spacing,  # X方向排列
                            "y": y_min + row_y,                # Y方向多行
                            "z": data.roomHeight - 0.2,        # 吊顶下方
                            "w": 1.2,  #
                            "h": 0.15,  # 
                            "l": 0.035,  # 高度
                            "rotation": [0, 0, 0]
                        })

                # 获取线形灯完整产品信息
                linear_info = self._get_product_info(
                    category1="线形灯具",
                    series="恒",
                    power=18,
                    color_temp=4000,
                    installation="吊线"
                )
                print(linear_info)
                products.append({
                    "materialCode": linear_info["materialCode"],
                    "lumen": linear_info["lumen"] if linear_info else None,
                    "lmEff": linear_info["efficiency"] if linear_info else None,
                    "CRI": linear_info["ra"] if linear_info else None,
                    "category1": "线形灯具",
                    "category2": "吊线式线形",
                    "series": "恒",
                    "power": linear_info["power"],
                    "colorTemperature": "4000",
                    "location": linear_locs,
                    "count": len(linear_locs),
                    "angle": [0, 0, 0, 0, 0, 1],
                    "area": room_name
                })

            elif self.planInfo["name"] in ["高效光"]:
                # 方案2: 线形灯 + 筒灯 (恒18W + 佳8W)
                # 新规则：
                # - 通道宽≤4米：1个线型灯+2个筒灯
                # - 每增加3米宽度：增加1条线型灯+1个筒灯
                # - X方向灯间距3米，均匀分布
                self.planInfo["id"] = 2
                self.planInfo["sellingKeywords"] = "欧普高效光"
                self.planInfo["sellingDescription"] = "高效指引、明亮清晰"

                # 根据通道宽度计算每个位置的灯具数量
                # 通道宽≤4米：1线型灯+2筒灯
                # 每增加3米：+1线型灯+1筒灯
                if corridor_width <= 4:
                    num_linear_per_pos = 1
                    num_downlight_per_pos = 2
                else:
                    # 每增加3米，增加1线型灯+1筒灯
                    extra_width = corridor_width - 4
                    extra_sets = int(extra_width / 3)
                    num_linear_per_pos = 1 + extra_sets
                    num_downlight_per_pos = 2 + extra_sets

                # X方向：固定间距3米，均匀分布
                x_spacing = 3.0
                num_positions = max(2, int(corridor_length / x_spacing) + 1)
                actual_x_spacing = corridor_length / (num_positions - 1) if num_positions > 1 else 0

                # Y方向：根据灯具数量均匀分布
                # 线型灯和筒灯交替排列
                total_fixtures = num_linear_per_pos + num_downlight_per_pos
                y_spacing = corridor_width / (total_fixtures + 1)

                linear_locs = []
                downlight_locs = []

                for i in range(num_positions):
                    x_pos = x_min + i * actual_x_spacing

                    # Y方向布置：线型灯和筒灯交替
                    # 从y_min开始，均匀分布所有灯具
                    fixture_y_positions = [
                        y_min + y_spacing * (j + 1) for j in range(total_fixtures)
                    ]

                    # 分配位置：先放筒灯，再放线型灯，交替排列
                    # 例如：筒灯-线型灯-筒灯-线型灯-筒灯（共3筒2线）
                    downlight_count = 0
                    linear_count = 0

                    for idx, y_pos in enumerate(fixture_y_positions):
                        # 交替布置：偶数位置放筒灯，奇数位置放线型灯
                        # 但要确保数量不超过限制
                        if idx % 2 == 0 and downlight_count < num_downlight_per_pos:
                            # 筒灯
                            downlight_locs.append({
                                "x": x_pos,
                                "y": y_pos,
                                "z": data.roomHeight - 0.2,
                                "w": 0.14,
                                "h": 0.14,
                                "l": 0.048,
                                "rotation": [0, 0, 0]
                            })
                            downlight_count += 1
                        elif idx % 2 == 1 and linear_count < num_linear_per_pos:
                            # 线型灯 (旋转90度沿Y方向)
                            linear_locs.append({
                                "x": x_pos,
                                "y": y_pos,
                                "z": data.roomHeight - 0.2,
                                "w": 1.2,
                                "h": 0.15,
                                "l": 0.08,
                                "rotation": [0, 0, 90]
                            })
                            linear_count += 1
                        elif downlight_count < num_downlight_per_pos:
                            # 如果还有筒灯没放完
                            downlight_locs.append({
                                "x": x_pos,
                                "y": y_pos,
                                "z": data.roomHeight - 0.2,
                                "w": 0.14,
                                "h": 0.14,
                                "l": 0.048,
                                "rotation": [0, 0, 0]
                            })
                            downlight_count += 1
                        elif linear_count < num_linear_per_pos:
                            # 如果还有线型灯没放完
                            linear_locs.append({
                                "x": x_pos,
                                "y": y_pos,
                                "z": data.roomHeight - 0.2,
                                "w": 1.2,
                                "h": 0.15,
                                "l": 0.08,
                                "rotation": [0, 0, 90]
                            })
                            linear_count += 1
                # 获取线形灯完整产品信息 (吊线式)
                linear_info = self._get_product_info(
                    category1="线形灯具",
                    series="恒",
                    power=18,
                    color_temp=4000,
                    installation="吊线"
                )

                # 获取筒灯完整产品信息
                downlight_info = self._get_product_info(
                    category1="筒灯",
                    series="佳",
                    power=8,
                    color_temp=4000,
                    opening=125
                )

                # 添加线形灯
                products.append({
                    "materialCode": linear_info["materialCode"] if linear_info else None,
                    "lumen": linear_info["lumen"] if linear_info else None,
                    "lmEff": linear_info["efficiency"] if linear_info else None,
                    "CRI": linear_info["ra"] if linear_info else None,
                    "category1": "线形灯具",
                    "category2": "吊线式线形",
                    "series": "恒",
                    "power": 18,
                    "colorTemperature": "4000",
                    "location": linear_locs,
                    "count": len(linear_locs),
                    "angle": [0, 0, 0, 0, 0, 1],
                    "area": room_name
                })

                # 添加筒灯
                products.append({
                    "materialCode": downlight_info["materialCode"] if downlight_info else None,
                    "lumen": downlight_info["lumen"] if downlight_info else None,
                    "lmEff": downlight_info["efficiency"] if downlight_info else None,
                    "CRI": downlight_info["ra"] if downlight_info else None,
                    "category1": "筒灯",
                    "category2": "嵌入式筒灯",
                    "series": "佳",
                    "power": 8,
                    "colorTemperature": "4000",
                    "location": downlight_locs,
                    "count": len(downlight_locs),
                    "angle": [0, 0, 0, 0, 0, 1],
                    "area": room_name
                })

        planInfo = deepcopy(self.planInfo)
        planInfo["products"] = products
        # extend products with customer service products
        customer_service_plan = self.design_customer_service(roomList, data)
        planInfo["products"].extend(customer_service_plan["products"]) 
        # 标记灯具与立柱是否冲突，如果冲突则标记到每个 location 中
        # 1) 收集房间内所有立柱的矩形边界
        pillars = []
        for room in roomList:
            for obj in room.get("objects", []):
                if obj.get("type") == "立柱":
                    for pl in obj.get("locations", []):
                        px = pl.get("x")
                        py = pl.get("y")
                        if px is None or py is None:
                            continue
                        p_size = assets_info.get("立柱", {}).get("size", [1.4, 1.0, 0])
                        p_w = float(p_size[0]) if len(p_size) > 0 else 1.4
                        p_h = float(p_size[1]) if len(p_size) > 1 else 1.0
                        pillars.append({
                            "x_min": px - p_w / 2,
                            "x_max": px + p_w / 2,
                            "y_min": py - p_h / 2,
                            "y_max": py + p_h / 2,
                        })

        # 2) 对每个产品的每个位置进行矩形相交检测，标记到 location 上
        for product in planInfo.get("products", []):
            product_conflict = False
            for loc in product.get("location", []):
                x = loc.get("x")
                y = loc.get("y")
                if x is None or y is None:
                    loc["conflictWithPillar"] = False
                    continue

                # consider rotation: if rotation around Z is ~90°, swap w/h for collision check
                rotation = loc.get("rotation", [0, 0, 0])
                try:
                    rot_z = float(rotation[2]) if len(rotation) > 2 else 0.0
                except Exception:
                    rot_z = 0.0

                fw = float(loc.get("w", 0.14))
                fh = float(loc.get("h", 0.14))
                # Normalize rotation to [0,180) and check proximity to 90°
                rot_norm = abs((rot_z % 180) - 90)
                if rot_norm < 1e-3:
                    # rotated ~90°, swap width/height for axis-aligned bbox
                    fw, fh = fh, fw

                fx_min = x - fw / 2
                fx_max = x + fw / 2
                fy_min = y - fh / 2
                fy_max = y + fh / 2

                # 检查与任一立柱是否相交（矩形相交）
                conflict = False
                for p in pillars:
                    # no-overlap conditions -> if any is true then they do NOT overlap
                    no_overlap = (fx_max < p["x_min"] or fx_min > p["x_max"] or
                                  fy_max < p["y_min"] or fy_min > p["y_max"]) 
                    if not no_overlap:
                        conflict = True
                        break

                loc["conflictWithPillar"] = bool(conflict)
                if conflict:
                    product_conflict = True

            # 同时在 product 级别记录（保持向后兼容）
            product["conflictWithPillar"] = bool(product_conflict)

        return planInfo

    def design_platform(self, roomList, data: Inputs):
        """站台灯具打点（更新）

        清晰光：
        - 线条灯固定 1.2m，不裁剪；候车区用若干 1.2m 的线条模块拼接，按 1.2m 间距居中。
        - 每列：上过道 2 筒灯（y 间距 1.2m），候车区若干线型 1.2m 单元，下过道 2 筒灯。
        - 列间距 2.5m。

        高效光：
        - 每列：上/下过道 各 1 条线 + 1 个筒灯组合；上：线位于上方，距中心 +0.65m，筒灯距中心 -0.15m
        ；下：线位于下方，距中心 -0.65m，筒灯距中心 +0.15m。
        - 候车区：中间放 1 个筒灯， 两侧按整件 1.2m 线条灯放置。最近的线条灯距离筒灯0.8m。
        - 列间距 3.5m；筒灯/线块间保持 1.2m 模数。

        不考虑穿插检测。
        """
        planInfo = deepcopy(self.planInfo)
        planInfo["products"] = []
        planInfo["designConcept"] = "站台的明需求非常明确，要保证乘客的通行安全，光环境舒适明亮。在满足基本功能需求下，灯具的布置形式有序列性或者秩序感，可以起到很好的指引性，让通行更加流畅。"
        if self.planInfo.get("name") == "清晰光":
            planInfo["id"] = 1
            planInfo["sellingKeywords"] = "欧普清晰光"
            planInfo["sellingDescription"] = "高效指引、提升通行辨识度"
        else:
            planInfo["id"] = 2
            planInfo["sellingKeywords"] = "欧普高效光"
            planInfo["sellingDescription"] = "高效指引、明亮清晰"
        # del sellingDescriptionCustomer key
        self.del_custom_service_keys(planInfo)

        # 收集目标房间（上过道 / 候车区 / 下过道）
        rooms = {
            room.get("name"): room
            for room in roomList
            if room.get("name") in ["站台上过道", "站台候车区", "站台下过道"]
        }

        top_room = rooms.get("站台上过道")
        mid_room = rooms.get("站台候车区")
        bot_room = rooms.get("站台下过道")

        if not mid_room:
            return planInfo

        def room_yrange(r):
            rect = r.get("rectangle", {}) if r else {}
            return rect.get("y_min", 0), rect.get("y_max", 0)

        top_ymin, top_ymax = room_yrange(top_room)
        mid_ymin, mid_ymax = room_yrange(mid_room)
        bot_ymin, bot_ymax = room_yrange(bot_room)

        margin = 1.5
        x_min = 0 + margin
        x_max = data.roomLength - margin
        platform_length = max(0.0, x_max - x_min)

        downlight_y_spacing = 1.2
        if self.planInfo.get("name") == "清晰光":
            group_spacing = 2.5
        else:
            group_spacing = 3.5

        # 计算列并均匀分布
        num_cols = max(1, int(platform_length / group_spacing) + 1)
        if num_cols > 1:
            x_spacing = platform_length / (num_cols - 1)
        else:
            x_spacing = 0.0

        linear_locs = []
        downlight_locs = []

        for i in range(num_cols):
            x = x_min + i * x_spacing

            # 上过道
            if top_room and (top_ymax - top_ymin) > 0:
                top_center = (top_ymin + top_ymax) / 2
                if self.planInfo.get("name") == "清晰光":
                    # 两个筒灯，y 偏移 ±0.6（间距 1.2）
                    downlight_locs.extend([
                        {
                            "x": x,
                            "y": top_center - downlight_y_spacing / 2,
                            "z": data.roomHeight - 0.2,
                            "w": 0.14,
                            "h": 0.14,
                            "l": 0.048,
                            "rotation": [0, 0, 0],
                        },
                        {
                            "x": x,
                            "y": top_center + downlight_y_spacing / 2,
                            "z": data.roomHeight - 0.2,
                            "w": 0.14,
                            "h": 0.14,
                            "l": 0.048,
                            "rotation": [0, 0, 0],
                        },
                    ])
                else:
                    # 高效光：一线一筒组合（线距中心 0.65，筒距中心 0.15）
                    linear_locs.append({
                        "x": x,
                        "y": top_center + 0.15,
                        "z": data.roomHeight - 0.2,
                        "w": 1.2,
                        "h": 0.15,
                        "l": 0.08,
                        "rotation": [0, 0, 90],
                    })
                    downlight_locs.append({
                        "x": x,
                        "y": top_center-0.65,
                        "z": data.roomHeight - 0.2,
                        "w": 0.14,
                        "h": 0.14,
                        "l": 0.048,
                        "rotation": [0, 0, 0],
                    })

            # 候车区
            mid_center = (mid_ymin + mid_ymax) / 2
            mid_width = max(0.1, mid_ymax - mid_ymin)

            if self.planInfo.get("name") == "清晰光":
                # 使用不可裁剪的 1.2m 模数拼接
                unit = 1.2
                count = max(1, int(mid_width // unit))
                # centers evenly spaced and centered on mid_center
                start_offset = - (count - 1) / 2.0 * unit
                for j in range(count):
                    y = mid_center + start_offset + j * unit
                    linear_locs.append({
                        "x": x,
                        "y": y,
                        "z": data.roomHeight - 0.2,
                        "w": unit,
                        "h": 0.15,
                        "l": 0.08,
                        "rotation": [0, 0, 90],
                    })
            else:
                # 高效光：中间替换 1.2m 的线为筒灯，两侧按整件 1.2m 放置
                unit = 1.2
                # Enforce exact pattern: 线 线 筒 线 线
                # center downlight at 0, nearest lines ±0.8, outer lines ±2.0
                offsets = [-2.0, -0.8, 0.0, 0.8, 2.0]
                half_unit = unit / 2.0
                for off in offsets:
                    y_center = mid_center + off
                    if abs(off) < 1e-6:
                        # center downlight: place if within mid area
                        if (y_center - half_unit) >= mid_ymin and \
                           (y_center + half_unit) <= mid_ymax:
                            downlight_locs.append({
                                "x": x,
                                "y": y_center,
                                "z": data.roomHeight - 0.2,
                                "w": 0.14,
                                "h": 0.14,
                                "l": 0.048,
                                "rotation": [0, 0, 0],
                            })
                        else:
                            # downlight is small; allow if inside bounds
                            if y_center >= mid_ymin and y_center <= mid_ymax:
                                downlight_locs.append({
                                    "x": x,
                                    "y": y_center,
                                    "z": data.roomHeight - 0.2,
                                    "w": 0.14,
                                    "h": 0.14,
                                    "l": 0.048,
                                    "rotation": [0, 0, 0],
                                })
                    else:
                        # linear modules: place whole 1.2m units only if they
                        # fully fit inside the mid area
                        if (y_center - half_unit) >= mid_ymin and \
                           (y_center + half_unit) <= mid_ymax:
                            linear_locs.append({
                                "x": x,
                                "y": y_center,
                                "z": data.roomHeight - 0.2,
                                "w": unit,
                                "h": 0.15,
                                "l": 0.08,
                                "rotation": [0, 0, 90],
                            })
                        # else: skip placement (insufficient space)

            # 下过道
            if bot_room and (bot_ymax - bot_ymin) > 0:
                bot_center = (bot_ymin + bot_ymax) / 2
                if self.planInfo.get("name") == "清晰光":
                    downlight_locs.extend([
                        {
                            "x": x,
                            "y": bot_center - downlight_y_spacing / 2,
                            "z": data.roomHeight - 0.2,
                            "w": 0.14,
                            "h": 0.14,
                            "l": 0.048,
                            "rotation": [0, 0, 0],
                        },
                        {
                            "x": x,
                            "y": bot_center + downlight_y_spacing / 2,
                            "z": data.roomHeight - 0.2,
                            "w": 0.14,
                            "h": 0.14,
                            "l": 0.048,
                            "rotation": [0, 0, 0],
                        },
                    ])
                else:
                    # 高效光：一线一筒组合，线距中心 -0.65，筒距中心 -0.15
                    linear_locs.append({
                        "x": x,
                        "y": bot_center - 0.15,
                        "z": data.roomHeight - 0.2,
                        "w": 1.2,
                        "h": 0.15,
                        "l": 0.08,
                        "rotation": [0, 0, 90],
                    })
                    downlight_locs.append({
                        "x": x,
                        "y": bot_center + 0.65,
                        "z": data.roomHeight - 0.2,
                        "w": 0.14,
                        "h": 0.14,
                        "l": 0.048,
                        "rotation": [0, 0, 0],
                    })

        # 获取产品信息
        linear_info = self._get_product_info(
            category1="线形灯具",
            series="恒",
            power=18,
            color_temp=4000,
            installation="吊线",
        )
        downlight_info = self._get_product_info(
            category1="筒灯",
            series="佳",
            power=8,
            color_temp=4000,
            opening=125,
        )

        # 组装 products（若某类为空则不加入）
        if linear_locs:
            # filter out any fixtures that fall inside escalator openings
            escalator_bboxes = []
            src_room = mid_room
            for obj in (src_room.get("objects", []) if src_room else []):
                if obj.get("type") == "扶梯":
                    for e_loc in obj.get("locations", []):
                        ex = e_loc.get("x", 0)
                        ey = e_loc.get("y", 0)
                        ew = e_loc.get("w", e_loc.get("width", obj.get("size", {}).get("w", 0)))
                        eh = e_loc.get("h", e_loc.get("height", obj.get("size", {}).get("h", 0)))
                        escalator_bboxes.append((
                            ex - ew/2.0,
                            ey - eh/2.0,
                            ex + ew/2.0,
                            ey + eh/2.0,
                        ))

            def _bbox_overlap(a, b):
                # a and b are (xmin, ymin, xmax, ymax)
                return not (
                    a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3]
                )

            def _loc_bbox(loc):
                # axis-aligned bbox for a fixture location; consider rot Z
                lx = loc.get("x", 0)
                ly = loc.get("y", 0)
                fw = float(loc.get("w", 0))
                fh = float(loc.get("h", 0))
                rotation = loc.get("rotation", [0, 0, 0])
                try:
                    rot_z = float(rotation[2]) if len(rotation) > 2 else 0.0
                except Exception:
                    rot_z = 0.0
                # if rotated ~90 degrees, swap width/height for AABB
                rot_norm = abs((rot_z % 180) - 90)
                if rot_norm < 1e-3:
                    fw, fh = fh, fw
                return (lx - fw/2.0, ly - fh/2.0, lx + fw/2.0, ly + fh/2.0)

            if escalator_bboxes:
                # iterative removal until stable using stricter criteria
                def _filter_list(locs):
                    filtered = []
                    removed_count = 0
                    for loc in locs:
                        lb = _loc_bbox(loc)
                        lx = loc.get("x", 0)
                        ly = loc.get("y", 0)
                        fw = float(loc.get("w", 0))
                        fh = float(loc.get("h", 0))

                        removed = False
                        for eb in escalator_bboxes:
                            # compute AABB overlap
                            ox_min = max(lb[0], eb[0])
                            oy_min = max(lb[1], eb[1])
                            ox_max = min(lb[2], eb[2])
                            oy_max = min(lb[3], eb[3])
                            overlap_w = ox_max - ox_min
                            overlap_h = oy_max - oy_min
                            overlap_area = 0.0
                            if overlap_w > 0 and overlap_h > 0:
                                overlap_area = overlap_w * overlap_h

                            fixture_area = fw * fh if fw > 0 and fh > 0 else 0.0

                            # collision rules:
                            # 1) fixture center inside escalator bbox
                            # 2) OR overlap area >= 50% of fixture area
                            center_inside = (
                                lx >= eb[0] and lx <= eb[2] and
                                ly >= eb[1] and ly <= eb[3]
                            )
                            significant_overlap = (
                                fixture_area > 0 and
                                overlap_area >= 0.5 * fixture_area
                            )

                            if center_inside or significant_overlap:
                                removed = True
                                break

                        if removed:
                            removed_count += 1
                            continue
                        filtered.append(loc)
                    return filtered, removed_count

                total_removed = 0
                # first pass
                linear_locs, linear_removed = _filter_list(linear_locs)
                downlight_locs, down_removed = _filter_list(downlight_locs)
                total_removed = linear_removed + down_removed

                # loop until no more removals
                while True:
                    linear_locs, linear_removed = _filter_list(linear_locs)
                    downlight_locs, down_removed = _filter_list(downlight_locs)
                    if (linear_removed + down_removed) == 0:
                        break
                    total_removed += (linear_removed + down_removed)

                if total_removed > 0:
                    print(
                        "Removed {} fixtures".format(total_removed)
                        + " overlapping escalator areas"
                    )

            planInfo["products"].append({
                "materialCode": (
                    linear_info.get("materialCode") if linear_info else None
                ),
                "lumen": (
                    linear_info.get("lumen") if linear_info else None
                ),
                "lmEff": (
                    linear_info.get("efficiency") if linear_info else None
                ),
                "CRI": (
                    linear_info.get("ra") if linear_info else None
                ),
                "category1": "线形灯具",
                "category2": "吊线式线形",
                "series": "恒",
                "power": 18,
                "colorTemperature": "4000",
                "location": linear_locs,
                "count": len(linear_locs),
                "angle": [0, 0, 0, 0, 0, 1],
                "area": "站台",
            })

        if downlight_locs:
            planInfo["products"].append({
                "materialCode": (
                    downlight_info.get("materialCode") if downlight_info
                    else None
                ),
                "lumen": (
                    downlight_info.get("lumen") if downlight_info else None
                ),
                "lmEff": (
                    downlight_info.get("efficiency") if downlight_info
                    else None
                ),
                "CRI": (
                    downlight_info.get("ra") if downlight_info else None
                ),
                "category1": "筒灯",
                "category2": "嵌入式筒灯",
                "series": "佳",
                "power": 8,
                "colorTemperature": "4000",
                "location": downlight_locs,
                "count": len(downlight_locs),
                "angle": [0, 0, 0, 0, 0, 1],
                "area": "站台",
            })

        return planInfo

    def del_custom_service_keys(self, planInfo):
        if "sellingDescriptionCustomer" in planInfo:
            del planInfo["sellingDescriptionCustomer"]
        if "designConceptCustomer" in planInfo:
            del planInfo["designConceptCustomer"]
        if "sellingKeywordsCustomer" in planInfo:
            del planInfo["sellingKeywordsCustomer"]

    def design_control_room(self, roomList, data: Inputs):
        """控制室灯具打点"""
        planInfo = deepcopy(self.planInfo)
        # TODO: implement control room lighting design

        return planInfo

if __name__ == "__main__":
    """
    Demo for metro station hall
    This demo showcases a metro station hall
    lighting design using the DesignMetro class.
    """
    from apps.metro_agent.construct_metro import ConstructMetro, Inputs
    import json
    # Define station hall parameters
    data = Inputs(
        roomLength=120,
        roomWidth=0,
        roomHeight=6,
        outerPassWidth_1=1.5,
        outerPassWidth_2=1.5,
        innerPassWidth=6.5,
        roomType="站台",
    )
    constructor = ConstructMetro()
    station_hall_rooms = constructor.build_platform(data)
    design_metro = DesignMetro("高效光")
    plan = design_metro.design_platform(station_hall_rooms, data)
    result = {
        "roomInfo": station_hall_rooms,
        "planList": [plan]
    }
    # save to json file
    filename = "metro_station_hall_design_demo_output.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
