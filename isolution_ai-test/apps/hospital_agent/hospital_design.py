from apps.office_agent.product_retrieval import ProductRetrievalService
from apps.req.hospital_agent_req import HospitalInputs
from apps.metro_agent.layout_objects import layout_grid_simple
import pandas as pd
import copy
import os
import math
import json

def round_p(val):
    if val == int(val): return int(val)
    return float(round(val, 2))

class HospitalDesign:
    """Design hospital lighting."""

    def __init__(self):
        # Initialize retriever with the products collection and 'hospital' partition
        self.retriever = ProductRetrievalService(partition_name="hospital")
        
        self.config = {
            "病房": {
                "build_func": self.build_ward,
                "layout_func": self._layout_ward,
                "schemes": {
                    "品质光方案": {
                        "id": 1, "name": "品质光方案",
                        "designConcept": "灯盘作为主照明灯具，有间接与直下两种照明模式。当切换至病人休息模式时，灯具开启间接照明部分，柔和舒缓的光线，营造出温馨氛围，有助于平复病人情绪，促进身心放松。在医生检查模式下，灯具的间接与直下照明全部开启，提供充足且明亮的光线，满足医生进行检查及简单治疗时对照明的严格需求。",
                        "sellingKeywords": "欧普品质光", "sellingDescription": "舒愈、放松、均匀、洁净",
                        "defaults": [
                            {"category1": "灯盘", "param_key": "main_light", "angle": [0, 0, 0, 0, 0, 1]},
                            {"category1": "筒灯", "param_key": "spot_light", "algoKeyword": "筒灯", "angle": [0, 0, 0, 0, 0, 1]},
                            {"category1": "夜灯", "param_key": "night_light", "angle": [0, 0, 0, 1, 0, 0]},
                            {"category1": "低压灯带", "param_key": "strip_light","algoKeyword": "低压灯带", "angle": [0, 0, 0, 1, 0, 0]},
                            {"category1": "IoT设备", "param_key": "gateway", "category2": "网关", "angle": [0, 0, 0, 0, 0, 0]},
                            {"category1": "智能面板", "param_key": "panel", "algoKeyword": "智能面板", "angle": [0, 0, 0, 0, 0, 0]}
                        ]
                    },
                    "疗愈光方案": {
                        "id": 2, "name": "疗愈光方案",
                        "designConcept": "专业配光设计的壁灯，具备双模式照明功能。全开模式，壁灯精准控光，提供均匀明亮的氛围，能够满足医生进行检查或简单治疗对照明的要求，确保医疗操作的精准性与安全性。壁灯的上出光，间接光与漫反射，营造出柔和舒适的光线，为病人日常休息与活动提供了舒适的氛围。床尾处的天境灯，可逼真模拟多种自然光场景。或蓝天白云，或柔和晚霞，或淡雅的淡彩光，营造出舒缓的氛围，帮助病人舒缓压力、放松心情，助力病人在自然舒适的光环境中更好地康复。",
                        "sellingKeywords": "欧普疗愈光", "sellingDescription": "疗愈、助眠、健康",
                        "defaults": [
                            {"category1": "灯盘", "param_key": "main_light", "algoKeyword": "天境", "angle": [0, 0, 0, 0, 0, 1]},
                            {"category1": "壁灯", "param_key": "wall_light", "angle": [0, 0, 0, 0, 1, 1]},
                            {"category1": "筒灯", "param_key": "spot_light", "algoKeyword": "筒灯", "angle": [0, 0, 0, 0, 0, 1]},
                            {"category1": "夜灯", "param_key": "night_light", "angle": [0, 0, 0, 1, 0, 0]},
                            {"category1": "IoT设备", "param_key": "gateway", "category2": "网关", "angle": [0, 0, 0, 0, 0, 0]},
                            {"category1": "智能面板", "param_key": "panel", "algoKeyword": "智能面板", "angle": [0, 0, 0, 0, 0, 0]}
                        ]
                    },
                    "节律光方案": {
                        "id": 3, "name": "节律光方案",
                        "designConcept": "天境灯作为主灯配合控制系统，可实现逼真全时自然光模拟。白天，天境灯营造仿若蓝天白云下的光环境，高照度与高色温的光线，提供明亮通透的氛围，也可以提升病人夜晚睡眠质量。傍晚，灯光切换为晚霞般的柔和光色，能够舒缓情绪，有助于睡眠。天境灯也能调出柔和的淡彩光线，营造出舒缓、放松的氛围。在紧急情况，医生只需轻按一键检查，天境灯可切换至检查模式，提供明亮且均匀的光线，满足紧急检查所需的照明。通过对灯光的调节，契合人体生物节律，为患者的康复助力。",
                        "sellingKeywords": "欧普节律光", "sellingDescription": "节律、疗愈、助眠、健康",
                        "defaults": [
                            {"category1": "灯盘", "param_key": "main_light", "algoKeyword": "天境", "angle": [0, 0, 0, 0, 0, 1]},
                            {"category1": "筒灯", "param_key": "spot_light", "algoKeyword": "筒灯", "angle": [0, 0, 0, 0, 0, 1]},
                            {"category1": "夜灯", "param_key": "night_light",  "angle": [0, 0, 0, 1, 0, 0]},
                            {"category1": "低压灯带", "param_key": "strip_light","algoKeyword": "低压灯带", "angle": [0, 0, 0, 1, 0, 0]},
                            {"category1": "IoT设备", "param_key": "gateway","category2": "网关", "angle": [0, 0, 0, 0, 0, 0]},
                            {"category1": "智能面板", "param_key": "panel", "algoKeyword": "智能面板", "angle": [0, 0, 0, 0, 0, 0]}
                        ]
                    }
                }
            },
            "诊疗室": {
                "build_func": self.build_clinic,
                "layout_func": self._layout_clinic,
                "schemes": {
                    "清澈光方案": {
                        "id": 1, "name": "清澈光方案",
                        "designConcept": "高照度均匀光环境，确保诊疗操作的精确性与环境的洁净感。",
                        "sellingKeywords": "清澈、专业", "sellingDescription": "高亮无影，专业护航",
                        "defaults": [
                            {"category1": "灯盘", "category2": "直下式灯盘", "param_key": "main_light", "algoKeyword": "直下式灯盘"},
                            {"category1": "筒灯", "param_key": "spot_light", "algoKeyword": "筒灯"},
                            {"category1": "IoT设备", "param_key": "gateway", "algoKeyword": "IoT设备"},
                            {"category1": "智能面板", "param_key": "panel", "algoKeyword": "智能面板"}
                        ]
                    },
                    "舒适光方案": {
                        "id": 2, "name": "舒适光方案",
                        "designConcept": "诊桌照明选用上下出光落地灯，灯具通过向上漫反射，照亮天花，营造柔和舒适氛围，确保医生操作区域亮度充足，同时也能提供柔和饱满立面光，有利于医生和患者交流，缓解患者焦虑情绪， 独特的上下光分控设计，可以自由调配多种发光配比，可满足诊室的多元用光需求。",
                        "sellingKeywords": "欧普舒适光",
                        "sellingDescription": "舒适、明亮、清晰",
                        "defaults": [
                            {"category1": "灯盘", "category2": "直下式灯盘", "param_key": "main_light", "algoKeyword": "直下式灯盘"},
                            {"category1": "护眼台灯", "param_key": "table_lamp", "algoKeyword": "护眼台灯"},
                            {"category1": "筒灯", "param_key": "spot_light", "algoKeyword": "筒灯"},
                            {"category1": "IoT设备", "param_key": "gateway", "algoKeyword": "IoT设备"},
                            {"category1": "智能面板", "param_key": "panel", "algoKeyword": "智能面板"}
                        ]
                    }
                }
            },
            "护士站": {
                "build_func": self.build_nurse_station,
                "layout_func": self._layout_nurse_station,
                "schemes": {
                    "节律光方案": {
                        "id": 1, "name": "节律光方案",
                        "designConcept": "护士站作为全天候运行的核心医疗空间，照明设计需要兼顾功能性与医护人员身体健康，打造健康高效的工作环境。台面上方异形发光膜，提供均匀柔和明亮的照明场域，满足日常交流、文书记录等需要，保证医护人员专注高效工作，空间内侧设置SDL洗墙灯，将天花均匀洗亮，实现动态照明效果，日间模拟晴朗天空，夜晚自动降低色温，营造舒适的氛围，缓解疲劳感，减少对医护人员生物节律的影响；另外筒灯洗亮背景墙，可以增加空间明亮感及空间的识别性，起到一定的引导作用。",
                        "sellingKeywords": "欧普节律光", "sellingDescription": "节律、疗愈、健康",
                        "defaults": [
                            {"category2": "直下式灯盘", "param_key": "main_light", "angle": [0, 0, 0, 0, 0, 1]},
                            {"category1": "模组", "param_key": "sdl_light", "algoKeyword": "天幕灯具", "category2": "条形模组", "angle": [0, 0, 0, 1, 0, 0]},
                            {"category1": "IoT设备", "param_key": "sdl_ctrl", "algoKeyword": "天幕控制器"},

                            {"category1": "筒灯", "param_key": "spot_light"},
                            {"category1": "线形灯具", "param_key": "wall_light_1", "algoKeyword": "洗墙灯", "angle": [0, 0, 0, 1, 0, 0]},
                            {"category1": "线形灯具", "param_key": "wall_light_2", "algoKeyword": "洗墙灯", "angle": [0, 1, 0, 0, 0, 0]},
                            {"category1": "线形灯具", "param_key": "wall_light_3", "algoKeyword": "洗墙灯", "angle": [1, 0, 0, 0, 0, 0]},
                            {"category1": "智能面板", "param_key": "panel"},
                            {"category1": "IoT设备", "param_key": "gateway", "category2": "网关"},
                            {"category1": "LED室内驱动", "param_key": "led_driver", "algoKeyword": "天幕电源","category2": "室内非智能驱动"}
                        ]
                    }
                }
            },
            "走廊": {
                "build_func": self.build_corridor,
                "layout_func": self._layout_corridor,
                "schemes": {
                    "舒适光方案": {
                        "id": 1, "name": "舒适光方案",
                        "designConcept": "病房走廊是连接病房及功能空间的交通通道，照明需考虑安全、舒适，兼顾昼夜不同时段的需求，保障通行安全、照顾患者休息，同时实现高效节能与低维护运营。\n灯盘均匀布置，提供均匀明亮的光环境，保证通行安全，灯具表面微棱镜技术，降低表面亮度，保证舒适性。",
                        "sellingKeywords": "欧普舒适光", "sellingDescription": "舒适通途，明亮柔宜",
                        "defaults": [
                            {"category1": "灯盘", "category2": "直下式灯盘", "param_key": "main_light", "algoKeyword": "灯盘"}
                        ]
                    },
                    "节能光方案": {
                        "id": 2, "name": "节能光方案",
                        "designConcept": "病房走廊是连接病房及功能空间的交通通道，照明需考虑安全、舒适，\n两侧暗藏灯带提供一定的立面照明，搭配筒灯，营造明亮，舒适氛围，低表面亮度筒灯保证舒适性，实现安全节能。",
                        "sellingKeywords": "欧普节能光", "sellingDescription": "环保、自然、舒适",
                        "defaults": [
                            {"category1": "筒灯", "param_key": "main_light"},
                            {"category1": "低压灯带", "param_key": "strip_light_1", "angle": [0, 0, 0, 1, 0, 0]},
                            {"category1": "低压灯带", "param_key": "strip_light_2", "angle": [0, 0, 1, 0, 0, 1]}
                        ]
                    }
                }
            }
        }

    def _select_hospital_products(self, defaults, user_text="", scheme_name="", room_type=""):
        """Select products based on defaults and ward.md design logic."""
        products = []
        user_text_lower = user_text.lower() if user_text else ""
        for prod_config in defaults:
            category1 = prod_config.get("category1")
            category2 = prod_config.get("category2")
            algo_kw = prod_config.get("algoKeyword", "")
            
            product = {
                "category1": category1, "category2": category2,
                "materialCode": None, "location": [], "count": 1, 
                "angle": prod_config.get("angle", [0, 0, 0, 0, 0, 1]),
                "algoKeyword": algo_kw,
                "param_key": prod_config.get("param_key"),
                "w": prod_config.get("w", 0), "h": prod_config.get("h", 0),
                "power": None, "size": None, "series": None,
                "colorTemperature": None, "lumen": None, "pricePosition": None,
                "beamAngle": None, "holeSize": None, "assemble": None,
                "CRI": None, "UGR": None, "luminousEfficacy": None
            }

            # 1. 构造检索词
            search_base = algo_kw or category2 or category1
            if "灯盘" in search_base:
                if scheme_name == "舒适光方案" and room_type == "走廊":
                    search_base += " 300*1200"
                else:
                    search_base += " 600*600"
            
            if scheme_name == "节能光方案":
                if "筒灯" in search_base:
                    search_base += "  光束角70度 12w"
            
            search_query = f"{search_base} {user_text_lower}".strip()
            # print(f"Product Search Query: {search_query}")
            # if room_type == "走廊" and "低压灯带" in search_base:
            #     if not user_text_lower:
            #         search_query += " 12w"

            # 2. 向量检索 (Top 10)
            filters = {}
            if category1:
                filters["category1"] = category1
            if category2:
                filters["category2"] = category2

            candidates = self.retriever.search(search_query, top_k=3, filters=filters)
            
            if candidates:
                best_match = None
                # 优先级：默认 600*600, 其他特殊硬约束处理。
                # if not best_match and ("灯盘" in search_query or "天境" in search_query):
                    # for c in candidates:
                    #     size_str = str(c.get("size", ""))
                    #     if "600" in size_str and "*" in size_str:
                    #         best_match = c
                    #         break

                # 没有匹配到硬约束时，取得分最高项
                if not best_match:
                    best_match = candidates[0]
                
                # 如果配置中没给 category1，从检索结果中补全
                if not product["category1"]:
                    product["category1"] = best_match.get("category1")
                if not product["category2"]:
                    product["category2"] = best_match.get("category2")

                # 3. 提取并清洗元数据
                try:
                    p_val = best_match.get("power")
                    product["power"] = p_val if p_val else None
                except:
                    product["power"] = best_match.get("power")

                size_str = str(best_match.get("size", ""))
                try:
                    if "*" in size_str:
                        parts = size_str.split("*")
                        product["w"] = float(parts[0]) / 1000
                        product["h"] = float(parts[1]) / 1000
                        if float(parts[0]) < float(parts[1]):
                            product["w"], product["h"] = product["h"], product["w"]
                    elif size_str and size_str.lower().startswith("d"):
                        d_val = float(size_str[1:]) / 1000
                        product["w"] = product["h"] = d_val
                except:
                    pass

                product.update({
                    "materialCode": best_match.get("materialCode"),
                    "series": best_match.get("series"),
                    "size": best_match.get("size"),
                    "colorTemperature": best_match.get("colorTemp"),
                    "lumen": int(float(best_match["lumen"])) if best_match.get("lumen") else None,
                    "pricePosition": best_match.get("pricePosition"),
                    "beamAngle": best_match.get("beamAngle"),
                    "holeSize": best_match.get("holeSize"),
                    "assemble": best_match.get("assemble"),
                    "CRI": best_match.get("cri"),
                    "UGR": best_match.get("ugr"),
                    "luminousEfficacy": best_match.get("industyLevel"),
                    "category2": best_match.get("category2") or product["category2"]
                })
            products.append(product)
        return products
    def design_hospital(self, data: HospitalInputs):
        if data.roomType not in self.config:
            raise ValueError(f"Unknown room type: {data.roomType}")
            
        cfg = self.config[data.roomType]
        
        # Scheme routing
        scheme_name = data.tags
        text = (data.text or "").lower()
        if not scheme_name:
            raise ValueError("Scheme name must be specified in tags.")
        scheme_cfg = cfg["schemes"][scheme_name]
        
        # Build Geometry
        build_res = cfg["build_func"](data)
        outer_poly = None
        if isinstance(build_res, dict):
            room_list = build_res["roomList"]
            accessory = build_res.get("accessory", "")
            outer_poly = build_res.get("outer_poly")
        else:
            room_list = build_res
            accessory = ""
        
        # If outer_poly not in build_res, try to get from data
        if outer_poly is None:
            if hasattr(data, "outerPoly") and data.outerPoly:
                outer_poly = data.outerPoly
            else:
                outer_poly = None

        # Product Selection
        products = self._select_hospital_products(scheme_cfg["defaults"], user_text=data.text, scheme_name=scheme_name, room_type=data.roomType)
        
        # Layout
        cfg["layout_func"](products, room_list, data, scheme_name)

        # Standardize Output
        cleaned_products = []
        for p in products:
            if p.get("count", 0) > 0:
                cleaned_products.append(self._clean_product_for_output(p))
        
        plan_info = {
            "id": scheme_cfg["id"],
            "name": scheme_cfg["name"],
            "shape": getattr(data, "roomPolyType", None),
            "designConcept": scheme_cfg["designConcept"],
            "sellingKeywords": scheme_cfg["sellingKeywords"],
            "sellingDescription": scheme_cfg["sellingDescription"],
            "products": cleaned_products
        }
        
        return room_list, [plan_info], outer_poly

    def build_ward(self, data: HospitalInputs):
        import math
        width = data.width
        length = data.length
        height = data.height
        bedNum = data.bedNum
        has_toilet = bool(data.hasToilet)

        bed_w = 1.25
        bed_h = 2.2
        sofa_w = 1.8
        sofa_h = 0.76
        teapoy_w = 0.62
        teapoy_h = 0.62
        teapoy_sofa_gap = 0.55
        wall_board_w = 1.2
        wall_board_h = 0.02

        bathroom_w = 2
        bathroom_l = 1.9
        w = min(width, length)
        l = max(width, length)

        if has_toilet:
            bed_room_bbox = [0, w - bathroom_l, l - bathroom_w, w]
            pass_bbox = [0, 0, l, w - bathroom_l]
            toilet_bbox = [l - bathroom_w, w - bathroom_l, l, w]
        else:
            bed_room_bbox = [0, w - bathroom_l, l, w]
            pass_bbox = [0, 0, l, w - bathroom_l]
            toilet_bbox = [0, 0, 0, 0]

        bed_locations = []
        sofa_locations = []
        teapoy_locations = []
        if (bedNum == 1 and l >= 5 and not has_toilet) or (bedNum == 1 and l >= 7 and has_toilet):
            bed_locations.append({
                "x": 1.5,
                "y": bed_room_bbox[3] - bed_h / 2,
                "w": bed_w,
                "h": bed_h
            })
            sofa_locations.append({
                "x": 3 + sofa_w / 2,
                "y": bed_room_bbox[3] - sofa_h / 2,
                "w": sofa_w,
                "h": sofa_h
            })
            teapoy_locations.append({
                "x": 3 + sofa_w / 2,
                "y": bed_room_bbox[3] - sofa_h - teapoy_sofa_gap,
                "w": teapoy_w,
                "h": teapoy_h
            })
        else:
            for i in range(bedNum):
                x = (bed_room_bbox[2] - bed_room_bbox[0]) / bedNum * i + (bed_room_bbox[2] - bed_room_bbox[0]) / bedNum / 2
                y = bed_room_bbox[3] - bed_h / 2
                bed_locations.append({
                    "x": x,
                    "y": y,
                    "w": bed_w,
                    "h": bed_h
                })

        roomInfo_1 = {
            "name": "病房",
            "rectangle": {
                "x_min": bed_room_bbox[0],
                "y_min": bed_room_bbox[1],
                "z_min": 0,
                "x_max": bed_room_bbox[2],
                "y_max": bed_room_bbox[3],
                "z_max": height
            },
            "objects": [
                {
                    "type": "bed",
                    "locations": bed_locations
                }
            ]
        }
        
        if sofa_locations:
            roomInfo_1["objects"].append({
                "type": "sofa",
                "locations": sofa_locations
            })

        if teapoy_locations:
            roomInfo_1["objects"].append({
                "type": "teapoy",
                "locations": teapoy_locations
            })

        wall_board_locations = []
        board_num = math.ceil((pass_bbox[2] - pass_bbox[0]) / wall_board_w)
        for i in range(board_num):
            wall_board_locations.append({
                "x": (i * 2 + 1) * wall_board_w / 2,
                "y": 0,
                "w": wall_board_w,
                "h": wall_board_h
            })
            
        roomInfo_2 = {
            "name": "过道",
            "rectangle": {
                "x_min": pass_bbox[0],
                "y_min": pass_bbox[1],
                "z_min": 0,
                "x_max": pass_bbox[2],
                "y_max": pass_bbox[3],
                "z_max": height
            },
            "objects": [
                {
                    "type": "wall_board",
                    "locations": wall_board_locations
                }
            ]
        }
        
        roomInfo_3 = {
            "name": "卫生间",
            "rectangle": {
                "x_min": toilet_bbox[0],
                "y_min": toilet_bbox[1],
                "z_min": 0,
                "x_max": toilet_bbox[2],
                "y_max": toilet_bbox[3],
                "z_max": height
            },
            "objects": []
        }

        if has_toilet:
            return [roomInfo_1, roomInfo_2, roomInfo_3]
        else:
            return [roomInfo_1, roomInfo_2]

    def build_clinic(self, data: HospitalInputs):
        # Match Dify layout proportions for clinic
        length = data.length
        width = data.width
        height = data.height
        
        bed_w = 1.20
        bed_h = 2.28
        desk_w = 1.85
        desk_h = 2.6

        bed_locations = [{
            "x": float(round(length - 1.6 - bed_h / 2, 2)),
            "y": float(round(width - bed_w / 2, 2)),
            "w": bed_h,
            "h": bed_w
        }]
        desk_locations = [{
            "x": float(round(length - 1 - desk_h / 2, 2)),
            "y": float(round(desk_w / 2, 2)),
            "w": desk_h,
            "h": desk_w
        }]

        room_info = {
            "name": "诊室",
            "rectangle": {
                "x_min": 0.0,
                "y_min": 0.0,
                "z_min": 0,
                "x_max": float(round(length, 2)),
                "y_max": float(round(width, 2)),
                "z_max": float(round(height, 2))
            },
            "objects": [
                {
                    "type": "bed",
                    "locations": bed_locations
                },
                {
                    "type": "desk",
                    "locations": desk_locations
                }
            ]
        }
        return {
            "roomList": [room_info],
            "accessory": "IoT设备 智能面板"
        }

    def build_nurse_station(self, data: HospitalInputs):
        if not data.roomPolyType:
            raise ValueError("roomPolyType is required for nurse station design.")
        roomPolyType = data.roomPolyType
        height = data.height
        
        # Using pre-calculated polygons from data
        roomPolyLs = data.roomPolyLS
        
        nurse_poly = None
        pass_poly = None
        for room_poly in roomPolyLs:
            if room_poly["type"] == "护士站":
                nurse_poly = room_poly["poly"]
            elif room_poly["type"] == "过道":
                pass_poly = room_poly["poly"]

        # 1.2 Build Spatial Info and Object Positions
        desk_h = 0.8
        desk_c_h = 1.079
        desk_c_w = 1.153
        tv_w, tv_l, tv_z = 1.6, 0.8, 1.5
        bd_w, bd_l, bd_z = 0.4, 0.3, 1.7
        sd_w, sd_l, sd_z, sd_offset = 1.0, 2.7, 1.35, 0
        dd_w, dd_l, dd_z, dd_offset = 1.54, 2.1, 1.05, 0

        desk_pass_w = 0.8 if (nurse_poly[2][1] - nurse_poly[0][1]) <= 3 else 1.5

        roomInfo_1 = {
            "name": "护士站",
            "type": "护士站",
            "rectangle": {
                "x_min": nurse_poly[0][0],
                "y_min": nurse_poly[0][1],
                "z_min": 0,
                "x_max": nurse_poly[2][0],
                "y_max": nurse_poly[2][1],
                "z_max": height
                },
            "objects": [
                {
                    "type": "desk",
                    "locations": []
                }
            ]
        }

        if roomPolyType == "一":
            desk_locations = [
                {
                    "x": (nurse_poly[2][0] + nurse_poly[0][0]) / 2,
                    "y": nurse_poly[2][1] - desk_h / 2,
                    "w": nurse_poly[2][0] - nurse_poly[0][0] - 2,
                    "h": desk_h
                }
            ]
            
            roomInfo_1["objects"][0]["locations"] = desk_locations
            roomInfo_1["objects"].append({
                "type": "desk_combo",
                    "locations": desk_locations
            })
            
            if nurse_poly[1][0] - nurse_poly[0][0] >= 4:
                roomInfo_1["objects"].append({
                        "type": "tv",
                        "locations": [{
                            "x": nurse_poly[0][0] + 0.2 + tv_w / 2,
                            "y": nurse_poly[0][1],
                            "z": tv_z,
                            "w": tv_w,
                            "h": 0.1,
                            "l": tv_l
                        }]
                    })
            roomInfo_1["objects"].append({
                    "type": "single-door",
                    "locations": [{
                        "x": nurse_poly[1][0] - 0.5 - sd_w / 2,
                        "y": nurse_poly[0][1] + sd_offset,
                        "z": sd_z,
                        "w": sd_w,
                        "h": 0.1,
                        "l": sd_l
                    }]
                })

            roomInfo_1["objects"].append({
                    "type": "Consultation-board",
                    "locations": [{
                        "x": nurse_poly[1][0] - 0.5 - sd_w - 0.2 - bd_w / 2,
                        "y": nurse_poly[0][1],
                        "z": bd_z,
                        "w": bd_w,
                        "h": 0.1,
                        "l": bd_l
                    }]
                })
            
            if pass_poly[3][1] - pass_poly[0][1] >= 2.4:
                door_type = "double-door"
                d_w, d_z, d_l, d_offset = dd_w, dd_z, dd_l, dd_offset
            else:
                door_type = "single-door"
                d_w, d_z, d_l, d_offset = sd_w, sd_z, sd_l, sd_offset

            pass_h_top_door_num = int((nurse_poly[0][0] - pass_poly[0][0]) // 4)
            start_x = ((nurse_poly[0][0] - pass_poly[0][0]) - 4 * pass_h_top_door_num) / 2
            pass_door_pos_1 = []
            for i in range(pass_h_top_door_num):
                pass_door_pos_1.append({
                    "x": start_x + 2 * (1 + i * 2),
                    "y": pass_poly[0][1] + sd_offset,
                    "z": sd_z,
                    "w": sd_w,
                    "h": 0.1,
                    "l": sd_l
                })

            pass_h_top_door_num = int((pass_poly[1][0] - nurse_poly[1][0]) // 4)
            start_x = ((pass_poly[1][0] - nurse_poly[1][0]) - 4 * pass_h_top_door_num) / 2 + nurse_poly[1][0]
            for i in range(pass_h_top_door_num):
                pass_door_pos_1.append({
                    "x": start_x + 2 * (1 + i * 2),
                    "y": pass_poly[0][1] + sd_offset,
                    "z": sd_z,
                    "w": sd_w,
                    "h": 0.1,
                    "l": sd_l
                })

            pass_h_bot_door_num = int((pass_poly[1][0] - pass_poly[0][0]) // 4)
            start_x = ((pass_poly[1][0] - pass_poly[0][0]) - 4 * pass_h_bot_door_num) / 2
            for i in range(pass_h_bot_door_num):
                pass_door_pos_1.append({
                    "x": start_x + 2 * (1 + i * 2),
                    "y": pass_poly[2][1] - sd_offset,
                    "z": sd_z,
                    "w": sd_w,
                    "h": 0.1,
                    "l": sd_l,
                    "rotation": [0, 0, 180]
                })

            pass_door_pos_2 = []
            pass_door_pos_2.append({
                        "x": pass_poly[0][0] + d_offset,
                        "y": (pass_poly[3][1] + pass_poly[0][1]) / 2,
                        "z": d_z,
                        "w": d_w,
                        "h": 0.1,
                        "l": d_l,
                        "rotation": [0, 0, 270]
                    })
            
            pass_door_pos_2.append({
                        "x": pass_poly[1][0] - d_offset,
                        "y": (pass_poly[3][1] + pass_poly[0][1]) / 2,
                        "z": d_z,
                        "w": d_w,
                        "h": 0.1,
                        "l": d_l,
                        "rotation": [0, 0, 90]
                    })

            roomInfo_2 = {
                "name": "过道",
                "type": "过道_h",
                "rectangle": {
                    "x_min": pass_poly[0][0],
                    "y_min": pass_poly[0][1],
                    "z_min": 0,
                    "x_max": pass_poly[2][0],
                    "y_max": pass_poly[2][1],
                    "z_max": height
                    },
                "objects": [{
                    "type": "single-door",
                    "locations": pass_door_pos_1
                    },
                    {
                    "type": door_type,
                    "locations": pass_door_pos_2
                    }]
            }

            roomList = [roomInfo_1, roomInfo_2]

        elif roomPolyType == "L":
            desk_locations = [
                {
                    "x": (nurse_poly[2][0] + nurse_poly[0][0] - desk_c_w) / 2,
                    "y": nurse_poly[2][1] - desk_h / 2,
                    "w": nurse_poly[2][0] - nurse_poly[0][0] - desk_c_w,
                    "h": desk_h
                },
                {
                    "x": nurse_poly[2][0] - desk_h / 2,
                    "y": desk_pass_w + (nurse_poly[2][1] - nurse_poly[0][1] - desk_pass_w - desk_c_h) / 2,
                    "w": desk_h,
                    "h": nurse_poly[2][1] - nurse_poly[0][1] - desk_pass_w - desk_c_h
                }
            ]

            roomInfo_1["objects"][0]["locations"] = desk_locations
            roomInfo_1["objects"].append({
                    "type": "desk_c",
                    "locations": [
                        {
                            "x": nurse_poly[2][0] - desk_c_w / 2,
                            "y": nurse_poly[3][1] - desk_c_h / 2,
                            "w": desk_c_w,
                            "h": desk_c_h,
                        }
                    ]
                })

            roomInfo_1["objects"].append({
                "type": "desk_combo",
                    "locations": [{
                    "x": (nurse_poly[2][0] + nurse_poly[0][0]) / 2,
                    "y": (nurse_poly[2][1] - desk_pass_w) / 2 + desk_pass_w,
                    "w": nurse_poly[2][0] - nurse_poly[0][0],
                    "h": nurse_poly[2][1] - desk_pass_w
                }]
            })

            roomInfo_1["objects"].extend([{
                    "type": "tv",
                    "locations": [{
                        "x": nurse_poly[0][0] + (nurse_poly[2][0] - nurse_poly[0][0]) * 0.34,
                        "y": nurse_poly[0][1],
                        "z": tv_z,
                        "w": tv_w,
                        "h": 0.1,
                        "l": tv_l
                    }]
                },
                {
                    "type": "single-door",
                    "locations": [{
                        "x": nurse_poly[0][0] + sd_offset,
                        "y": nurse_poly[0][1] + 1,
                        "z": sd_z,
                        "w": sd_w,
                        "h": 0.1,
                        "l": sd_l,
                        "rotation": [0, 0, 270]
                    }]
                },
                {
                    "type": "Pre-IV-board",
                    "locations": [{
                        "x": nurse_poly[0][0] + (nurse_poly[2][0] - nurse_poly[0][0]) * 0.34 + 0.8 + 0.5,
                        "y": nurse_poly[0][1],
                        "z": bd_z,
                        "w": bd_w,
                        "h": 0.1,
                        "l": bd_l
                    }]
                },
                {
                    "type": "Consultation-board",
                    "locations": [
                    {
                        "x": nurse_poly[0][0],
                        "y": nurse_poly[0][1] + 1.5 + bd_w / 2 + 0.33,
                        "z": bd_z,
                        "w": bd_w,
                        "h": 0.1,
                        "l": bd_l,
                        "rotation": [0, 0, 270]
                    }
                    ]
                }
                ])
            
            if pass_poly[4][1] - pass_poly[0][1] >= 2.4:
                door_type = "double-door"
                d_w, d_z, d_l, d_offset = dd_w, dd_z, dd_l, dd_offset
            else:
                door_type = "single-door"
                d_w, d_z, d_l, d_offset = sd_w, sd_z, sd_l, sd_offset

            pass_h_top_door_num = int((nurse_poly[0][0] - pass_poly[0][0]) // 4)
            start_x = ((nurse_poly[0][0] - pass_poly[0][0]) - 4 * pass_h_top_door_num) / 2
            pass_door_pos_1 = []
            for i in range(pass_h_top_door_num):
                pass_door_pos_1.append({
                    "x": start_x + 2 * (1 + i * 2),
                    "y": pass_poly[0][1] + sd_offset,
                    "z": sd_z,
                    "w": sd_w,
                    "h": 0.1,
                    "l": sd_l
                })

            pass_h_bot_door_num = int((pass_poly[4][0] - pass_poly[0][0]) // 4)
            start_x = ((pass_poly[4][0] - pass_poly[0][0]) - 4 * pass_h_bot_door_num) / 2
            for i in range(pass_h_bot_door_num):
                pass_door_pos_1.append({
                    "x": start_x + 2 * (1 + i * 2),
                    "y": pass_poly[4][1] - sd_offset,
                    "z": sd_z,
                    "w": sd_w,
                    "h": 0.1,
                    "l": sd_l,
                    "rotation": [0, 0, 180]
                })

            pass_door_pos_2 = []
            pass_door_pos_2.append({
                        "x": pass_poly[0][0] + d_offset,
                        "y": (pass_poly[4][1] + pass_poly[0][1]) / 2,
                        "z": d_z,
                        "w": d_w,
                        "h": 0.1,
                        "l": d_l,
                        "rotation": [0, 0, 270]
                    })
            pass_door_pos_2.append({
                        "x": pass_poly[4][0] - d_offset,
                        "y": (pass_poly[4][1] + pass_poly[0][1]) / 2,
                        "z": d_z,
                        "w": d_w,
                        "h": 0.1,
                        "l": d_l,
                        "rotation": [0, 0, 90]
                    })

            roomInfo_2 = {
                "name": "过道",
                "type": "过道_h",
                "rectangle": {
                    "x_min": pass_poly[0][0],
                    "y_min": pass_poly[0][1],
                    "z_min": 0,
                    "x_max": pass_poly[1][0],
                    "y_max": pass_poly[4][1],
                    "z_max": height
                    },
                "objects": [{
                    "type": "single-door",
                    "locations": pass_door_pos_1
                    },
                    {
                    "type": door_type,
                    "locations": pass_door_pos_2
                    }
                ]
            }

            if pass_poly[4][0] - pass_poly[2][0] >= 2.4:
                door_type = "double-door"
                d_w, d_z, d_l, d_offset = dd_w, dd_z, dd_l, dd_offset
            else:
                door_type = "single-door"
                d_w, d_z, d_l, d_offset = sd_w, sd_z, sd_l, sd_offset

            door_pos = []
            roomInfo_3 = {
                "name": "过道",
                "type": "过道_r",
                "rectangle": {
                    "x_min": pass_poly[2][0],
                    "y_min": pass_poly[2][1],
                    "z_min": 0,
                    "x_max": pass_poly[4][0],
                    "y_max": pass_poly[1][1],
                    "z_max": height
                    },
                "objects": [{
                    "type": door_type,
                    "locations": [{
                        "x": (pass_poly[4][0] + pass_poly[2][0]) / 2,
                        "y": pass_poly[2][1] + d_offset,
                        "z": d_z,
                        "w": d_w,
                        "h": 0.1,
                        "l": d_l
                    }]
                }]
            }

            roomInfo_4 = {
                "name": "过道",
                "type": "过道_r_c",
                "rectangle": {
                    "x_min": pass_poly[1][0],
                    "y_min": pass_poly[1][1],
                    "z_min": 0,
                    "x_max": pass_poly[4][0],
                    "y_max": pass_poly[4][1],
                    "z_max": height
                    },
                "objects": []
            }

            roomList = [roomInfo_1, roomInfo_2, roomInfo_3, roomInfo_4]

        elif roomPolyType == "U":
            desk_locations = [
                {
                    "x": (nurse_poly[2][0] + nurse_poly[0][0]) / 2,
                    "y": nurse_poly[2][1] - desk_h / 2,
                    "w": nurse_poly[2][0] - nurse_poly[0][0] - desk_c_h * 2,
                    "h": desk_h
                },
                {
                    "x": nurse_poly[2][0] - desk_h / 2,
                    "y": nurse_poly[0][1] + desk_pass_w + (nurse_poly[2][1] - nurse_poly[0][1] - desk_c_h - desk_pass_w) / 2,
                    "w": desk_h,
                    "h": nurse_poly[2][1] - nurse_poly[0][1] - desk_c_h - desk_pass_w
                },
                {
                    "x": nurse_poly[0][0] + desk_h / 2,
                    "y": nurse_poly[0][1] + desk_pass_w + (nurse_poly[2][1] - nurse_poly[0][1] - desk_c_h - desk_pass_w) / 2,
                    "w": desk_h,
                    "h": nurse_poly[2][1] - nurse_poly[0][1] - desk_c_h - desk_pass_w
                }
            ]
            
            roomInfo_1["objects"][0]["locations"] = desk_locations
            roomInfo_1["objects"].append(
                {
                    "type": "desk_c",
                    "locations": [
                        {
                            "x": nurse_poly[0][0] + desk_c_h / 2,
                            "y": nurse_poly[3][1] - desk_c_h / 2,
                            "w": desk_c_h,
                            "h": desk_c_h,
                        },
                        {
                            "x": nurse_poly[1][0] - desk_c_h / 2,
                            "y": nurse_poly[3][1] - desk_c_h / 2,
                            "w": desk_c_h,
                            "h": desk_c_h,
                        }
                    ]
                }
            )

            roomInfo_1["objects"].append({
                "type": "desk_combo",
                    "locations": [{
                    "x": (nurse_poly[2][0] + nurse_poly[0][0]) / 2,
                    "y": (nurse_poly[2][1] - nurse_poly[0][1] - desk_pass_w) / 2 + desk_pass_w + nurse_poly[0][1],
                    "w": nurse_poly[2][0] - nurse_poly[0][0],
                    "h": nurse_poly[2][1] - nurse_poly[0][1] - desk_pass_w
                }]
            })

            if nurse_poly[1][0] - nurse_poly[0][0] >= 4:
                roomInfo_1["objects"].append({
                        "type": "tv",
                        "locations": [{
                            "x": nurse_poly[0][0] + 0.2 + tv_w / 2,
                            "y": nurse_poly[0][1],
                            "z": tv_z,
                            "w": tv_w,
                            "h": 0.1,
                            "l": tv_l
                        }]
                    })
            roomInfo_1["objects"].append({
                    "type": "single-door",
                    "locations": [{
                        "x": nurse_poly[1][0] - 0.5 - sd_w / 2,
                        "y": nurse_poly[0][1] + sd_offset,
                        "z": sd_z,
                        "w": sd_w,
                        "h": 0.1,
                        "l": sd_l
                    }]
                })

            roomInfo_1["objects"].append({
                    "type": "Consultation-board",
                    "locations": [{
                        "x": nurse_poly[1][0] - 0.5 - sd_w - 0.2 - bd_w / 2,
                        "y": nurse_poly[0][1],
                        "z": bd_z,
                        "w": bd_w,
                        "h": 0.1,
                        "l": bd_l
                    }]
                })
            
            if pass_poly[6][1] - pass_poly[3][1] >= 2.4:
                door_type = "double-door"
                d_w, d_z, d_l, d_offset = dd_w, dd_z, dd_l, dd_offset
            else:
                door_type = "single-door"
                d_w, d_z, d_l, d_offset = sd_w, sd_z, sd_l, sd_offset

            pass_door_pos_1 = []
            pass_h_bot_door_num = int((pass_poly[5][0] - pass_poly[0][0]) // 4)
            start_x = ((pass_poly[5][0] - pass_poly[0][0]) - 4 * pass_h_bot_door_num) / 2
            for i in range(pass_h_bot_door_num):
                pass_door_pos_1.append({
                    "x": start_x + 2 * (1 + i * 2),
                    "y": pass_poly[6][1] - sd_offset,
                    "z": sd_z,
                    "w": sd_w,
                    "h": 0.1,
                    "l": sd_l,
                    "rotation": [0, 0, 180]
                })

            pass_door_pos_2 = []
            pass_door_pos_2.append({
                        "x": pass_poly[0][0] + d_offset,
                        "y": (pass_poly[6][1] + pass_poly[2][1]) / 2,
                        "z": d_z,
                        "w": d_w,
                        "h": 0.1,
                        "l": d_l,
                        "rotation": [0, 0, 270]
                    })
            pass_door_pos_2.append({
                        "x": pass_poly[5][0] - d_offset,
                        "y": (pass_poly[6][1] + pass_poly[2][1]) / 2,
                        "z": d_z,
                        "w": d_w,
                        "h": 0.1,
                        "l": d_l,
                        "rotation": [0, 0, 90]
                    })

            roomInfo_2 = {
                "name": "过道",
                "type": "过道_h",
                "rectangle": {
                    "x_min": pass_poly[2][0],
                    "y_min": pass_poly[2][1],
                    "z_min": 0,
                    "x_max": pass_poly[3][0],
                    "y_max": pass_poly[6][1],
                    "z_max": height
                    },
                "objects": [{
                    "type": "single-door",
                    "locations": pass_door_pos_1
                    },
                    {
                    "type": door_type,
                    "locations": pass_door_pos_2
                    }]
            }

            # 右边过道
            if pass_poly[5][0] - pass_poly[4][0] >= 2.4:
                door_type = "double-door"
                d_w, d_z, d_l, d_offset = dd_w, dd_z, dd_l, dd_offset
            else:
                door_type = "single-door"
                d_w, d_z, d_l, d_offset = sd_w, sd_z, sd_l, sd_offset

            pass_door_pos_1 = []
            pass_door_pos_2 = []
            pass_v_r_door_num = int((pass_poly[3][1] - pass_poly[5][1]) // 4)
            start_y = ((pass_poly[3][1] - pass_poly[5][1]) - 4 * pass_v_r_door_num) / 2
            for i in range(pass_v_r_door_num):
                pass_door_pos_1.append({
                    "x": pass_poly[5][0] - sd_offset,
                    "y": pass_poly[5][1] + (i * 2 + 1) * 2 + start_y,
                    "z": sd_z,
                    "w": sd_w,
                    "h": 0.1,
                    "l": sd_l,
                    "rotation": [0, 0, 90]
                })

            pass_v_l_door_num = int((nurse_poly[1][1] - pass_poly[4][1]) // 4)
            start_y = ((nurse_poly[1][1] - pass_poly[4][1]) - 4 * pass_v_l_door_num) / 2
            for i in range(pass_v_l_door_num):
                pass_door_pos_1.append({
                    "x": pass_poly[4][0] + sd_offset,
                    "y": pass_poly[4][1] + (i * 2 + 1) * 2 + start_y,
                    "z": sd_z,
                    "w": sd_w,
                    "h": 0.1,
                    "l": sd_l,
                    "rotation": [0, 0, 270]
                })

            pass_door_pos_2.append({
                "x": (pass_poly[4][0] + pass_poly[5][0]) / 2,
                "y": pass_poly[4][1] + d_offset,
                "z": d_z,
                "w": d_w,
                "h": 0.1,
                "l": d_l,
                "rotation": [0, 0, 0]
            })

            roomInfo_3 = {
                "name": "过道",
                "type": "过道_r",
                "rectangle": {
                    "x_min": pass_poly[4][0],
                    "y_min": pass_poly[4][1],
                    "z_min": 0,
                    "x_max": pass_poly[6][0],
                    "y_max": pass_poly[3][1],
                    "z_max": height
                    },
                "objects": [
                    {
                    "type": "single-door",
                    "locations": pass_door_pos_1
                    },
                    {
                    "type": door_type,
                    "locations": pass_door_pos_2
                    }
                    ]
            }

            roomInfo_4 = {
                "name": "过道",
                "type": "过道_r_c",
                "rectangle": {
                    "x_min": pass_poly[3][0],
                    "y_min": pass_poly[3][1],
                    "z_min": 0,
                    "x_max": pass_poly[6][0],
                    "y_max": pass_poly[6][1],
                    "z_max": height
                    },
                "objects": []
            }

            # 左边过道
            if pass_poly[1][0] - pass_poly[0][0] >= 2.4:
                door_type = "double-door"
                d_w, d_z, d_l, d_offset = dd_w, dd_z, dd_l, dd_offset
            else:
                door_type = "single-door"
                d_w, d_z, d_l, d_offset = sd_w, sd_z, sd_l, sd_offset

            pass_door_pos_1 = []
            pass_door_pos_2 = []
            pass_v_r_door_num = int((nurse_poly[0][1] - pass_poly[1][1]) // 4)
            start_y = ((nurse_poly[0][1] - pass_poly[1][1]) - 4 * pass_v_r_door_num) / 2
            for i in range(pass_v_r_door_num):
                pass_door_pos_1.append({
                    "x": pass_poly[1][0] - sd_offset,
                    "y": pass_poly[1][1] + (i * 2 + 1) * 2 + start_y,
                    "z": sd_z,
                    "w": sd_w,
                    "h": 0.1,
                    "l": sd_l,
                    "rotation": [0, 0, 90]
                })

            pass_v_l_door_num = int((pass_poly[2][1] - pass_poly[0][1]) // 4)
            start_y = ((nurse_poly[2][1] - pass_poly[0][1]) - 4 * pass_v_l_door_num) / 2
            for i in range(pass_v_l_door_num):
                pass_door_pos_1.append({
                    "x": pass_poly[0][0] + sd_offset,
                    "y": pass_poly[0][1] + (i * 2 + 1) * 2 + start_y,
                    "z": sd_z,
                    "w": sd_w,
                    "h": 0.1,
                    "l": sd_l,
                    "rotation": [0, 0, 270]
                })

            pass_door_pos_2.append({
                "x": (pass_poly[0][0] + pass_poly[1][0]) / 2,
                "y": pass_poly[0][1] + d_offset,
                "z": d_z,
                "w": d_w,
                "h": 0.1,
                "l": d_l,
                "rotation": [0, 0, 0]
            })

            roomInfo_5 = {
                "name": "过道",
                "type": "过道_l",
                "rectangle": {
                    "x_min": pass_poly[0][0],
                    "y_min": pass_poly[0][1],
                    "z_min": 0,
                    "x_max": pass_poly[1][0],
                    "y_max": pass_poly[2][1],
                    "z_max": height
                    },
                "objects": [{
                    "type": "single-door",
                    "locations": pass_door_pos_1
                    },
                    {
                    "type": door_type,
                    "locations": pass_door_pos_2
                    }]
            }

            roomInfo_6 = {
                "name": "过道",
                "type": "过道_l_c",
                "rectangle": {
                    "x_min": pass_poly[2][0],
                    "y_min": pass_poly[2][1],
                    "z_min": 0,
                    "x_max": pass_poly[7][0],
                    "y_max": pass_poly[7][1],
                    "z_max": height
                    },
                "objects": []
            }

            roomList = [roomInfo_1, roomInfo_2, roomInfo_3, roomInfo_4, roomInfo_5, roomInfo_6]

        # 1.3 Add Desktops and Chairs
        desk_loc = roomList[0]["objects"][0]["locations"][0]
        desk_w, desk_h_size, desk_x, desk_y = desk_loc["w"], desk_loc["h"], desk_loc["x"], desk_loc["y"]
        desktop_num = 2 if desk_w >= 2 else 1
        gap_x = desk_w / desktop_num / 2
        dt_locs, ch_locs = [], []
        for i in range(desktop_num):
            x = desk_x - desk_w / 2 + (i * 2 + 1) * gap_x
            dt_locs.append({"x": x, "y": desk_y - 0.2, "z": 1, "w": 0.5, "h": 0.5, "l": 0.5})
            ch_locs.append({"x": x, "y": desk_y - 0.5, "z": 1, "w": 0.5, "h": 0.5, "l": 0.5})
        roomList[0]["objects"].append({"type": "desktop", "locations": dt_locs})
        roomList[0]["objects"].append({"type": "chair", "locations": ch_locs})

        return {
            "roomList": roomList,
            "accessory": "网关 智能开关",
            "outer_poly": data.outerPoly
        }

    def build_corridor(self, data: HospitalInputs):
        L = data.length
        W = data.width
        H = data.height
        
        sd_w, sd_l, sd_z, sd_offset = 1.0, 2.7, 1.35, 0
        dd_w, dd_l, dd_z, dd_offset = 1.54, 2.1, 1.05, 0
        door_gap = 4
        
        door_x_ls = [-sd_w / 2]
        pass_door_pos_1 = []
        h_door_num = int(L // door_gap)
        start_x = (L - door_gap * h_door_num) / 2
        
        for i in range(h_door_num):
            x = start_x + 2 * (1 + i * 2)
            # Side doors (top and bottom)
            pass_door_pos_1.append({
                "x": round_p(x), "y": round_p(0 - sd_offset), "z": sd_z,
                "w": sd_w, "h": 0.1, "l": sd_l, "rotation": [0, 0, 0]
            })
            pass_door_pos_1.append({
                "x": round_p(x), "y": round_p(W + sd_offset), "z": sd_z,
                "w": sd_w, "h": 0.1, "l": sd_l, "rotation": [0, 0, 180]
            })
            door_x_ls.append(x)
        
        door_x_ls.append(L + sd_w / 2)
        
        handrail_position = []
        for i in range(len(door_x_ls) - 1):
            x_mid = (door_x_ls[i] + door_x_ls[i + 1]) / 2
            w = door_x_ls[i + 1] - door_x_ls[i] - sd_w
            if w <= 0: continue
            handrail_position.append({
                "x": round_p(x_mid), "y": 0, "z": 0.8,
                "w": round_p(w), "h": 0.1, "l": 0, "rotation": [0, 0, 0]
            })
            handrail_position.append({
                "x": round_p(x_mid), "y": W, "z": 0.8,
                "w": round_p(w), "h": 0.1, "l": 0, "rotation": [0, 0, 180]
            })

        if W >= 2.4:
            door_type = "double-door"
            d_w, d_z, d_l, d_offset = dd_w, dd_z, dd_l, dd_offset
        else:
            door_type = "single-door"
            d_w, d_z, d_l, d_offset = sd_w, sd_z, sd_l, sd_offset
            
        pass_door_pos_2 = [
            {"x": round_p(0 - d_offset), "y": round_p(W / 2), "z": d_z, "w": d_w, "h": 0.1, "l": d_l, "rotation": [0, 0, 270]},
            {"x": round_p(L + d_offset), "y": round_p(W / 2), "z": d_z, "w": d_w, "h": 0.1, "l": d_l, "rotation": [0, 0, 90]}
        ]

        room_info = {
            "name": "走廊",
            "rectangle": {
                "x_min": 0, "y_min": 0, "z_min": 0,
                "x_max": L, "y_max": W, "z_max": H
            },
            "objects": [
                {"type": "single-door", "locations": pass_door_pos_1},
                {"type": door_type, "locations": pass_door_pos_2},
                {"type": "handrail", "locations": handrail_position}
            ]
        }
        return [room_info]

    # --- Layout Functions ---
    def _layout_ward(self, products, room_list, data, scheme_name):
        ward_room = next((r for r in room_list if r["name"] == "病房"), room_list[0])
        pass_room = next((r for r in room_list if r["name"] == "过道"), None)
        
        # Room dimensions (following Dify convention where y_max is min(W, L))
        room_h = ward_room["rectangle"]["y_max"] 
        
        # Constants from Dify
        bed_w = 1.25
        bed_h = 2.2
        bed_outer_h = 2.47
        wall_h = 0.228 
        
        beds = []
        for obj in ward_room.get("objects", []):
            if obj["type"] == "bed":
                for loc in obj["locations"]:
                    beds.append([
                        loc["x"] - loc["w"] / 2, loc["y"] - loc["h"] / 2,
                        loc["x"] + loc["w"] / 2, loc["y"] + loc["h"] / 2
                    ])
        
        teapoys = []
        for obj in ward_room.get("objects", []):
            if obj["type"] == "teapoy":
                for loc in obj["locations"]:
                    teapoys.append([loc["x"] - loc["w"] / 2, loc["y"] - loc["h"] / 2, loc["x"] + loc["w"] / 2, loc["y"] + loc["h"] / 2])

        pass_bbox = [0, 0, 0, 0]
        if pass_room:
            pr = pass_room["rectangle"]
            pass_bbox = [pr["x_min"], pr["y_min"], pr["x_max"], pr["y_max"]]

        # Position Calculations matching Dify exactly
        lamp_light_pos = [{"x": (b[0] + b[2]) / 2, "y": room_h - bed_h / 2} for b in beds]
        night_lights_pos_1 = [{"x": (b[0] + b[2]) / 2 + bed_w / 2 + 0.2, "y": room_h, "z": 0.3} for b in beds]
        
        # Determine if toilet exists
        has_toilet = any(r["name"] == "卫生间" for r in room_list)

        # Teapoy Spotlights - Dify puts spots at loc["y"]
        teapoy_spot_pos = []
        for o in ward_room.get("objects", []):
            if o["type"] == "teapoy":
                for loc in o["locations"]:
                    x, y = loc["x"], loc["y"]
                    teapoy_spot_pos.append({"x": round(x - 0.055, 2), "y": round(y, 2)})
                    teapoy_spot_pos.append({"x": round(x + 0.055, 2), "y": round(y, 2)})

        # Final Spotlight assembly based on scheme
        final_spot_pos = []
        if "品质" in scheme_name or "节律" in scheme_name:
            # Quality/Rhythm have general corridor spots + teapoy spots
            if pass_room:
                spot_num = round((pass_bbox[2] - pass_bbox[0] - 2) / 1.8)
                if spot_num > 0:
                    for i in range(int(spot_num)):
                        x = (pass_bbox[2] - pass_bbox[0]) / (spot_num + 1) * (i + 1)
                        final_spot_pos.append({"x": round(x, 2), "y": round((room_h - bed_outer_h) / 2, 2)})
            
            final_spot_pos.extend(teapoy_spot_pos)

        elif "疗愈" in scheme_name:
            # Healing spots (Toilet + Teapoy special corridor spot + Teapoy bedside spots)
            if has_toilet:
                # Dify adds a spot near toilet entrance
                final_spot_pos.append({
                    "x": round(pass_bbox[2] - 0.5, 2),
                    "y": round((pass_bbox[3] + pass_bbox[1]) / 2, 2)
                })
            
            if teapoys:
                # Special corridor spot for Healing scheme when teapoy exists
                x_center = (teapoys[0][0] + teapoys[0][2]) / 2
                final_spot_pos.append({"x": round(x_center, 2), "y": round((room_h - bed_outer_h) / 2, 2)})
            
            final_spot_pos.extend(teapoy_spot_pos)

        if "品质" in scheme_name:
            for p in products:
                loc_w, loc_h = p.get("w", 0), p.get("h", 0)
                if p.get("category1") == "灯盘":
                    p["location"] = [{"x": l["x"], "y": l["y"], "w": loc_w, "h": loc_h} for l in lamp_light_pos]
                    p["count"] = len(lamp_light_pos)
                elif p.get("category1") == "筒灯":
                    p["location"] = [{"x": l["x"], "y": l["y"], "w": loc_w, "h": loc_h} for l in final_spot_pos]
                    p["count"] = len(final_spot_pos)
                elif p.get("category1") == "夜灯":
                    p["location"] = [{"x": l["x"], "y": l["y"], "z": l.get("z", 0.3), "w": loc_w, "h": loc_h} for l in night_lights_pos_1]
                    p["count"] = len(night_lights_pos_1)
                elif p.get("category1") == "低压灯带":
                    p["location"] = [{"x": (pass_bbox[2] - pass_bbox[0]) / 2, "y": 0.15, "w": pass_bbox[2] - pass_bbox[0]}]
                    p["count"] = math.ceil(p["location"][0]["w"] / 10) if p["location"] else 0

        elif "疗愈" in scheme_name:
            wall_light_pos = [{"x": (b[0] + b[2]) / 2, "y": b[3] - wall_h / 2} for b in beds]
            sky_light_pos = []
            for b in beds:
                x = (b[0] + b[2]) / 2
                sky_light_pos.append({"x": round(x - 0.35, 2), "y": round((room_h - bed_outer_h) / 2, 2)})
                sky_light_pos.append({"x": round(x + 0.35, 2), "y": round((room_h - bed_outer_h) / 2, 2)})

            for p in products:
                loc_w, loc_h = p.get("w", 0), p.get("h", 0)
                if p.get("category1") == "壁灯":
                    p["location"] = [{"x": l["x"], "y": l["y"], "w": loc_w, "h": loc_h} for l in wall_light_pos]
                    p["count"] = len(wall_light_pos)
                elif "灯盘" in (p.get("category1") or ""):
                    p["location"] = [{"x": l["x"], "y": l["y"], "w": loc_w, "h": loc_h} for l in sky_light_pos]
                    p["count"] = len(sky_light_pos)
                elif p.get("category1") == "筒灯":
                    p["location"] = [{"x": l["x"], "y": l["y"], "w": loc_w, "h": loc_h} for l in final_spot_pos]
                    p["count"] = len(final_spot_pos)
                elif p.get("category1") == "夜灯":
                    p["location"] = [{"x": l["x"], "y": l["y"], "z": l.get("z", 0.3), "w": loc_w, "h": loc_h} for l in night_lights_pos_1]
                    p["count"] = len(night_lights_pos_1)

        else: # 节律光
            for p in products:
                loc_w, loc_h = p.get("w", 0), p.get("h", 0)
                if "灯盘" in (p.get("category1") or ""):
                    p["location"] = [{"x": l["x"], "y": l["y"], "w": loc_w, "h": loc_h} for l in lamp_light_pos]
                    p["count"] = len(lamp_light_pos)
                elif p.get("category1") == "筒灯":
                    p["location"] = [{"x": l["x"], "y": l["y"], "w": loc_w, "h": loc_h} for l in final_spot_pos]
                    p["count"] = len(final_spot_pos)
                elif p.get("category1") == "夜灯":
                    p["location"] = [{"x": l["x"], "y": l["y"], "z": l.get("z", 0.3), "w": loc_w, "h": loc_h} for l in night_lights_pos_1]
                    p["count"] = len(night_lights_pos_1)
                elif p.get("category1") == "低压灯带":
                    p["location"] = [{"x": (pass_bbox[2] - pass_bbox[0]) / 2, "y": 0.15, "w": pass_bbox[2] - pass_bbox[0]}]
                    p["count"] = math.ceil(p["location"][0]["w"] / 10) if p["location"] else 0

        # Common (IoT/Panels)
        for p in products:
            if p.get("category1") in ["IoT设备", "智能面板"] and not p.get("location"):
                p["location"] = [{"x": 0.0, "y": 0.0, "w": p.get("w", 0), "h": p.get("h", 0)}]
                p["count"] = 1

    def _layout_clinic(self, products, room_list, data, scheme_name):
        gap = 1.8
        revise_gap = 0.05
        room = next((r for r in room_list if r["name"] == "诊室"), None)
        if not room: return
        
        consult_w = room["rectangle"]["x_max"] - room["rectangle"]["x_min"]
        consult_h = room["rectangle"]["y_max"] - room["rectangle"]["y_min"]
        
        beds = []
        desks = []
        for obj in room["objects"]:
            if obj["type"] == "bed":
                for loc in obj["locations"]:
                    beds.append([loc["x"], loc["y"], loc["w"], loc["h"]])
            if obj["type"] == "desk":
                for loc in obj["locations"]:
                    desks.append([loc["x"], loc["y"], loc["w"], loc["h"]])
                    
        bed_locations = [{"x": b[0], "y": b[1]} for b in beds]
        
        # Table lamp height from Dify (悅瞳)
        table_lamp_h = 0.605
        table_lamp_locations = []
        for desk in desks:
            table_lamp_locations.append({
                "x": round_p(desk[0] + desk[2] / 2),
                "y": round_p(table_lamp_h / 2)
            })
            
        lamp_locations = []
        lamp_w_num = int(consult_w // gap)
        lamp_h_num = int(consult_h // gap)
        
        # Ensure at least one if room is small
        if lamp_w_num == 0: lamp_w_num = 1
        if lamp_h_num == 0: lamp_h_num = 1
        
        start_x = (consult_w - (lamp_w_num - 1) * gap) / 2
        start_y = (consult_h - (lamp_h_num - 1) * gap) / 2
        for i in range(lamp_w_num):
            for j in range(lamp_h_num):
                lamp_locations.append({
                    "x": round_p(start_x + (i * gap)),
                    "y": round_p(start_y + (j * gap))
                })
        
        def box_in_box(box1, box2):
            for pt in box1:
                # pt is [x, y]
                if box2[0][0] < pt[0] < box2[2][0] and box2[0][1] < pt[1] < box2[2][1]:
                    return True
            return False

        if beds:
            # Dify uses beds[0] directly
            b = beds[0]
            # [xmin, ymin], [xmax, ymin], [xmax, ymax], [xmin, ymax]
            bed_box = [
                [b[0] - b[2]/2, b[1] - b[3]/2], [b[0] + b[2]/2, b[1] - b[3]/2],
                [b[0] + b[2]/2, b[1] + b[3]/2], [b[0] - b[2]/2, b[1] + b[3]/2]
            ]
            y_map = {}
            for idx, lamp in enumerate(lamp_locations):
                # 0.6x0.6 lamp box
                l_box = [
                    [lamp["x"] - 0.3, lamp["y"] - 0.3], [lamp["x"] + 0.3, lamp["y"] - 0.3],
                    [lamp["x"] + 0.3, lamp["y"] + 0.3], [lamp["x"] - 0.3, lamp["y"] + 0.3]
                ]
                if box_in_box(l_box, bed_box):
                    y_map[lamp["y"]] = b[1] - b[3]/2 - 0.3 - revise_gap

            for idx, lamp in enumerate(lamp_locations):
                if lamp["y"] in y_map:
                    lamp_locations[idx]["y"] = round_p(y_map[lamp["y"]])

        # Comfort/Quality Light: remove closest to table lamp
        if ("舒适" in scheme_name or "质量" in scheme_name) and lamp_locations and table_lamp_locations:
            t = table_lamp_locations[0]
            remove_idx = 0
            min_dis = 999
            for idx, lamp in enumerate(lamp_locations):
                d = ((t["x"]-lamp["x"])**2 + (t["y"]-lamp["y"])**2)**0.5
                if d < min_dis:
                    min_dis = d
                    remove_idx = idx
            lamp_locations.pop(remove_idx)

        # Final assignments
        for p in products:
            c1, c2 = p.get("category1"), p.get("category2")
            if c2 == "直下式灯盘" or c1 == "灯盘":
                p["location"] = [{"x": l["x"], "y": l["y"], "w": 0.6, "h": 0.6} for l in lamp_locations]
                p["count"] = len(lamp_locations)
            elif c1 == "筒灯":
                # Cleaning/Comfort: bedside spotlights
                p["location"] = [{"x": l["x"], "y": l["y"], "w": 0.09, "h": 0.09} for l in bed_locations]
                p["count"] = len(bed_locations)
            elif c1 in ["护眼台灯", "台灯"]:
                p["location"] = [{"x": l["x"], "y": l["y"], "w": 0.34, "h": 0.605} for l in table_lamp_locations]
                p["count"] = len(table_lamp_locations)
            elif c1 in ["IoT设备", "智能面板"]:
                p["location"] = [{"x": 0.0, "y": 0.0}]
                p["count"] = 1

    def _layout_nurse_station(self, products, room_list, data, scheme_name):
        room_poly_type = getattr(data, "roomPolyType", "一")
        desk_c_h = 1.16
        pass_lamp_gap = 3
        pass_spot_gap = 2
        sdl_h = 0.4

        def do_pass_h(pass_room):
            light_locations = []
            if (pass_room[3] - pass_room[1]) >= 3:  
                light_type = "lamp"
                light_gap = pass_lamp_gap
            else:
                light_type = "spot"
                light_gap = pass_spot_gap
            light_num = int(round((pass_room[2] - pass_room[0]) / light_gap))
            if light_num > 0:
                start_x = pass_room[0] + ((pass_room[2] - pass_room[0]) - (light_num - 1) * light_gap) / 2
                for i in range(light_num):
                    light_locations.append({
                        "x": start_x + i * light_gap,
                        "y": (pass_room[1] + pass_room[3]) / 2
                    })
            return light_locations, light_type
        
        def do_pass_v(pass_room):
            light_locations = []
            if (pass_room[2] - pass_room[0]) >= 3:  
                light_type = "lamp"
                light_gap = pass_lamp_gap
            else:
                light_type = "spot"
                light_gap = pass_spot_gap
            light_num = int(round((pass_room[3] - pass_room[1]) / light_gap))
            if light_num > 0:
                start_y = pass_room[1] + ((pass_room[3] - pass_room[1]) - (light_num - 1) * light_gap) / 2
                for i in range(light_num):
                    light_locations.append({
                        "x": (pass_room[0] + pass_room[2]) / 2,
                        "y": start_y + i * light_gap,
                        "rotation": [0, 0, 90]
                    })
            return light_locations, light_type
        
        def do_pass_c(pass_room):
            light_locations = []
            if (pass_room[3] - pass_room[1]) >= 3:  
                light_type = "lamp"
            else:
                light_type = "spot"
            light_locations.append({
                "x": (pass_room[2] + pass_room[0]) / 2,
                "y": (pass_room[1] + pass_room[3]) / 2
            })
            return light_locations, light_type

        lamp_locations = []
        spot_locations = []
        sdl_locations = []
        wall_locations_1 = []
        wall_locations_2 = []
        wall_locations_3 = []

        nurse_room = [0, 0, 0, 0]
        desk_ls = []
        pass_room = None
        pass_room_r = pass_room_l = pass_room_r_c = pass_room_l_c = None

        for room in room_list:
            rect = [room["rectangle"]["x_min"], room["rectangle"]["y_min"], room["rectangle"]["x_max"], room["rectangle"]["y_max"]]
            if room["name"] == "护士站":
                nurse_room = rect
                for obj in room["objects"]:
                    if obj["type"] == "desk":
                        for loc in obj["locations"]:
                            desk_ls.append([loc["x"], loc["y"], loc["w"], loc["h"]])
            if room["type"] == "过道_h":
                pass_room = rect
            if room["type"] == "过道_r":
                pass_room_r = rect
            if room["type"] == "过道_l":
                pass_room_l = rect
            if room["type"] == "过道_r_c":
                pass_room_r_c = rect
            if room["type"] == "过道_l_c":
                pass_room_l_c = rect
            
        # Front spots for nurse station
        nurse_spot_num = int(round((nurse_room[2] - nurse_room[0] - 1) / 0.8))
        if nurse_spot_num > 1:
            nurse_spot_gap = (nurse_room[2] - nurse_room[0] - 1) / (nurse_spot_num - 1)
            start_x = 0.5 + nurse_room[0]
            for i in range(nurse_spot_num):
                spot_locations.append({
                    "x": start_x + i * nurse_spot_gap,
                    "y": nurse_room[1] + 0.5
                })
        
        if desk_ls:
            wall_locations_1.append({
                "x": desk_ls[0][0],
                "y": nurse_room[3] - 0.41,
                "w": desk_ls[0][2]
            })

        if pass_room:
            light_locs, light_type = do_pass_h(pass_room)
            if light_type == "lamp": lamp_locations.extend(light_locs)
            else: spot_locations.extend(light_locs)

        if room_poly_type == "一":    
            if desk_ls:
                sdl_locations.append({
                    "x": desk_ls[0][0],
                    "y": nurse_room[3] - 0.2,
                    "w": desk_ls[0][2],
                    "h": sdl_h
                })

        elif room_poly_type == "L" and len(desk_ls) >= 2:
            sdl_locations.append({
                "x": desk_ls[0][0] + desk_c_h / 2,
                "y": nurse_room[3] - 0.2,
                "w": desk_ls[0][2] + desk_c_h,
                "h": sdl_h
            })
            sdl_locations.append({
                "x": nurse_room[2] - 0.2,
                "y": desk_ls[1][1] + desk_c_h / 2 - 0.2,
                "w": sdl_h,
                "h": desk_ls[1][3] + desk_c_h - 0.4
            })
            if pass_room_r:
                light_locs, light_type = do_pass_v(pass_room_r)
                if light_type == "lamp": lamp_locations.extend(light_locs)
                else: spot_locations.extend(light_locs)
            if pass_room_r_c:
                light_locs, light_type = do_pass_c(pass_room_r_c)
                if light_type == "lamp": lamp_locations.extend(light_locs)
                else: spot_locations.extend(light_locs)
        
        elif room_poly_type == "U" and len(desk_ls) >= 3:
            sdl_locations.append({
                "x": (nurse_room[0] + nurse_room[2]) / 2,
                "y": nurse_room[3] - 0.2,
                "w": nurse_room[2] - nurse_room[0],
                "h": sdl_h
            })
            sdl_locations.append({
                "x": nurse_room[2] - 0.2,
                "y": desk_ls[1][1] + (desk_c_h - 0.4) / 2,
                "w": sdl_h,
                "h": desk_ls[1][3] + desk_c_h - 0.4
            })
            sdl_locations.append({
                "x": nurse_room[0] + 0.2,
                "y": desk_ls[2][1] + (desk_c_h - 0.4) / 2,
                "w": sdl_h,
                "h": desk_ls[2][3] + desk_c_h - 0.4
            })
            wall_locations_2.append({
                "x": nurse_room[2] - 0.41,
                "y": desk_ls[1][1],
                "w": desk_ls[1][3],
                "rotation": [0, 0, 90]
            })
            wall_locations_3.append({
                "x": nurse_room[0] + 0.41,
                "y": desk_ls[2][1],
                "w": desk_ls[2][3],
                "rotation": [0, 0, 90]
            })
            if pass_room_r:
                light_locs, light_type = do_pass_v(pass_room_r)
                if light_type == "lamp": lamp_locations.extend(light_locs)
                else: spot_locations.extend(light_locs)
            if pass_room_r_c:
                light_locs, light_type = do_pass_c(pass_room_r_c)
                if light_type == "lamp": lamp_locations.extend(light_locs)
                else: spot_locations.extend(light_locs)
            if pass_room_l:
                light_locs, light_type = do_pass_v(pass_room_l)
                if light_type == "lamp": lamp_locations.extend(light_locs)
                else: spot_locations.extend(light_locs)
            if pass_room_l_c:
                light_locs, light_type = do_pass_c(pass_room_l_c)
                if light_type == "lamp": lamp_locations.extend(light_locs)
                else: spot_locations.extend(light_locs)

        # Mapping back to the products list
        wall_light_cnt_1 = sum(loc["w"] for loc in wall_locations_1)
        wall_light_cnt_2 = sum(loc["w"] for loc in wall_locations_2)
        wall_light_cnt_3 = sum(loc["w"] for loc in wall_locations_3)

        # Calculate SDL Power for later if needed (keeping existing service logic)
        tm_l = 0
        for i, loc in enumerate(sdl_locations):
            if i == 0: tm_l += loc.get("w", 0)
            else: tm_l += loc.get("h", 0)
        dengzhu_w = int(tm_l / 0.15) + 1
        tm_power = 3 * dengzhu_w * 2.1

        for p in products:
            if p.get("category1") == "灯盘":
                p["location"] = lamp_locations
                p["count"] = len(lamp_locations)
            elif p.get("category1") == "筒灯":
                p["location"] = spot_locations
                p["count"] = len(spot_locations)
            elif p.get("algoKeyword") == "天幕灯具":
                p["location"] = sdl_locations
                p["count"] = 1 # Grouped
                p["power"] = f"{tm_power:.1f}"
                p["category1"] = "模组"
            elif p.get("algoKeyword") == "洗墙灯":
                angle = p.get("angle")
                if angle == [0, 0, 0, 1, 0, 0]:
                    p["location"] = wall_locations_1
                    p["count"] = int(round(wall_light_cnt_1))
                elif angle == [0, 1, 0, 0, 0, 0]:
                    p["location"] = wall_locations_2
                    p["count"] = int(round(wall_light_cnt_2))
                elif angle == [1, 0, 0, 0, 0, 0]:
                    p["location"] = wall_locations_3
                    p["count"] = int(round(wall_light_cnt_3))
            elif p.get("category1") in ["IoT设备", "智能面板", "LED室内驱动", "天幕电源", "天幕控制器"] or p.get("category2") in ["网关", "智能开关"]:
                p["location"] = [{"x": 0, "y": 0}]
                p["count"] = 1

    def _layout_corridor(self, products, room_list, data, scheme_name):
        L = data.length
        W = data.width
        H = data.height
        
        # 1. 舒适光方案
        if scheme_name == "舒适光方案":
            gap = 3
            lamp_num = int(L / gap)
            start_x = (L - (lamp_num - 1) * gap) / 2
            lamp_locations = []
            for i in range(lamp_num):
                lamp_locations.append({
                    "x": round_p(start_x + i * gap),
                    "y": round_p(W / 2),
                    "z": 0,
                    "rotation": [0, 0, 90]
                })
            
            for p in products:
                if p.get("category1") == "灯盘" or p.get("category2") == "直下式灯盘":
                    p["location"] = lamp_locations
                    p["count"] = len(lamp_locations)
                    p["angle"] = [0, 0, 0, 0, 0, 1]
                    
        # 2. 节能光方案
        elif scheme_name == "节能光方案":
            gap = 2
            lamp_num = int(L / gap)
            start_x = (L - (lamp_num - 1) * gap) / 2
            lamp_num_v = 2 + int((W - 4) // 2) if W >= 4 else 1
            
            lamp_locations = []
            for i in range(lamp_num_v):
                y = W / (lamp_num_v + 1) * (i + 1)
                for j in range(lamp_num):
                    lamp_locations.append({
                        "x": round_p(start_x + j * gap),
                        "y": round_p(y),
                        "z": 0,
                        "rotation": [0, 0, 0]
                    })
            
            strip_loc_1 = [{
                "x": round_p(L / 2), "y": 0.15, "z": 0, "w": L, "rotation": [0, 0, 0]
            }]
            strip_loc_2 = [{
                "x": round_p(L / 2), "y": round_p(W - 0.15), "z": 0, "w": L, "rotation": [0, 0, 0]
            }]

            for p in products:
                if p.get("category1") == "筒灯":
                    p["location"] = lamp_locations
                    p["count"] = len(lamp_locations)
                    p["angle"] = [0, 0, 0, 0, 0, 1]
                elif p.get("param_key") == "strip_light_1":
                    p["location"] = strip_loc_1
                    p["count"] = math.ceil(L / 10)
                elif p.get("param_key") == "strip_light_2":
                    p["location"] = strip_loc_2
                    p["count"] = math.ceil(L / 10)

        # 3. 网关与面板 (Dify often appends these)
        for p in products:
            if p.get("category1") == "IoT设备":
                p["location"] = [{"x": 0.0, "y": 0.0}]
                p["count"] = 1
            elif p.get("category1") == "智能面板":
                p["location"] = [{"x": 0.0, "y": 0.0}]
                p["count"] = 1

    def _clean_product_for_output(self, p):
        """Standardize product dictionary."""
        p.pop("area", None)
        p.pop("param_key", None)
        
        # Inject dimensions into locations based on Dify logic
        # p["w"] and p["h"] were set in _select_hospital_products or defaults
        p_w = p.get("w")
        p_h = p.get("h")
        
        if p_w and p_h:
            for loc in p.get("location", []):
                # Dify: if not loc.get("w"): loc["w"] = p_w; loc["h"] = p_h
                if not loc.get("w"):
                    loc["w"] = p_w
                if not loc.get("h"):
                    loc["h"] = p_h

        # Avoid unnecessary algoKeyword
        if p.get("algoKeyword") not in ["洗墙灯", "天幕灯具", "天幕电源", "天幕控制器", "网关", "线形灯具", "灯盘", "夜灯"]:
            p.pop("algoKeyword", None)

        # Removed 'w' and 'h' from product level as Dify doesn't have them at top level
        p.pop("w", None)
        p.pop("h", None)

        if p.get("category1") in ["智能面板", "筒灯"]:
            # Dify doesn't have these top level dimensions for these
            pass

        for loc in p.get("location", []):
            if "x" in loc: loc["x"] = round_p(loc["x"])
            if "y" in loc: loc["y"] = round_p(loc["y"])
            if "w" in loc: loc["w"] = round_p(loc["w"])
            if "h" in loc: loc["h"] = round_p(loc["h"])
            if "z" in loc: loc["z"] = round_p(loc["z"])
            if "l" in loc: loc["l"] = round_p(loc["l"])

        # Special case: map category1 from '天境' to '灯盘' again to be safe
        if p.get("category1") == "天境":
            p["category1"] = "灯盘"
            
        for key in ["beamAngle", "CRI", "luminousEfficacy", "colorTemperature", "holeSize", "assemble", "size", "UGR", "power", "series"]:
            val = p.get(key)
            if not val or val == "None" or val == "0" or val == "0.0" or val == 0 or val == 0.0:
                p[key] = None # Dify prefers null/None for missing metadata
        
        return p

