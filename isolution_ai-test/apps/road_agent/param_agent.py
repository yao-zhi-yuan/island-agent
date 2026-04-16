from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import MessagesState, StateGraph
import numpy as np

from apps.road_agent.llm import req_llm
from apps.road_agent.utils import load_prompt
from apps.road_agent.prod_datasets import prod_dataset


class MessagesState(MessagesState):
    user_id: str
    params: dict = {}

class ParamAgent:
    def __init__(self):
        self.sys_prompt = load_prompt("prompts/param_sys_prompt.md")
        self.agent_name = "param_agent"
        self.agent = self.build_param_agent()
        self.pole_series_ls = prod_dataset.pole_series_ls
        self.light_series_ls = prod_dataset.light_series_ls
        self.module_series_ls = prod_dataset.module_series_ls
        self.number_dict = {"I": ["1", "一", "I", "i"], "II": ["2", "二", "II", "ii"], "III": ["3", "三", "III", "iii"], "IV": ["4", "四", "IV", "iv"], "V": ["5", "五", "V", "v"], "VI": ["6", "六", "VI", "vi"], "VII": ["7", "七", "VII", "vii"], "VIII": ["8", "八", "VIII", "viii"], "IX": ["9", "九", "IX", "ix"], "X": ["10", "十", "X", "x"]}

    def parse_params(self, state):

        sys_msg = SystemMessage(content=self.sys_prompt)
        user_msg = HumanMessage(content=state["messages"][0].content)
        messages = [sys_msg, user_msg]
        params = req_llm(messages)
        
        return {"params": params}

    def build_param_agent(self):
        weather_graph_builder = StateGraph(MessagesState)
        weather_graph_builder.add_node("parse_params", self.parse_params)
        weather_graph_builder.set_entry_point("parse_params")
        weather_graph_builder.set_finish_point("parse_params")
        graph = weather_graph_builder.compile(name=self.agent_name)

        return graph
    
    def run(self, text, user_id):

        res = {
            "series": None, 
            "colorTemp": None, 
            "power1": None, 
            "power2": None, 
            "pole_series": None, 
            "light_series": None, 
            "module_series": None,
            "lumEff": None,
            "controller_type": None
            }
        
        if text == "":
            return res
        
        messages = HumanMessage(content=text)
        messages = [messages]

        config = {
            "configurable": {
                "thread_id": user_id,
            }
        }
        state = MessagesState(user_id=user_id, messages=messages, config=config)
        result = self.agent.invoke(state)

        pole_series, light_series, module_series = self.extract_series(text)
        res["power1"] = result["params"].get("power1", None)
        res["power2"] = result["params"].get("power2", None)
        if res["power1"] and res["power2"]:
            if int(res["power1"]) < int(res["power2"]):
                res["power1"], res["power2"] = res["power2"], res["power1"]
        res["colorTemp"] = result["params"].get("colorTemp", None)
        res["lumEff"] = result["params"].get("lumEff", None)
        res["pole_series"] = pole_series
        res["light_series"] = light_series
        res["module_series"] = module_series

        text = text.lower()
        if "nema" in text:
            res["controller_type"] = "NEMA"
        elif "cps" in text or "单路控制器" in text:
            res["controller_type"] = "CPS"
        elif "cpd" in text or "双路控制器" in text:
            res["controller_type"] = "CPD"
        elif "物联网电源" in text:
            res["controller_type"] = "POWER"
        
        return res
    
    def extract_series(self, text):
        """从文本中提取系列信息"""
        
        pole_series, light_series, module_series = None, None, None
        for ps in self.pole_series_ls:
            for n in self.number_dict:
                if ps.endswith(n):
                    for num in self.number_dict[n]:
                        cur_ps = ps.replace(n, num)
                        if cur_ps in text:
                            pole_series = ps
                            break
                else:
                    if ps in text:
                        pole_series = ps
                        break
                    
        for ls in self.light_series_ls:
            for n in self.number_dict:
                if ls.endswith(n):
                    for num in self.number_dict[n]:
                        cur_ls = ls.replace(n, num)
                        if cur_ls in text:
                            light_series = ls
                            break
                else:
                    if ls in text:
                        light_series = ls
                        break

        for ms in self.module_series_ls:
            for n in self.number_dict:
                if ms.endswith(n):
                    for num in self.number_dict[n]:
                        cur_ms = ms.replace(n, num)
                        if cur_ms in text:
                            module_series = ms
                            break
                else:
                    if ms in text:
                        module_series = ms
                        break
        
        return pole_series, light_series, module_series
    
    def judge_params(self, params, arm_type):
        """判断参数的合理性"""

        # 1. 灯杆系列是否支持所选灯臂类型
        if params["pole_series"]:
            pole_ls = prod_dataset.prod_df[(prod_dataset.prod_df["二级分类名称"] == "灯杆") & (prod_dataset.prod_df["系列"] == params["pole_series"]) & (prod_dataset.prod_df["灯杆灯臂类型"].str.contains(arm_type))]

            if len(pole_ls) == 0:
                return False, f"所选灯杆系列{params['pole_series']}不支持{arm_type}，请重新选择"
            
        # 2. 灯杆系列是否支持路灯、模组系列，标准灯杆匹配路灯，非标准灯杆匹配模组
        if params["pole_series"] and (params["light_series"] or params["module_series"]):
            pole_df = prod_dataset.prod_df[(prod_dataset.prod_df["二级分类名称"] == "灯杆") & (prod_dataset.prod_df["系列"] == params["pole_series"])]
            if len(pole_df) > 0:
                pole_type = pole_df.iloc[0]["标准灯杆"]
                if pole_type == "1" and params["module_series"]:
                    return False, f"所选灯杆系列{params['pole_series']}为标准灯杆，不支持模组系列{params['module_series']}，请重新选择"
                elif pole_type == "0" and params["light_series"]:
                    return False, f"所选灯杆系列{params['pole_series']}为非标准灯杆，不支持路灯系列{params['light_series']}，请重新选择"
                
        # 3. 路灯系列，色温组合是否存在
        if params["light_series"] and (params["power1"] or params["colorTemp"]):
            light_ls = prod_dataset.prod_df[(prod_dataset.prod_df["二级分类名称"] == "路灯") & (prod_dataset.prod_df["系列"] == params["light_series"])]
            if params["colorTemp"]:
                light_ls = light_ls[light_ls["色温(k)"] == params["colorTemp"]]
            if len(light_ls) == 0:
                colorTemp_options = sorted(list(np.array(prod_dataset.prod_df[(prod_dataset.prod_df["二级分类名称"] == "路灯") & (prod_dataset.prod_df["系列"] == params["light_series"])]["色温(k)"].unique().tolist(), dtype=int)))

                return False, f"所选路灯系列{params['light_series']}仅支持色温{colorTemp_options}K组合，请重新选择"
            
        # 4. 模组系列，色温组合是否存在
        if params["module_series"] and (params["power1"] or params["colorTemp"]):
            module_ls = prod_dataset.prod_df[(prod_dataset.prod_df["二级分类名称"] == "模组") & (prod_dataset.prod_df["系列"] == params["module_series"])]
            if params["power1"]:
                module_ls = module_ls[module_ls["功率(w)"] == int(params["power1"])]
            if params["colorTemp"]:
                module_ls = module_ls[module_ls["色温(k)"] == params["colorTemp"]]
            if len(module_ls) == 0:
                colorTemp_options = sorted(list(np.array(prod_dataset.prod_df[(prod_dataset.prod_df["二级分类名称"] == "模组") & (prod_dataset.prod_df["系列"] == params["module_series"])]["色温(k)"].unique().tolist(), dtype=int)))

                return False, f"所选模组系列{params['module_series']}仅支持色温{colorTemp_options}K组合，请重新选择"
            
        return True, "ok"