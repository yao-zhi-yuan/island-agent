from apps.metro_agent.control_room_param_agent import ControlRoomParamAgent
from apps.req.metro_agent_req import Inputs
from apps.metro_agent.layout_objects import layout_aligned_lights_and_cells
from apps.metro_agent.prod_selector import metro_selector
from apps.metro_agent.construct_metro import ConstructMetro


""" Control room lighting designer """
# 品质光 1、灯盘，色温：4000k,功率：不限，尺寸：600*600；600*1200；系列：佳IV、众IV、昱
# 节律光 1、灯盘，色温：1800K~12000K,功率：不限，尺寸：600*600；600*1200；系列：天境

class ControlRoomDesign:
    """Select control room lighting products from the database."""

    def __init__(self):
        self.param_agent = ControlRoomParamAgent()
        self.design_concept_dict = {
            "品质光": (
                "控制室由于工作类型，工作时间长，精力高度集中，容易出现焦虑、疲惫。"
                "所以采用专业光谱缓解情绪，调节节律，促进夜班工作人员的睡眠问题。"
            ),
            "节律光": (
                "控制室由于工作类型，工作时间长，精力高度集中，容易出现焦虑、疲惫。"
                "所以采用专业光谱缓解情绪，调节节律，促进夜班工作人员的睡眠问题。"
            ),
        }

    def select_products(self, data: Inputs) -> dict:
        """Select products based on the description.

        Args:
            description: Text description of the control room lighting needs.

        Returns:
            dict: Extracted parameters including series, colorTemp, and size.
        """
        description = data.text
        if not description:
            params = {"category": "灯盘"}
            if "品质光" in data.tag:
                params["series"] = "佳IV"
                params["colorTemp"] = "4000"
                params["tag"] = "品质光"
                params["size"] = "600*600"
            elif "节律光" in data.tag:
                params["series"] = "天境"
                params["colorTemp"] = "1800-12000"
                params["tag"] = "节律光"
                params["size"] = "1200*600"
            else:
                params["series"] = "佳IV"
                params["colorTemp"] = "4000"
                params["tag"] = "品质光"
                params["size"] = "600*600"
            return params
        params = self.param_agent.run(description, user_id="control_room_user")
        series = params.get("series", None)
        color_temp = params.get("colorTemp", None)
        size = params.get("size", None)
        # 一级分类
        params["category"] = "灯盘"
        if size:
            params["size"] = size
        else:
            params["size"] = "1200*600"

        if series:
            params["series"] = series
            if series in ["佳IV", "众IV", "昱"]:
                params["colorTemp"] = "4000"
                params["tag"] = "品质光"
                if series == "昱":
                    params["size"] = "1200*600"
                if series in ["佳IV", "众IV"]:
                    params["size"] = "600*600"
            elif series in ["天境"]:
                params["colorTemp"] = "1800-12000"
                params["tag"] = "节律光"
            else:
                raise ValueError(
                    f"指定系列{series}不存在，目前仅支持：佳IV、众IV、昱、天境这四个系列"
                )
        elif color_temp:
            temp = color_temp
            if temp == "4000":
                params["colorTemp"] = "4000"
                params["series"] = "佳IV"
                params["tag"] = "品质光"
                params["size"] = "600*600"
            elif temp in ["1800-12000", "1800～12000"]:
                params["colorTemp"] = "1800-12000"
                params["series"] = "天境"
                params["tag"] = "节律光"
            else:
                params["colorTemp"] = "1800-12000"
                params["series"] = "天境"
                params["tag"] = "节律光"
        elif size:
            sz = size
            if sz in ["600*600", "600x600"]:
                params["size"] = "600*600"
                params["series"] = "佳IV"
                params["colorTemp"] = "4000"
                params["tag"] = "品质光"
            elif sz in ["600*1200", "1200*600"]:
                params["size"] = "1200*600"
                params["series"] = "天境"
                params["colorTemp"] = "1800-12000"
                params["tag"] = "节律光"
            else:
                params["size"] = "1200*600"
                params["series"] = "天境"
                params["colorTemp"] = "1800-12000"
                params["tag"] = "节律光"
        else:
            if "品质光" in data.tag:
                params["series"] = "佳IV"
                params["colorTemp"] = "4000"
                params["tag"] = "品质光"
                params["size"] = "600*600"
            elif "节律光" in data.tag:
                params["series"] = "天境"
                params["colorTemp"] = "1800-12000"
                params["tag"] = "节律光"
            else:
                params["series"] = "佳IV"
                params["colorTemp"] = "4000"
                params["tag"] = "品质光"
                params["size"] = "600*600"
        return params

    def design_control_room(self, data: Inputs):
        """
        Designs the entire control room, from construction to light placement.

        Args:
            data: Input parameters for the control room.

        Returns:
            A tuple containing (roomInfo, planList).
        """
        # 1. Build the initial room structure
        construct_metro = ConstructMetro()
        room_list = construct_metro.build_control_room(data)
        roomInfo = room_list  # roomInfo is the list of rooms

        # 2. Determine plan type and get product parameters
        light_params = self.select_products(data)
        print("控制室灯具参数:", light_params)
        plan_type = light_params.get("tag", "品质光")

        # 3. Build the planInfo structure
        planInfo = {
            "id": 1 if plan_type == "品质光" else 2,
            "name": plan_type,
            "designConcept": self.design_concept_dict.get(
                plan_type, self.design_concept_dict["品质光"]
            ),
            "sellingKeywords": (
                "欧普品质光" if plan_type == "品质光" else "欧普节律光"
            ),
            "sellingDescription": (
                "专业光谱、缓解疲劳" if plan_type == "品质光"
                else "智能节律、舒适健康"
            ),
        }

        # 4. Layout lights and generate product list
        if not room_list:
            planInfo["products"] = []
            return roomInfo, [planInfo]

        rect = room_list[0].get("rectangle", {})
        x_min, y_min = rect.get("x_min", 0), rect.get("y_min", 0)
        x_max, y_max = rect.get("x_max", 0), rect.get("y_max", 0)
        size_str = light_params.get("size", "600*600")
        print("控制室灯盘尺寸:", size_str)
        try:
            w_mm, h_mm = [int(float(s)) for s in size_str.split("*")[:2]]
        except Exception:
            w_mm, h_mm = 1200, 600
        light_size = (w_mm / 1000.0, h_mm / 1000.0)

        if f"{w_mm}*{h_mm}" in ("600*600", "600*600"):
            spacing, cell_size = (2.4, 2.4), (0.6, 0.6)
            light_size = (0.6, 0.6)
        elif f"{w_mm}*{h_mm}" in ("600*1200", "1200*600"):
            spacing, cell_size = (3.6, 3.6), (0.6, 0.6)
            light_size = (1.2, 0.6)
        else:
            spacing, cell_size = (3.6, 3.6), (0.6, 0.6)

        light_size = light_size[1], light_size[0]  # 调整长边改为由x轴向，对齐Y轴
        lights, cells = layout_aligned_lights_and_cells(
            x_min=x_min, x_max=x_max, y_min=y_min, y_max=y_max,
            light_size=light_size, spacing=spacing, cell_size=cell_size,
            height=max(0.0, data.roomHeight - 0.2),
            remove_colliding_cells=True,
        )
        # 输出日志：
        print("x_min:", x_min, "x_max:", x_max, "y_min:", y_min, "y_max:", y_max,"light_size:", light_size, "spacing:", spacing, "cell_size:", cell_size)
        series = light_params.get("series")
        color_temp = light_params.get("colorTemp")
        size_filter = light_params.get("size")

        if size_filter in ("600*1200", "1200*600"):
            size_filter = "1200*600"
        df = metro_selector.select_control_room_product(
            series=series, color_temp=color_temp, size=size_filter
        )
        print(f"筛选控制室产品:间距={spacing} 系列={series}, 色温={color_temp}, 尺寸={size_filter}, 结果数={len(df) if df is not None else 0}")
        if df is None or df.empty:
            df = metro_selector.select_control_room_product(
                series=series, color_temp=color_temp, size=None
            )

        prod_row = df.iloc[0] if df is not None and not df.empty else None

        def get_col(row, key, default=None):
            if row is None:
                return default
            val = row.get(key) if hasattr(row, 'get') else row.get(key)
            return default if (val is None or str(val) == 'nan') else val

        material_code = str(get_col(prod_row, "物料号", ""))
        power = get_col(prod_row, "功率(w)")
        lumen = get_col(prod_row, "光通量(lm)")
        lm_eff = get_col(prod_row, "光效(lm/w)")
        cri = get_col(prod_row, "显色指数(ra)")
        category2 = get_col(prod_row, "二级分类名称", "直下式灯盘")
        # reverse light[w] and light[h],make sure w>h
        for light in lights:
            light["w"], light["h"] = light["h"], light["w"]
        product = {
            "materialCode": material_code,
            "lumen": float(lumen) if lumen else None,
            "lmEff": float(lm_eff) if lm_eff else None,
            "CRI": int(cri) if cri else None,
            "category1": "灯盘",
            "category2": category2,
            "series": series,
            "power": float(power) if power else None,
            "colorTemperature": str(color_temp) if color_temp else None,
            "location": lights,
            "count": len(lights),
            "angle": [0, 0, 0, 0, 0, 1],
            "area": "控制室",
        }
        planInfo["products"] = [product]
        # 5. Update roomInfo with ceiling cells
        room_list[0]["objects"] = [{"type": "cell", "locations": cells}]
        return roomInfo, planInfo
