from copy import deepcopy
import json
import os
import shutil

import cv2
import numpy as np
from apps.req.road_agent_req import RoadAgentReq, Inputs
from apps.road_agent.road_agent import RoadAgent
from apps.vo.road_agent_vo import RoadAgentVo
from tqdm import tqdm


def vis_dify(response):
    response = response.dict()
    color_map = {
        "tree": (0, 255, 0),
        "concrete": (0, 255, 0),
        "guardrail": (0, 255, 0),
        "main_road": (128, 128, 128),
        "sub_road": (175, 175, 175),
        "bike_road": (255, 0, 255),
        "person_road": (0, 0, 255),
        "white_line": (255, 255, 255),
        "white_dashed_line": (255, 255, 255),
        "yellow_line": (0, 255, 255),
        "car": (255, 0, 0),
    }
    res_ls = []
    res = np.zeros((2000 + 1, 1000 + 1, 3), np.uint8)

    for room in response["roomInfo"]:
        # x1 = int(room["rectangle"]["x_min"] * 10)
        # y1 = int(room["rectangle"]["y_min"] * 10)
        # x2 = int(room["rectangle"]["x_max"] * 10)
        # y2 = int(room["rectangle"]["y_max"] * 10)

        # cv2.rectangle(res, (x1, y1), (x2, y2), (0, 0, 255), 1)
        if room.get("objects") is None:
            continue
        for object in room.get("objects"):
            for loc in object["locations"]:
                x1 = int((loc["x"] - loc["w"] / 2) * 10)
                y1 = int((loc["y"] - loc["h"] / 2) * 10)
                x2 = int((loc["x"] + loc["w"] / 2) * 10)
                y2 = int((loc["y"] + loc["h"] / 2) * 10)
                if loc.get("rotation"):
                    angle = loc["rotation"][-1]
                    if angle == 90 or angle == 270:
                        x1 = int((loc["x"] - loc["h"] / 2) * 10)
                        y1 = int((loc["y"] - loc["w"] / 2) * 10)
                        x2 = int((loc["x"] + loc["h"] / 2) * 10)
                        y2 = int((loc["y"] + loc["w"] / 2) * 10)
                        
                cv2.rectangle(res, (x1, y1), (x2, y2), color_map[object["type"]], -1)
                # cv2.putText(res, f"{object["type"]}: {loc["w"]}m", (x1 + 10, y1 + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)

    for plan in response["planList"]:
        plan_vis = deepcopy(res)
        for prod in plan.get("products", []):
            for loc in prod.get("location", []):
                if loc.get("w") is None or loc.get("h") is None:
                    continue
                x1 = int((loc["x"] - loc["w"] / 2) * 10)
                y1 = int((loc["y"] - loc["h"] / 2) * 10)
                x2 = int((loc["x"] + loc["w"] / 2) * 10)
                y2 = int((loc["y"] + loc["h"] / 2) * 10)

                if loc.get("rotation"):
                    angle = loc["rotation"][-1]
                    if angle == 90 or angle == 270:
                        x1 = int((loc["x"] - loc["h"] / 2) * 10)
                        y1 = int((loc["y"] - loc["w"] / 2) * 10)
                        x2 = int((loc["x"] + loc["h"] / 2) * 10)
                        y2 = int((loc["y"] + loc["w"] / 2) * 10)

                if prod["category2"] == "灯杆":
                    cv2.circle(plan_vis, (int(loc["x"] * 10), int(loc["y"] * 10)), 5, (255, 255, 255), -1)
                elif prod["category2"] in ["路灯", "控制器"]:
                    continue
                else:
                    cv2.rectangle(plan_vis, (x1, y1), (x2, y2), (255, 255, 255), -1)

        cv2.putText(plan_vis, f"light_gap: {round(plan["lightGap"], 1)}", (10, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)
        cv2.putText(plan_vis, f"light_height: {round(plan["lightPoleHeight"], 1)}", (10, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)
        cv2.putText(plan_vis, f"light_num: {plan["lightNum"]}", (10, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)

        res_ls.append(plan_vis)
    
    return res_ls

if __name__ == "__main__":

    level = ["快速路", "主干路", "次干路", "支路"]
    # level = ["次干路"]
    main_lane = {
        "快速路": [4, 6, 8, 10],
        "主干路": [4, 6, 8, 10],
        "次干路": [2, 4, 6],
        "支路": [1, 2]
    }

    sub_lane = {
        "快速路": [0],
        "主干路": [2, 4],
        "次干路": [0],
        "支路": [0]
    }

    bike_lane = {
        "快速路": [0],
        "主干路": [2],
        "次干路": [2],
        "支路": [0]
    }

    person_lane = {
        "快速路": [0],
        "主干路": [2],
        "次干路": [2],
        "支路": [2]
    }

    assembleMethod = {
        "快速路": ["双侧对称", "双侧交错", "中心对称", "单侧"],
        "主干路": ["双侧对称", "双侧交错", "中心对称", "单侧"],
        "次干路": ["双侧对称", "双侧交错", "中心对称", "单侧"],
        "支路": ["双侧交错", "单侧"]
    }

    lightArmType = {
        "双侧对称": ["单臂", "高低臂"],
        "双侧交错": ["平行臂", "高低臂", "单臂"],
        "中心对称": ["平行臂"],
        "单侧": ["单臂"]
    }

    mid_split_num = {
        "快速路": [0, 1],
        "主干路": [0, 1],
        "次干路": [0, 1],
        "支路": [0]
    }

    side_split_num = {
        "快速路": [2, 4],
        "主干路": [2, 4],
        "次干路": [2, 4],
        "支路": [0]
    }

    agent = RoadAgent()

    reqs = []
    for lev in level[:]:
        for main in main_lane[lev]:
            for sub in sub_lane[lev]:
                for bike in bike_lane[lev]:
                    for person in person_lane[lev]:
                        for mid_split in mid_split_num[lev]:
                            for side_split in side_split_num[lev]:
                                for method in assembleMethod[lev]:
                                    # if method != "双侧交错":
                                    #     continue
                                    for arm in lightArmType[method]:
                                        # if arm != "平行臂":
                                        #     continue
                                        inputs = Inputs(
                                            level=lev,
                                            length=10.0,
                                            lanes=[
                                                {"type": "机动车道", "count": main, "width": 3.75},
                                                {"type": "辅道", "count": sub, "width": 3.5},
                                                {"type": "非机动车道", "count": bike, "width": 3.5},
                                                {"type": "人行道", "count": person, "width": 2.5},
                                                {"type": "绿化带", "count": mid_split, "width": 1.0},
                                                {"type": "水泥墩", "count": side_split, "width": 2.0}
                                            ],
                                            assembleMethod=method,
                                            lightArmType=arm,
                                            lightPole=True,
                                            planType="新建道路",
                                            lights=[],
                                            lightNum=100,
                                            subLightFlag=True if main >= 6 and sub >= 4 else False,
                                            subLightArmType="单臂",
                                            tag="",
                                            text=""
                                        )
                                        cur_req = RoadAgentReq(inputs=inputs, user="test_user")
                                        param_res = agent.param_run(cur_req)
                                        cur_req.inputs.lightPoleHeight = param_res.data.lightPoleHeight
                                        cur_req.inputs.mainLightHeight = param_res.data.mainLightHeight
                                        cur_req.inputs.subLightHeight = param_res.data.subLightHeight
                                        cur_req.inputs.mainLightArmLength = param_res.data.mainLightArmLength
                                        cur_req.inputs.subLightArmLength = param_res.data.subLightArmLength
                                        cur_req.inputs.mainLightArmAngle = param_res.data.mainLightArmAngle
                                        cur_req.inputs.subLightArmAngle = param_res.data.subLightArmAngle
                                        cur_req.inputs.mainLightAngle = 0.0
                                        cur_req.inputs.subLightAngle = 0.0
                                        cur_req.inputs.lightGap = param_res.data.lightGap
                                        cur_req.inputs.lightMaintenanceFactor = 0.7
                                        cur_req.inputs.splitType = "侧分隔带"
                                        cur_req.inputs.lightRoadGap = param_res.data.lightRoadGap
                                        reqs.append(cur_req)

    save_dir = "test_data"
    if os.path.exists(save_dir):
        shutil.rmtree(save_dir)
    os.makedirs(save_dir, exist_ok=True)

    xlsx_path = os.path.join(save_dir, "test_data.xlsx")
    if os.path.exists(xlsx_path):
        os.remove(xlsx_path)
    import pandas as pd
    df = pd.DataFrame(columns=["planName", "level", "assembleMethod", "lightArmType",
                             "main_lane", "sub_lane", "bike_lane", "person_lane", "split_lane",
                             "lightGap", "lightPoleHeight", "lightNum", "mainLightHeight", "subLightHeight",
                             "mainLightArmLength", "subLightArmLength", "mainLightArmAngle", "subLightArmAngle",
                             "mainLightAngle", "subLightAngle"])
    
    for req in tqdm(reqs[:]):
        
        response = agent.run(req)
        if response.code == 400:
            print(response.msg)
            continue
        res = vis_dify(response)
        
        planName = f"{req.inputs.level}_{req.inputs.assembleMethod}_{req.inputs.lightArmType}_主{req.inputs.lanes[0].count}_辅{req.inputs.lanes[1].count}_非{req.inputs.lanes[2].count}_人{req.inputs.lanes[3].count}_绿{req.inputs.lanes[4].count + req.inputs.lanes[5].count}"
        cv2.imwrite(os.path.join(save_dir, f"{planName}.jpg"), res[0])
        with open(os.path.join(save_dir, f"{planName}.json"), "w") as f:
            json.dump(response.dict(), f, ensure_ascii=False, indent=4)

        # 写入 xlsx
        new_row = pd.DataFrame([{
            "planName": planName,
            "level": req.inputs.level,
            "assembleMethod": req.inputs.assembleMethod,
            "lightArmType": req.inputs.lightArmType,
            "main_lane": req.inputs.lanes[0].count,
            "sub_lane": req.inputs.lanes[1].count,
            "bike_lane": req.inputs.lanes[2].count,
            "person_lane": req.inputs.lanes[3].count,
            "split_lane": req.inputs.lanes[4].count + req.inputs.lanes[5].count,
            "lightGap": response.planList[0]["lightGap"],
            "lightPoleHeight": response.planList[0]["lightPoleHeight"],
            "lightNum": response.planList[0]["lightNum"],
            "mainLightHeight": response.planList[0]["mainLightHeight"],
            "subLightHeight": response.planList[0]["subLightHeight"],
            "mainLightArmLength": response.planList[0]["mainLightArmLength"],
            "subLightArmLength": response.planList[0]["subLightArmLength"],
            "mainLightArmAngle": response.planList[0]["mainLightArmAngle"],
            "subLightArmAngle": response.planList[0]["subLightArmAngle"],
            "mainLightAngle": req.inputs.mainLightAngle,
            "subLightAngle": req.inputs.subLightAngle
            }])
        df = pd.concat([df, new_row], ignore_index=True)
        
    df.to_excel(xlsx_path, index=False)