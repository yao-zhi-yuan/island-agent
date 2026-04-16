from apps.office_agent.office_param_agent import OfficeParamAgent
from apps.req.office_agent_req import OfficeInputs
from apps.metro_agent.layout_objects import layout_grid_simple
from apps.office_agent.product_retrieval import get_product_retriever
import pandas as pd
import copy

class OfficeDesign:
    """Design office lighting."""

    def __init__(self):
        self.retriever = get_product_retriever()
        self.config = {
            "独立办公室": {
                "agent": OfficeParamAgent("apps/office_agent/prompts/independent_office_prompt.md"),
                "build_func": self.build_independent_office,
                "layout_func": self._layout_independent_office,
                "plan_info": {
                    "id": 1,
                    "name": "品质光",
                    "designConcept": "通过预设的智能照明控制系统，实现两种光环境的一键无缝切换。这不仅科学地满足了员工在不同时间段的工作与生理节律需求，体现了人性化关怀，更通过精准的配光实现了功能与氛围的统一。",
                    "sellingKeywords": "欧普品质光",
                    "sellingDescription": "舒适、明亮、清晰",
                },
                "defaults": [
                    {"category1": "线形灯具", "series": "朗界", "param_key": "linear_light_series"},
                    {"category1": "护眼台灯", "series": "悦瞳", "param_key": "eye_care_lamp_series"},
                    {"category1": "低压灯带", "series": "虹昀Ⅲ", "param_key": "low_voltage_strip_series"},
                ]
            },
            "开放办公区": {
                "agent": OfficeParamAgent("apps/office_agent/prompts/open_office_prompt.md"),
                "build_func": self.build_open_office,
                "layout_func": self._layout_open_office,
                "plan_info": {
                    "id": 1,
                    "name": "专注光",
                    "designConcept": '运用“动态节律照明”理念，通过智能系统精确调控色温与照度，模拟自然光全天的光谱与强度变化，以契合人体生理节律，提升办公空间的健康属性与工作效率。',
                    "sellingKeywords": "欧普专注光",
                    "sellingDescription": "活力、专注、高效",
                },
                "defaults": [
                    {"category1": "线形灯具", "series": "朗界", "param_key": "linear_light_series"}
                ]
            },
            "多功能会议厅": {
                "agent": OfficeParamAgent("apps/office_agent/prompts/multi_functional_meeting_room_prompt.md"),
                "build_func": self.build_multi_functional_meeting_room,
                "layout_func": self._layout_multi_functional_meeting_room,
                "plan_info": {
                    "id": 1,
                    "name": "专注光",
                    "designConcept": '运用“智能动态光环境”的照明理念，设计了可一键切换的场景模式：入会前将自动开启窗帘，融合自然光以营造明亮通透的迎宾氛围；会议模式则关闭窗帘，启用高色温、高照度的专注光谱，有效提升与会者的工作效率与警觉性；演讲模式以美肤光精准聚焦主席台，在吸引全场视觉焦点的同时调暗观众席背景光，以强化演示效果；休息模式切换为低色温、低照度的舒缓暖光，为与会者提供放松与交流的柔和氛围。',
                    "sellingKeywords": "欧普专注光",
                    "sellingDescription": "活力、专注、高效",
                },
                "defaults": [
                    {"category1": "线形灯具", "series": "朗型", "param_key": "linear_light_series"},
                ]
            },
            "会议室": {
                # Agent is no longer needed for Meeting Room as scheme is direct input
                "build_func": self.build_meeting_room,
                "layout_func": self._layout_meeting_room,
                "schemes": {
                    "舒适光方案": {
                        "plan_info": {
                            "id": 1, "name": "舒适光方案",
                            "designConcept": "以功能导向为核心，通过矩阵式LED面板灯实现全空间无差别均匀照明。",
                            "sellingKeywords": "欧普舒适光", "sellingDescription": "舒适、明亮、清晰"
                        },
                        "defaults": [
                            {"category1": "灯盘", "series": "众IV", "param_key": "comfort_series"},
                            {"category2": "网关", "series": None, "param_key": None},
                            {"category2": "智能开关", "series": None, "param_key": None},
                            {"category2": "传感器", "series": None, "param_key": None},
                        ]
                    },
                    "品质光方案": {
                        "plan_info": {
                            "id": 2, "name": "品质光方案",
                            "designConcept": "以极简美学与现代科技融合为目标，通过防眩筒灯构建高效光环境。",
                            "sellingKeywords": "欧普品质光", "sellingDescription": "舒适、明亮、清晰"
                        },
                        "defaults": [
                            {"category1": "筒灯", "series": "皓", "param_key": "quality_series"},
                            {"category2": "网关", "series": None, "param_key": None},
                            {"category2": "智能开关", "series": None, "param_key": None},
                            {"category2": "传感器", "series": None, "param_key": None},
                        ]
                    },
                    "专注光方案": {
                        "plan_info": {
                            "id": 3, "name": "专注光方案",
                            "designConcept": "针对核心洽谈区加强重点照明，采用线形办公灯具营造专注氛围。",
                            "sellingKeywords": "专注、高效", "sellingDescription": "重点照明，目光聚焦"
                        },
                        "defaults": [
                            {"category1": "线形灯具", "series": "锋芒", "param_key": "focus_series_linear"},
                            {"category1": "射灯", "series": "皓", "param_key": "focus_series_spot"},
                            {"category2": "网关", "series": None, "param_key": None},
                            {"category2": "智能开关", "series": None, "param_key": None},
                            {"category2": "传感器", "series": None, "param_key": None},
                        ]
                    },
                    "SDL 天幕方案": {
                        "plan_info": {
                            "id": 4, "name": "SDL 天幕方案",
                            "designConcept": "以SDL技术为核心，打造高端柔和的沉浸式光环境。",
                            "sellingKeywords": "欧普 SDL技术", "sellingDescription": "节律、健康"
                        },
                        "defaults": [
                            {"category1": "模组", "series": "天幕", "param_key": "skylight_series"},
                            {"category2": "网关", "series": None, "param_key": None},
                            {"category2": "智能开关", "series": None, "param_key": None},
                            {"category2": "传感器", "series": None, "param_key": None},
                            {"algoKeyword": "天幕电源", "category1": "LED室内驱动", "series": None, "param_key": None},
                            {"algoKeyword": "天幕控制器", "category1": "IoT设备", "category2": "控制模块", "series": None, "param_key": None},
                        ]
                    }
                }
            }
        }

    def build_independent_office(self, data: OfficeInputs):
        """
        Build Independent Office room Info.
        Layout:
        - 1 Desk (Parallel to long side, 80cm from short wall, 50cm from long wall)
        - 3 Chairs (1 main, 2 guest) - Simplified as objects for now
        """
        room_info = {
            "name": data.officeType,
            "rectangle": {
                "x_min": 0,
                "y_min": 0,
                "z_min": 0,
                "x_max": data.officeLength,
                "y_max": data.officeWidth,
                "z_max": data.officeHeight
            },
            "objects": [],
        }

        desk_w, desk_d = 2.2, 2.28
        measurement_w, measurement_d = 2.2, 1.0
        desk_x = 0.8 + desk_w / 2
        desk_y = 0.5 + desk_d / 2
        rotation = [0, 0, 0]
        # 办公桌
        desk_obj = {
            "type": "办公桌",
            "locations": [{
                "x": desk_x, "y": desk_y, "z": 0,
                "w": desk_w, "h": desk_d, "l": 0.75,
                "rotation": rotation
            }]
        }
        margin = 0.25
        measure_bbox = {
            "x_min": desk_x - measurement_w / 2 ,
            "y_min": desk_y - measurement_d / 2 ,
            "z_min": 0.0,
            "x_max": desk_x + measurement_w / 2,
            "y_max": desk_y + measurement_d / 2,
            "z_max": data.officeHeight
        }
        expend_room = {
            "x_min": measure_bbox["x_min"] - margin,
            "y_min": measure_bbox["y_min"] - margin,
            "z_min": measure_bbox["z_min"],
            "x_max": measure_bbox["x_max"] + margin,
            "y_max": measure_bbox["y_max"] + margin,
            "z_max": measure_bbox["z_max"]
        }
        room_info["calculateInfo"]= [{
            "name": data.officeType,
            "bbox": expend_room,
            "config": {
                "margin": margin,
                "spacing": 0.2
            }
        }]
        # 会议桌
        meeting_table_w, meeting_table_d = 2.16, 1.46
        meeting_table_x = data.officeLength - 1 - meeting_table_w / 2
        meeting_table_y = 0.5 + meeting_table_d / 2
        meeting_table_obj = {
            "type": "会议桌",
            "locations": [{
                "x": meeting_table_x, "y": meeting_table_y, "z": 0,
                "w": meeting_table_w, "h": meeting_table_d, "l": 0.75,
                "rotation": rotation
            }]
        }
        room_info["objects"].append(desk_obj)
        room_info["objects"].append(meeting_table_obj)
        return [room_info]

    def build_open_office(self, data: OfficeInputs):
        """
        Build Open Office room Info.
        Layout:
        - Occupy the available office area with desks.
        """
        room_info = {
            "name": data.officeType,
            "rectangle": {
                "x_min": 0, "y_min": 0, "z_min": 0,
                "x_max": data.officeLength,
                "y_max": data.officeWidth,
                "z_max": data.officeHeight
            },
            "objects": []
        }
        # 1. Layout Desks in Office Area in a line
        desk_w, desk_l = 1.4, 1.2
        desk_spacing = 1.7 + desk_l
        margin_x = desk_l / 2 + 0.85
        margin_y = desk_w / 2 
        locations = layout_grid_simple(x_min=margin_x, y_min=margin_y, x_max=data.officeLength-margin_x, y_max=data.officeWidth-margin_y,
        spacing_x=desk_spacing, spacing_y=desk_w)
        # update rotation 
        for loc in locations:
            loc["rotation"] = [0, 0, 90]
            loc["w"], loc["h"], loc["l"] = desk_w, desk_l, 0.75
        room_info["objects"].append({
            "type": "办公桌",
            "locations": locations
        })
        return [room_info]

    def build_multi_functional_meeting_room(self, data: OfficeInputs):
        """
        Build Multi Functional Meeting Room room Info.
        Layout:
        - Occupy the available office area with desks.
        """
        room_info = {
            "name": data.officeType,
            "rectangle": {
                "x_min": 0, "y_min": 0, "z_min": 0,
                "x_max": data.officeLength,
                "y_max": data.officeWidth,
                "z_max": data.officeHeight
            },
            "objects": []
        }
        # 1. Layout Cells in Office Area in a line
        cell_w = 1.2
        cell_h = 1.2
        margin_x = 0.6 + cell_w/2
        margin_y = 0.1 + cell_w/2
        locations = layout_grid_simple(x_min=margin_x, y_min=margin_y, x_max=data.officeLength-margin_x, y_max=data.officeWidth-margin_y,
        spacing_x=cell_w, spacing_y=cell_h)
        # update rotation 
        for loc in locations:
            loc["rotation"] = [0, 0, 90]
            loc["w"], loc["h"], loc["l"] = cell_w, cell_h, 0.01
        room_info["objects"].append({
            "type": "天花板",
            "locations": locations
        })
        # 2. Layout Desks in Office Area in a line 3.6*0.9*0.848
        desk_w = 3.6
        desk_h = 0.9
        margin_x = desk_h/2
        margin_y = 0.1 + desk_w/2
        locations = layout_grid_simple(x_min=2+margin_x, y_min=margin_y, x_max=data.officeLength-margin_x-0.3, y_max=data.officeWidth-margin_y,
        spacing_x=1.7, spacing_y=desk_w+1)
        # update rotation 
        for loc in locations:
            loc["rotation"] = [0, 0, 90]
            loc["w"], loc["h"], loc["l"] = desk_w, desk_h, 0.75
        room_info["objects"].append({
            "type": "活动桌",
            "locations": locations
        })
        return [room_info]

    def build_meeting_room(self, data: OfficeInputs):
        """
        Build Meeting Room room Info based on Dify logic.
        """
        w = min(data.officeLength, data.officeWidth)
        l = max(data.officeLength, data.officeWidth)
        
        gap = 0.8
        desk_w = min(w - gap * 2, 1.8)
        desk_h = l - gap * 2
        
        room_info = {
            "name": "会议室",
            "rectangle": {
                "x_min": 0, "y_min": 0, "z_min": 0,
                "x_max": w, "y_max": l, "z_max": data.officeHeight
            },
            "objects": []
        }
        
        desk_obj = {
            "type": "desk",
            "locations": [{
                "x": w / 2, "y": l / 2,
                "w": desk_w, "h": desk_h,
                "rotation": [0, 0, 0]
            }]
        }
        
        # Chairs
        chair_w = 0.76
        chair_offset = 0.15
        chair_num = int(desk_h // 0.85)
        start_y = (desk_h - chair_num * chair_w) / 2 + gap
        
        chair_locations = []
        # Left side chairs
        for i in range(chair_num):
            x = (w / 2) - (desk_w / 2) + chair_offset
            y = start_y + (i * 2 + 1) * chair_w / 2
            chair_locations.append({
                "x": x, "y": y,
                "w": chair_w, "h": chair_w,
                "rotation": [0, 0, 270]
            })
        # Right side chairs
        for i in range(chair_num):
            x = (w / 2) + (desk_w / 2) - chair_offset
            y = start_y + (i * 2 + 1) * chair_w / 2
            chair_locations.append({
                "x": x, "y": y,
                "w": chair_w, "h": chair_w,
                "rotation": [0, 0, 90]
            })
            
        chair_obj = {"type": "chair", "locations": chair_locations}
        
        # TV/Screen
        tv_obj = {
            "type": "tv",
            "locations": [{
                "x": w / 2, "y": 0, "z": 1.4,
                "w": 1, "h": 1,
                "rotation": [0, 0, 0]
            }]
        }
        
        room_info["objects"] = [desk_obj, chair_obj, tv_obj]
        return [room_info]


    def _select_office_products(self, defaults, params, area_name, user_text=""):
        """Common helper to select products based on defaults and LLM params."""
        # 1. Load CSV (Legacy)
        try:
            df = pd.read_csv("data/道路行业产品库.csv")
        except Exception as e:
            print(f"Warning: data/道路行业产品库.csv not found: {e}")
            df = None

        # 2. Update defaults with user-provided series (Skip for Meeting Room)
        params = params or {}
        if df is not None and area_name != "会议室":
            for default in defaults:
                user_series = params.get(default["param_key"])
                if user_series:
                    category1 = default["category1"]
                    # Match Series AND Category (Exact match)
                    match = df[(df["系列"] == user_series) & (df["一级分类名称"] == category1)]
                    if not match.empty:
                        default["series"] = user_series
                    else:
                        print(f"Warning: Product '{user_series}' ('{category1}') not found. Using default '{default['series']}'.")

        # 3. Fetch detailed product info
        products = []
        for prod_config in defaults:
            category1 = prod_config.get("category1")
            category2 = prod_config.get("category2")
            series = prod_config.get("series")
            param_key = prod_config.get("param_key")
            
            product = {
                "category1": category1, "category2": category2, "series": series,
                "power": 0.0, "colorTemperature": "",
                "materialCode": "", "location": [], "count": 1, "angle": [0, 0, 0, 0, 0, 1],
                "algoKeyword": prod_config.get("algoKeyword", "")
            }

            # Special case for Meeting Room: Use AI Fuzzy Retrieval with the new Excel data
            if area_name == "会议室":
                user_input = params.get(param_key) if param_key else None
                # Construct query: category + user input OR default series + Original User Text

                query = f"{category1 or ''} {category2 or ''} {user_input or series or ''} {user_text}".strip()  
                if category1:
                    if category1 == "筒灯":
                        query = f"{category1} 70° {user_text}".strip()
                filters = {}
                if category1: filters["category1"] = category1
                if category2: filters["category2"] = category2
                
                search_results = self.retriever.search(query, top_k=10, filters=filters)
                if search_results:
                    row = search_results[0]
                    # Format power as string (e.g. "12.0")
                    power_val = row.get("power", "0")
                    try:
                        p_float = float(power_val) if power_val and power_val != "" else 0.0
                        power_str = f"{p_float:.1f}"
                    except:
                        power_str = str(power_val)

                    # Get algoKeyword from product defaults or from retrieval
                    algo_kw = product.get("algoKeyword", "")
                    if not algo_kw:
                        algo_kw = str(row.get("keyword", "")) if pd.notnull(row.get("keyword")) else ""
                    
                    product.update({
                        "power": power_str,
                        "colorTemperature": str(row.get("colorTemp", "")) if pd.notnull(row.get("colorTemp")) else "",
                        "materialCode": str(row.get("materialCode", "")) if pd.notnull(row.get("materialCode")) else "",
                        "luminousEfficacy": str(row.get("industyLevel", "")) if pd.notnull(row.get("industyLevel")) else "",
                        "CRI": str(row.get("cri", "")) if pd.notnull(row.get("cri")) else "",
                        "category1": str(row.get("category1", category1 or "")),
                        "category2": str(row.get("category2", category2 or "")),
                        "lumen": int(float(row.get("lumen", 0))) if pd.notnull(row.get("lumen")) and row.get("lumen") != "" else 0,
                        "series": str(row.get("series", series or "")),
                        "beamAngle": str(row.get("beamAngle", "")) if pd.notnull(row.get("beamAngle")) else "",
                        "UGR": str(row.get("ugr", "")) if pd.notnull(row.get("ugr")) else "",
                        "assemble": str(row.get("assemble", "")) if pd.notnull(row.get("assemble")) else "",
                        "size": str(row.get("size", "")) if pd.notnull(row.get("size")) else "",
                        "holeSize": str(row.get("holeSize", "")) if pd.notnull(row.get("holeSize")) else "",
                        "pricePosition": str(row.get("pricePosition", "")) if pd.notnull(row.get("pricePosition")) else "",
                        "algoKeyword": algo_kw,
                        "area": area_name,
                        # SDL accessories get zeros for angle
                        "angle": [0, 0, 0, 0, 0, 0] if algo_kw in ["天幕电源", "天幕控制器"] else product.get("angle", [0, 0, 0, 0, 0, 1])
                    })
                    products.append(product)
                    continue

            # Default logic for other areas or if retrieval fails
            if df is not None:
                if category1 and series:
                    match = df[(df["系列"] == series) & (df["一级分类名称"] == category1)]
                elif category2:
                    match = df[df["二级分类名称"] == category2]
                else:
                    match = pd.DataFrame()

                if not match.empty:
                    row = match.iloc[0]
                    power_val = row.get("功率(w)", "0")
                    try:
                        p_float = float(power_val) if power_val and power_val != "" else 0.0
                        power_str = f"{p_float:.1f}"
                    except:
                        power_str = str(power_val)
                    
                    # Get algoKeyword from default or row
                    algo_kw = product.get("algoKeyword", "")
                    if not algo_kw:
                        algo_kw = str(row.get("keyword", "")) if pd.notnull(row.get("keyword")) else ""
                    
                    product.update({
                        "power": power_str,
                        "colorTemperature": str(row.get("色温(k)", "")) if pd.notnull(row.get("色温(k)")) else "",
                        "materialCode": str(row.get("物料号", "")) if pd.notnull(row.get("物料号")) else "",
                        "luminousEfficacy": str(row.get("光效(lm/w)", "")) if pd.notnull(row.get("光效(lm/w)")) else "",
                        "CRI": str(row.get("显色指数(ra)", "")) if pd.notnull(row.get("显色指数(ra)")) else "",
                        "category1": str(row.get("一级分类名称", category1 or "")),
                        "category2": str(row.get("二级分类名称", category2 or "")),
                        "lumen": float(row.get("光通量(lm)", 0)) if pd.notnull(row.get("光通量(lm)")) else 0.0,
                        "area": area_name,
                        "algoKeyword": algo_kw,
                        "angle": [0, 0, 0, 0, 0, 0] if algo_kw in ["天幕电源", "天幕控制器"] else product.get("angle", [0, 0, 0, 0, 0, 1])
                    })
            products.append(product)
        return products

    def design_office(self, data: OfficeInputs):
        # 0. Get Config
        cfg = self.config[data.officeType]

        # 1. Parse params (Skip for Meeting Room)
        if data.officeType == "会议室":
            params = {}
        else:
            params = cfg["agent"].run(data.text, user_id="office_user")

        # 2. Support for multiple schemes
        if "schemes" in cfg:
            # Use tag/scheme_type directly (already normalized in OfficeInputs)
            scheme_name = data.tag or params.get("scheme_type")
            
            # Default to 品质光方案 if no scheme found
            scheme_cfg = cfg["schemes"].get(scheme_name, cfg["schemes"].get("品质光方案", list(cfg["schemes"].values())[0]))
            plan_info = copy.deepcopy(scheme_cfg["plan_info"])
            defaults = copy.deepcopy(scheme_cfg["defaults"])
        else:
            plan_info = copy.deepcopy(cfg["plan_info"])
            defaults = copy.deepcopy(cfg["defaults"])

        # 3. Build Room & Select Products
        room_list = cfg["build_func"](data)
        products = self._select_office_products(
            defaults, params, data.officeType, user_text=data.text
        )

        # 4. Layout Lights
        cfg["layout_func"](products, room_list[0], data, params)

        plan_info["products"] = products
        
        return room_list, [plan_info]

    def _clean_product_for_output(self, p):
        """Standardize product dictionary for Dify parity."""
        # 1. Strip internal fields
        p.pop("area", None)
        # ONLY keep algoKeyword for specific items (Dify behavior)
        # Keep for: modules (模组), OR specific SDL accessories by keyword OR by category
        should_keep_algo = (
            p.get("category1") == "模组" or
            p.get("algoKeyword") in ["天幕电源", "天幕控制器", "天幕灯具"] or
            (p.get("category1") == "LED室内驱动" and p.get("category2") == "室内非智能驱动") or
            (p.get("category1") == "IoT设备" and p.get("category2") == "控制模块")
        )
        if not should_keep_algo:
            p.pop("algoKeyword", None)
        
        # 2. Convert empty strings to None for specific attributes
        for key in ["beamAngle", "CRI", "luminousEfficacy", "colorTemperature", "holeSize", "assemble", "size", "UGR"]:
            if p.get(key) == "" or p.get(key) == "None":
                p[key] = None
        
        # Special handling for power: "0.0" or 0 -> None for accessories
        if p.get("power") in ["0.0", "0", 0, 0.0]:
            p["power"] = None
                
        # 3. Type consistency: MODULES use float power, Others use string
        if p.get("category1") == "模组":
            if p.get("power"):
                try: p["power"] = float(p["power"])
                except: pass
            if p.get("lumen") is not None:
                p["lumen"] = int(p["lumen"])
        else:
            if p.get("lumen") is not None:
                try: p["lumen"] = int(p["lumen"])
                except: pass
        
        # 4. Standardize locations
        algo = p.get("algoKeyword")
        for loc in p.get("location", []):
            # Globally remove 'z'
            loc.pop("z", None)
            
            # Special case: Drivers/Controllers don't have w, h
            if algo in ["天幕电源", "天幕控制器"]:
                loc.pop("w", None)
                loc.pop("h", None)
                loc.pop("rotation", None)
                
        return p

    def _layout_independent_office(self, products, room, data: OfficeInputs, params: dict = {}):
        # Desk Layout
        desk = next((obj for obj in room["objects"] if obj["type"] == "办公桌"), None)
        if desk:
            d_loc = desk["locations"][0]
            products[0]["location"] = [{
                "x": d_loc["x"], "y": d_loc["y"], "z": data.officeHeight - 0.1,
                "l": 0.1, "w": 1.5, "h": 0.080, "rotation": d_loc["rotation"]
            }]
            products[0]["count"] = 1
            products[0]["angle"] = [0,0,0,0,1,1]
        
        # Meeting Table Layout
        meeting_table = next((obj for obj in room["objects"] if obj["type"] == "会议桌"), None)
        if meeting_table:
            r_loc = meeting_table["locations"][0]
            products[1]["location"] = [{
                "x": r_loc["x"], "y": 0.5, "z": 1.9, "rotation": [0,0,0]
            }]
            products[1]["angle"] = [0,0,0,0,0,1]

        # Strip lights (Low Voltage Strip)
        strip_product_template = products[2]
        strip_len = data.officeLength - 0.16
        strip_x = data.officeLength / 2
        
        strip1 = copy.deepcopy(strip_product_template)
        strip1["location"] = [
            {"x": strip_x, "y": 0.15, "z": data.officeHeight - 0.1, "l": 0.01, "w": strip_len, "h": 0.01, "rotation": [0, 0, 0]}
        ]
        strip1["count"] = int(strip_len + 0.999)
        strip1["angle"] = [0, 0, 0, 1, 0, 0]
        
        strip2 = copy.deepcopy(strip_product_template)
        strip2["location"] = [
            {"x": strip_x, "y": data.officeWidth - 0.15, "z": data.officeHeight - 0.1, "l": 0.01, "w": strip_len, "h": 0.01, "rotation": [0, 0, 0]}
        ]
        strip2["count"] = int(strip_len + 0.999)
        strip2["angle"] = [0, 0, 1, 0, 0, 0]

        products[2] = strip1
        products.insert(3, strip2)

    def _layout_open_office(self, products, room, data: OfficeInputs, params: dict = {}):    
        desk_w, desk_l = 1.4, 1.2 
        desks_obj = next((obj for obj in room["objects"] if obj["type"] == "办公桌"), None)
        if not desks_obj or not desks_obj["locations"]:
            return

        # 1. Group desks by X coordinate to handle them as "blocks"
        from collections import defaultdict
        x_groups = defaultdict(list)
        for loc in desks_obj["locations"]:
            # Round X to handle float precision
            rx = round(loc["x"], 2)
            x_groups[rx].append(loc)

        linear_light = next((p for p in products if p["category1"] == "线形灯具"), None)
        if not linear_light:
            return

        linear_light["location"] = []
        linear_light["angle"] = [0, 0, 0, 0, 1, 1]
        
        light_len = 1.2
        # 获取分组后桌子在y方向的最大最小值。如果距离>0.6 就放置一个柜子,更新room中的objects，在桌子两册放置柜子。
        room_max_y = data.officeWidth
        counter_locations = []
        for x_coord, locs in x_groups.items():
            # Find Y range for this block of desks
            y_coords = [l["y"] for l in locs]
            min_y, max_y = min(y_coords), max(y_coords)
            if room_max_y - max_y - desk_w/2 > 0.6:
                counter_locations.append({
                    "x": x_coord, "y": max_y + 0.95, "z": 0.0,
                    "w": 1.2, "h": 0.5, "l": 0.75,
                    "rotation": [0, 0, 0]
                })
                counter_locations.append({
                    "x": x_coord, "y": min_y - 0.95, "z": 0.0,
                    "w": 1.2, "h": 0.5, "l": 0.75,
                    "rotation": [0, 0, 0]
                })
            center_y = (min_y + max_y) / 2
            total_desk_span = (max_y - min_y) + desk_w
            
            # Calculate how many 1.2m lights fit in this span (centered)
            # Use a small epsilon to ensure 2.8 / 1.2 -> 2.33 -> 2 lights correctly, 
            # and precisely 2.4/1.2 -> 2.
            num_lights = max(1, int(total_desk_span / light_len + 1e-6))
            
            # Start position to center lights over the desk block
            total_light_span = (num_lights - 1) * light_len
            start_y = center_y - total_light_span / 2
            
            for i in range(num_lights):
                ly = start_y + i * light_len
                linear_light["location"].append({
                    "x": x_coord, "y": ly, "z": data.officeHeight - 0.08, 
                    "rotation": [0, 0, 90]
                })
        
        if counter_locations:
            room["objects"].append({
                "type": "柜子",
                "locations": counter_locations
            })
        linear_light["count"] = len(linear_light["location"])
        
    def _layout_multi_functional_meeting_room(self, products, room, data: OfficeInputs, params: dict = {}):
        # Layout Lights 1、室内天花区域间隔1.2米垂直于室内较长的一边放置N条宽10cm的嵌入式线型灯；(四舍五入计算)
        linear_light = next((p for p in products if p["category1"] == "线形灯具"), None)
        if not linear_light:
            return
        light_w = 1.2
        light_h = 0.1
        margin_x = 0.6 + light_w/2
        margin_y = 0.1 + light_w/2
        locations = layout_grid_simple(x_min=margin_x, y_min=margin_y, x_max=data.officeLength-margin_x, y_max=data.officeWidth-margin_y,
        spacing_x=light_w, spacing_y=light_w)
        # update rotation 
        for loc in locations:
            loc["rotation"] = [0, 0, 90]
            loc["z"] = data.officeHeight - 0.08
            loc["w"], loc["h"], loc["l"] = light_w, light_h, 0.01
        linear_light["location"] = locations
        linear_light["count"] = len(locations)
        linear_light["angle"] = [0, 0, 0, 0, 0, 1]

    def _layout_meeting_room(self, products, room, data: OfficeInputs, params: dict = {}):
        """
        Layout lights for Meeting Room based on the selected scheme.
        """
        scheme_type = data.tag or params.get("scheme_type") or "品质光方案"
        room_obj = room
        room_w = room_obj["rectangle"]["x_max"]
        room_h = room_obj["rectangle"]["y_max"]
        room_z = room_obj["rectangle"]["z_max"]
        
        # 0. Set default locations for accessories (matches Dify behavior)
        for p in products:
            p["location"] = p.get("location") or []
            p["count"] = p.get("count") or 0
            
            # Use size to set w, h in locations
            size_str = p.get("size", "")
            w_val, h_val = 0.0, 0.0
            if size_str and "*" in size_str:
                parts = size_str.split("*")
                try:
                    w_val = float(parts[0]) / 1000.0
                    h_val = float(parts[1]) / 1000.0
                except: pass
            
            is_accessory = (p.get("category2") in ["网关", "智能开关", "传感器", "智能面板", "控制模块"] or 
                          p.get("category1") == "IoT设备" or 
                          p.get("algoKeyword") in ["天幕电源", "天幕控制器"])
            
            if not p["location"] and is_accessory:
                loc = {"x": 0.0, "y": 0.0}
                # Dify Power/Controllers DON'T have w, h
                if p.get("algoKeyword") not in ["天幕电源", "天幕控制器"]:
                    loc["w"], loc["h"] = w_val, h_val
                p["location"] = [loc]
                p["count"] = 1
                # SDL accessories have all zeros, others might have [0,0,0,0,0,0]
                if p.get("algoKeyword") in ["天幕电源", "天幕控制器"]:
                    p["angle"] = [0, 0, 0, 0, 0, 0]
                else:
                    p["angle"] = [0, 0, 0, 0, 0, 0]

            # pricePosition sync
            if p.get("category1") == "筒灯": p["pricePosition"] = "利润"
            elif p.get("category1") == "灯盘": p["pricePosition"] = "规模"
            elif p.get("category1") == "射灯": p["pricePosition"] = "利润"
            elif p.get("category1") == "线形灯具": p["pricePosition"] = "利润"
            elif p.get("category1") == "模组": p["pricePosition"] = "品牌"
            else: p["pricePosition"] = "品牌"

        if scheme_type == "舒适光方案":
            # Direct-lit panel grid
            lamp = next((p for p in products if p.get("category1") == "灯盘"), products[0])
            size_str = lamp.get("size", "600*600")
            w_l, h_l = 0.6, 0.6
            if size_str and "*" in size_str:
                parts = size_str.split("*")
                try:
                    w_l = float(parts[0]) / 1000.0
                    h_l = float(parts[1]) / 1000.0
                except: pass
            
            gap = 1.8
            w_num = max(round(room_w / gap), 1)
            h_num = max(round(room_h / gap), 1)
            locations = []
            for i in range(w_num):
                x = room_w / w_num / 2 * (i * 2 + 1)
                for j in range(h_num):
                    y = room_h / h_num / 2 * (j * 2 + 1)
                    locations.append({"x": x, "y": y, "w": w_l, "h": h_l, "rotation": [0,0,0]})
            lamp["location"] = locations
            lamp["count"] = len(locations)
            lamp["angle"] = [0, 0, 0, 0, 0, 1]

        elif scheme_type == "品质光方案":
            # Downlight grid
            lamp = next((p for p in products if p.get("category1") == "筒灯"), products[0])
            size_str = lamp.get("size", "88*59")
            w_l, h_l = 0.088, 0.059
            if size_str and "*" in size_str:
                parts = size_str.split("*")
                try:
                    w_l = float(parts[0]) / 1000.0
                    h_l = float(parts[1]) / 1000.0
                except: pass
            
            gap = 1.4
            w_num = max(round(room_w / gap), 1)
            h_num = max(round(room_h / gap), 1)
            locations = []
            for i in range(w_num):
                x = room_w / w_num / 2 * (i * 2 + 1)
                for j in range(h_num):
                    y = room_h / h_num / 2 * (j * 2 + 1)
                    locations.append({"x": x, "y": y, "w": w_l, "h": h_l, "rotation": [0,0,0]})
            lamp["location"] = locations
            lamp["count"] = len(locations)
            lamp["angle"] = [0, 0, 0, 0, 0, 1]

        elif scheme_type == "专注光方案":
            # Linear lights + Spotlights
            liner = next((p for p in products if p.get("category1") == "线形灯具"), products[0])
            spot = next((p for p in products if p.get("category1") == "射灯"), products[min(1, len(products)-1)])
            
            # Linear lights centered over desk
            desk = next((obj for obj in room["objects"] if obj["type"] == "desk"), None)
            if desk:
                d_loc = desk["locations"][0]
                line_h = 1.2 # Standard module
                line_num = max(1, int(d_loc["w"] // line_h))
                start_x = d_loc["x"] - (line_num * line_h) / 2
                locations = []
                for i in range(line_num):
                    x = start_x + (i * 2 + 1) * line_h / 2
                    locations.append({"x": x, "y": d_loc["y"], "z": data.officeHeight - 0.05, "w": line_h, "h": 0.1, "rotation": [0,0,0]})
                liner["location"] = locations
                liner["count"] = len(locations)
                liner["angle"] = [0, 0, 0, 0, 0, 1]
            
            # Spotlights along walls
            spot_locations = []
            size_str = spot.get("size", "88*59")
            sw, sh = 0.088, 0.059
            if size_str and "*" in size_str:
                parts = size_str.split("*")
                try:
                    sw = float(parts[0]) / 1000.0
                    sh = float(parts[1]) / 1000.0
                except: pass
                
            spot_gap = 1.8
            num_spots = max(1, int(room_w // spot_gap))
            for j in range(num_spots):
                x = room_w / num_spots / 2 * (j * 2 + 1)
                spot_locations.append({"x": x, "y": 0.5, "w": sw, "h": sh, "rotation": [0,0,0]})
                spot_locations.append({"x": x, "y": room_h - 0.5, "w": sw, "h": sh, "rotation": [0,0,0]})
            spot["location"] = spot_locations
            spot["count"] = len(spot_locations)
            spot["angle"] = [0, 0, 0, 0, 0, 1]

        elif scheme_type == "SDL 天幕方案":
            import math
            sdl_gap = data.sdlGap if data.sdlGap else 0.085 # default from Dify
            w_gap = 0.1
            h_gap = 0.02
            w_num = math.ceil(room_w / 4.2)
            lamp_w = (room_w - w_gap * 2 - sdl_gap * (w_num - 1)) / w_num
            lamp_h = room_h - h_gap * 2
            locations = []
            tm_w = 0
            tm_h = 0
            for i in range(w_num):
                x = w_gap + lamp_w / 2 * (1 + i * 2) + i * sdl_gap
                y = room_h / 2
                locations.append({"x": x, "y": y, "rotation": [0,0,0], "w": lamp_w, "h": lamp_h})
                tm_w += lamp_w
                tm_h += lamp_h
            
            # Find the skylight lamp
            lamp = next((p for p in products if p.get("category1") == "模组" or p.get("algoKeyword") == "天幕灯具"), products[0])
            lamp["algoKeyword"] = "天幕灯具"
            lamp["location"] = locations
            lamp["size"] = None  # Dify sets this to None
            
            # Dify Power Logic: based on 0.15m grid beads
            dengzhu_w = int(tm_w / 0.15) + 1
            dengzhu_h = int(tm_h / 0.15) + 1
            tm_power = dengzhu_w * dengzhu_h * 2.1
            
            lamp["power"] = f"{tm_power:.1f}"
            lamp["count"] = 1
            lamp["angle"] = [0, 0, 0, 0, 0, 1]

        # Final Clean-up: Apply standardized formatting
        for p in products:
            self._clean_product_for_output(p)

