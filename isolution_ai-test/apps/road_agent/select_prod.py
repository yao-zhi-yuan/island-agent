import math
import pandas as pd
from apps.road_agent.prod_datasets import prod_dataset


class SelectProd:
    def __init__(self):
        self.defult_colorTemp = "4000"      # 默认色温
        self.defult_ploe_series = "东方明珠"
        self.defult_light_series = "北斗星"
        self.defult_module_series = "清致II"
        self.controller = {
            "materialCode": None,
            "category1": "道路灯具",
            "category2": "控制器",
        }
        self.power = {
            "materialCode": None,
            "category1": "道路灯具",
            "category2": "电源",
        }

    def load_prod_data(self):
        df = pd.read_csv(self.prod_file, encoding="utf-8")
        df = df.fillna("")
        prod_ls = df.to_dict(orient='records')
        return prod_ls


    def select(self, planInfo, params):
        colorTemp = self.defult_colorTemp if not params["colorTemp"] else params["colorTemp"]
        power_mapper = {}
        power1 = params.get("power1", None)
        power2 = params.get("power2", None)
        lumEff = params.get("lumEff", None)
        pole_series = self.defult_ploe_series if not params["pole_series"] else params["pole_series"]
        light_series = self.defult_light_series if not params["light_series"] else params["light_series"]
        module_series = self.defult_module_series if not params["module_series"] else params["module_series"]
        controllers = []
        powers = []
        # 初始标准灯杆
        pole_type = 1
        lightArmType = "平行臂"
        light_num = 0
        pole_num = 0
        for prod in planInfo["products"]:
            if prod["category2"] == "灯杆":
                lightArmType = prod["lightArmType"]
                pole_num += prod["count"]

        for prod in planInfo["products"]:
            if prod["category2"] == "灯杆":
                lightArmType = prod["lightArmType"]
                pole_ls = prod_dataset.prod_df[(prod_dataset.prod_df["二级分类名称"] == "灯杆") & (prod_dataset.prod_df["系列"] == pole_series)]
                if len(pole_ls) > 0:
                    prod["description"] = pole_ls.iloc[0]["物料描述"]
                    prod["materialCode"] = str(pole_ls.iloc[0]["物料号"])
                    prod["series"] = pole_ls.iloc[0]["系列"]
                    prod["height"] = planInfo["lightPoleHeight"]
                    prod["pricePosition"] = pole_ls.iloc[0]["定位"]
                    prod["price"] = str(int(pole_ls.iloc[0]["产品价格"]))
                for idx, bulb in enumerate(prod["lightBulb"]):
                    if idx == 0:
                        base_power = bulb["power"] if not power1 else power1
                        power_mapper[str(bulb["power"]) + "_" + bulb["pos"]] = base_power
                    elif idx== 1:
                        if lightArmType == "平行臂" and power2 is None and power1 is not None:
                            base_power = power1
                        else:
                            base_power = bulb["power"] if not power2 else power2
                        power_mapper[str(bulb["power"]) + "_" + bulb["pos"]] = base_power
                        
                    if int(pole_ls.iloc[0]["标准灯杆"]) == 0:
                        bulb_candidates = self.select_light(module_series, base_power, colorTemp, type="模组")
                        cnt = math.ceil(int(base_power) / int(bulb_candidates[0]["功率(w)"]))
                        pole_type = 0
                    else:
                        bulb_candidates = self.select_light(light_series, base_power, colorTemp, type="路灯")
                        cnt = 1
                   
                    if len(bulb_candidates) > 0:
                        bulb["materialCode"] = str(bulb_candidates[0]["物料号"])
                        bulb["series"] = bulb_candidates[0]["系列"]
                        bulb["power"] = str(int(bulb_candidates[0]["功率(w)"]))
                        bulb["lmEff"] = lumEff if lumEff else str(int(bulb_candidates[0]["光效(lm/w)"]))
                        bulb["lumen"] = str(int(bulb["lmEff"]) * int(bulb["power"]))
                        bulb["colorTemperature"] = str(int(bulb_candidates[0]["色温(k)"]))
                        bulb["pricePosition"] = bulb_candidates[0]["定位"]
                        bulb["category2"] = bulb_candidates[0]["二级分类名称"]
                        bulb["count"] = cnt
                
            elif prod["category2"] == "路灯":
                base_power = power_mapper[str(prod["power"]) + "_" + prod["pos"]]
                if pole_type == 0:
                    candidates = self.select_light(module_series, base_power, colorTemp, type="模组")
                    cnt = math.ceil(int(base_power) / int(candidates[0]["功率(w)"]))
                else:
                    candidates = self.select_light(light_series, base_power, colorTemp, type="路灯")
                    cnt = 1
                
                if len(candidates) > 0:
                    prod["description"] = candidates[0]["物料描述"]
                    prod["materialCode"] = str(candidates[0]["物料号"])
                    prod["series"] = candidates[0]["系列"]
                    prod["power"] = str(int(candidates[0]["功率(w)"]))
                    prod["lmEff"] = lumEff if lumEff else str(int(candidates[0]["光效(lm/w)"]))
                    prod["lumen"] = str(int(prod["power"]) * int(prod["lmEff"]))
                    prod["colorTemperature"] = str(int(candidates[0]["色温(k)"]))
                    prod["pricePosition"] = candidates[0]["定位"]
                    prod["price"] = str(int(candidates[0]["产品价格"]))
                    prod["size"] = candidates[0]["尺寸"]
                    prod["color"] = candidates[0]["颜色"]
                    prod["CRI"] = str(int(candidates[0]["显色指数(ra)"]))
                    prod["assemble"] = candidates[0]["安装方式"]
                    prod["count"] *= cnt
                    prod["category2"] = candidates[0]["二级分类名称"]
                    light_num += prod["count"]

                    # 默认捆绑类型
                    if "控制器" in candidates[0]["捆绑二级分类"]:
                        bundle_type = "CONTROLLER"
                    elif "电源" in candidates[0]["捆绑二级分类"]:
                        bundle_type = "POWER"
                    else:
                        bundle_type = None
                    
                    if params["controller_type"] == "POWER":
                        bundle_type = "POWER"
                    elif params["controller_type"] in ["NEMA", "CPS", "CPD"]:
                        bundle_type = "CONTROLLER"

                    # 增加对应的控制器
                    if bundle_type == "CONTROLLER":
                        controller_type = "CPS"
                        if "NEMA" in candidates[0]["物料描述"]:
                            controller_type = "NEMA"
                        elif lightArmType in ["单臂"]:
                            controller_type = "CPS"
                        elif lightArmType in ["平行臂", "高低臂"]:
                            controller_type = "CPD"
                        if params["controller_type"]:
                            controller_type = params["controller_type"]

                        cnt = prod["count"]
                        if controller_type == "CPD":
                            cnt = pole_num
                        
                        controller = self.select_controllers(prod_dataset, cnt, controller_type)
                        controllers.extend(controller)
                    # 增加对应的电源
                    elif bundle_type == "POWER":
                        power_candidates = prod_dataset.prod_df[(prod_dataset.prod_df["一级分类名称"] == "道路灯具") & (prod_dataset.prod_df["二级分类名称"] == "电源")]
                        cur_power = self.power.copy()
                        power_candidates = power_candidates.sort_values(by="功率(w)").to_dict(orient='records')
                        for i in range(len(power_candidates)):
                            if int(power_candidates[i]["功率(w)"]) >= int(candidates[0]["功率(w)"]):
                                cur_power["count"] = int(prod["count"] / cnt)
                                cur_power["materialCode"] = str(power_candidates[i]["物料号"])
                                cur_power["description"] = power_candidates[i]["物料描述"]
                                cur_power["series"] = power_candidates[i]["系列"]
                                cur_power["size"] = power_candidates[i]["尺寸"]
                                cur_power["price"] = str(int(power_candidates[i]["产品价格"]))
                                powers.append(cur_power)
                                break
                        if cur_power["materialCode"] is None:
                            cur_power["count"] = int(prod["count"] / cnt)
                            cur_power["materialCode"] = str(power_candidates[-1]["物料号"])
                            cur_power["description"] = power_candidates[-1]["物料描述"]
                            cur_power["series"] = power_candidates[-1]["系列"]
                            cur_power["size"] = power_candidates[-1]["尺寸"]
                            cur_power["price"] = str(int(power_candidates[-1]["产品价格"]))
                            powers.append(cur_power)

            elif prod["category2"] == "平台":
                platform_candidates = prod_dataset.prod_df[(prod_dataset.prod_df["二级分类名称"] == "平台")]
                if len(platform_candidates) > 0:
                    prod["description"] = platform_candidates.iloc[0]["物料描述"]
                    prod["materialCode"] = str(platform_candidates.iloc[0]["物料号"])
                    prod["price"] = str(int(platform_candidates.iloc[0]["产品价格"]))
                    prod["series"] = platform_candidates.iloc[0]["系列"]
        
        if controllers:
            if "CPD" in controllers[0]["description"]:
                new_controllers = []
                cpd_controller = controllers[0]
                cpd_controller["count"] = pole_num
                new_controllers.append(cpd_controller)
                planInfo["products"].extend(new_controllers)
            else:
                planInfo["products"].extend(controllers)
        if powers:
            planInfo["products"].extend(powers)
        
        planInfo["lightNum"] = light_num

        return planInfo

    def select_light(self, series, base_power, colorTemp, type="路灯"):
        """根据系列、功率、色温选择灯具"""

        if type == "路灯":
            candidates = prod_dataset.prod_df[(prod_dataset.prod_df["二级分类名称"] == "路灯") & (prod_dataset.prod_df["系列"] == series)]
            # 进一步筛选功率
            power_candidates = candidates[candidates["功率(w)"] == int(base_power)]
            if power_candidates.empty:
                # 定制品路线
                power_candidates = candidates[candidates["功率(w)"] == 0].copy()
                # 赋值colorTemp
                power_candidates["色温(k)"] = str(colorTemp)
                power_candidates["功率(w)"] = int(base_power)
            lights = power_candidates.sort_values(by="功率(w)").to_dict(orient='records')
            return lights
        else:
            candidates = prod_dataset.prod_df[(prod_dataset.prod_df["二级分类名称"] == "模组") & (prod_dataset.prod_df["系列"] == series)]
        
            # 进一步筛选功率
            power_candidates = candidates[candidates["功率(w)"] == int(base_power)]
            if power_candidates.empty:
                cur_power_ls = sorted(candidates["功率(w)"].unique().tolist())
                # 如果没有完全匹配的功率，向上取最接近的功率
                for p in cur_power_ls:
                    if p >= int(base_power):
                        power_candidates = candidates[candidates["功率(w)"] == p]
                        break
                if power_candidates.empty:
                    power_candidates = candidates[candidates["功率(w)"] == cur_power_ls[-1]]

            # 进一步筛选色温
            colorTemp_candidates = power_candidates[power_candidates["色温(k)"] == int(colorTemp)]
            if colorTemp_candidates.empty:
                colorTemp_candidates = power_candidates
            lights = colorTemp_candidates.sort_values(by="功率(w)").to_dict(orient='records')

            return lights
        
    def select_controllers(self, prod_dataset, cnt, controller_type):
        
        controllers = []
        controller_candidates = prod_dataset.prod_df[(prod_dataset.prod_df["一级分类名称"] == "道路灯具") & (prod_dataset.prod_df["二级分类名称"] == "控制器")]
        controller = self.controller.copy()
        for i in range(len(controller_candidates)):
            if controller_type in controller_candidates.iloc[i]["物料描述"]:
                controller["count"] = cnt
                controller["materialCode"] = str(controller_candidates.iloc[i]["物料号"])
                controller["description"] = controller_candidates.iloc[i]["物料描述"]
                controller["series"] = controller_candidates.iloc[i]["系列"]
                controller["size"] = controller_candidates.iloc[i]["尺寸"]
                controller["price"] = str(int(controller_candidates.iloc[i]["产品价格"]))
                controllers.append(controller)
                break

        return controllers
    
select_prod = SelectProd()