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
    agent = RoadAgent()
    test_ls = [
        "快速路 双侧对称 单臂 4 0 0 0 3 27 9 742 9 6 2.25 1 10 10",
        "快速路 双侧交错 单臂 4 0 0 0 3 36 12 558 12 9 3 1 10 10",
        "快速路 双侧对称 单臂 6 0 0 0 3 36 12 558 12 9 3 1 15 15",
        "快速路 双侧交错 单臂 6 0 0 0 3 36 12 558 12 9 3 1 15 15",
        "快速路 双侧对称 单臂 8 0 0 0 3 36 12 558 12 9 3 1 15 15",
        "快速路 中心对称 平行臂 8 0 0 0 3 36 12 558 12 9 3 1 15 15",
        "快速路 双侧对称 单臂 10 0 0 0 3 39 13 514 13 10 3.25 1 15 15",
        "快速路 中心对称 平行臂 10 0 0 0 3 39 13 514 13 10 3.25 1 15 15",
        "主干路 双侧对称 高低臂 4 2 2 2 3 27 9 1484 9 6 2.25 1 10 10",
        "主干路 双侧交错 单臂 4 2 2 2 3 36 12 558 12 9 3 1 10 10",
        "主干路 双侧对称 高低臂 6 2 2 2 3 36 12 1116 12 9 3 1 15 15",
        "主干路 中心对称 平行臂 6 2 2 2 3 36 12 558 12 9 3 1 15 15",
        "主干路 双侧对称 高低臂 10 2 2 2 3 39 13 1028 13 10 3.25 1 15 15",
        "主干路 中心对称 平行臂 10 2 2 2 3 39 13 514 13 10 3.25 1 15 15",
        "次干路 双侧对称 单臂 2 0 2 2 3 21 6 954 6 3 1.5 1 5 5",
        "次干路 双侧交错 平行臂 2 0 2 2 3 21 6 1908 6 3 1.5 1 5 5",
        "次干路 双侧对称 单臂 4 0 2 2 3 31.5 9 636 9 6 2.25 1 10 10",
        "次干路 双侧交错 单臂 4 0 2 2 3 42 12 478 12 9 3 1 10 10",
        "次干路 中心对称 平行臂 6 0 2 2 3 42 12 478 12 9 3 1 15 15",
        "支路 双侧交错 单臂 1 0 0 2 3 21 6 954 6 3 1.5 1 5 5",
        "支路 单侧 单臂 1 0 0 2 3 21 6 477 6 3 1.5 1 5 5",
        "支路 双侧交错 单臂 2 0 0 2 3 21 6 954 6 3 1.5 1 5 5",
        "支路 单侧 单臂 2 0 0 2 3 31.5 9 318 9 6 2.25 1 5 5",
    ]
    reqs = []
    for t in test_ls:
        lev, method, arm, main, sub, bike, person, split, lightGap, lightPoleHeight, lightNum, mainLightHeight, subLightHeight, mainLightArmLength, subLightArmLength, mainLightArmAngle, subLightArmAngle = t.split(" ")
        inputs = Inputs(
            level=lev,
            length=10.0,
            lanes=[
                {"type": "机动车道", "count": int(main), "width": 3.75},
                {"type": "辅道", "count": int(sub), "width": 3.5},
                {"type": "非机动车道", "count": int(bike), "width": 3.5},
                {"type": "人行道", "count": int(person), "width": 2.5},
                {"type": "绿化带", "count": int(split), "width": 1.0}
            ],
            assembleMethod=method,
            lightArmType=arm,
            lightPole=True,
            planType="新建道路",
            lights=[],
            lightNum=100,
            subLightFlag=True if int(main) >= 6 and int(sub) >= 4 else False,
            subLightArmType="单臂",
            tag="",
            text="晨曦",
            lightGap=float(lightGap),
            lightPoleHeight=float(lightPoleHeight),
            lightRoadGap=0.5,
            mainLightHeight=float(mainLightHeight),
            subLightHeight=float(subLightHeight),
            mainLightArmLength=float(mainLightArmLength),
            subLightArmLength=float(subLightArmLength),
            mainLightArmAngle=float(mainLightArmAngle),
            subLightArmAngle=float(subLightArmAngle)
        )
        cur_req = RoadAgentReq(inputs=inputs, user="test_user")
        
        reqs.append(cur_req)

    save_dir = "test_data"
    if os.path.exists(save_dir):
        shutil.rmtree(save_dir)
    os.makedirs(save_dir, exist_ok=True)

    xlsx_path = os.path.join(save_dir, "test_data.xlsx")
    if os.path.exists(xlsx_path):
        os.remove(xlsx_path)
    import pandas as pd
    df = pd.DataFrame(columns=["level", "assembleMethod", "lightArmType",
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
        
        cv2.imwrite(os.path.join(save_dir, f"{req.inputs.level}_{req.inputs.assembleMethod}_{req.inputs.lightArmType}_主{req.inputs.lanes[0].count}_辅{req.inputs.lanes[1].count}_非{req.inputs.lanes[2].count}_人{req.inputs.lanes[3].count}_绿{req.inputs.lanes[4].count}.jpg"), res[0])
        with open(os.path.join(save_dir, f"{req.inputs.level}_{req.inputs.assembleMethod}_{req.inputs.lightArmType}_主{req.inputs.lanes[0].count}_辅{req.inputs.lanes[1].count}_非{req.inputs.lanes[2].count}_人{req.inputs.lanes[3].count}_绿{req.inputs.lanes[4].count}.json"), "w") as f:
            json.dump(response.dict(), f, ensure_ascii=False, indent=4)

        # 写入 xlsx
        new_row = pd.DataFrame([{
            "level": req.inputs.level,
            "assembleMethod": req.inputs.assembleMethod,
            "lightArmType": req.inputs.lightArmType,
            "main_lane": req.inputs.lanes[0].count,
            "sub_lane": req.inputs.lanes[1].count,
            "bike_lane": req.inputs.lanes[2].count,
            "person_lane": req.inputs.lanes[3].count,
            "split_lane": req.inputs.lanes[4].count,
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