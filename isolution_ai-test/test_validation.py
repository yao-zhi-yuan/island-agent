"""测试 metro_agent_req 的条件验证"""
from apps.req.metro_agent_req import Inputs, MetroAgentReq

def test_inner_pass_width_validation():
    print("=" * 60)
    print("测试条件验证：innerPassWidth 根据 outerPassWidth_1 的不同要求")
    print("=" * 60)
    
    # 测试1: outerPassWidth_1 > 0, innerPassWidth > 14 (应该通过)
    print("\n测试1: outerPassWidth_1=3, innerPassWidth=15 (应该通过) ✅")
    try:
        inputs1 = Inputs(
            roomType="stationHall",
            roomWidth=20,
            innerPassWidth=15,
            outerPassWidth_1=3
        )
        print(f"✅ 验证通过: {inputs1.innerPassWidth}米")
    except ValueError as e:
        print(f"❌ 验证失败: {e}")
    
    # 测试2: outerPassWidth_1 > 0, innerPassWidth <= 14 (应该失败)
    print("\n测试2: outerPassWidth_1=3, innerPassWidth=14 (应该失败) ❌")
    try:
        inputs2 = Inputs(
            roomType="stationHall",
            roomWidth=20,
            innerPassWidth=14,
            outerPassWidth_1=3
        )
        print(f"✅ 验证通过: {inputs2.innerPassWidth}米")
    except ValueError as e:
        print(f"❌ 验证失败（符合预期）✅: {e}")
    
    # 测试3: outerPassWidth_1 = 0, innerPassWidth > 9 (应该通过)
    print("\n测试3: outerPassWidth_1=0, innerPassWidth=10 (应该通过) ✅")
    try:
        inputs3 = Inputs(
            roomType="stationHall",
            roomWidth=20,
            innerPassWidth=10,
            outerPassWidth_1=0
        )
        print(f"✅ 验证通过: {inputs3.innerPassWidth}米")
    except ValueError as e:
        print(f"❌ 验证失败: {e}")
    
    # 测试4: outerPassWidth_1 = 0, innerPassWidth <= 9 (应该失败)
    print("\n测试4: outerPassWidth_1=0, innerPassWidth=9 (应该失败) ❌")
    try:
        inputs4 = Inputs(
            roomType="stationHall",
            roomWidth=20,
            innerPassWidth=9,
            outerPassWidth_1=0
        )
        print(f"✅ 验证通过: {inputs4.innerPassWidth}米")
    except ValueError as e:
        print(f"❌ 验证失败（符合预期）✅: {e}")
    
    # 测试5: 边界情况 - outerPassWidth_1=0, innerPassWidth=9.1 (应该通过)
    print("\n测试5: outerPassWidth_1=0, innerPassWidth=9.1 (边界测试，应该通过) ✅")
    try:
        inputs5 = Inputs(
            roomType="stationHall",
            roomWidth=20,
            innerPassWidth=9.1,
            outerPassWidth_1=0
        )
        print(f"✅ 验证通过: {inputs5.innerPassWidth}米")
    except ValueError as e:
        print(f"❌ 验证失败: {e}")

if __name__ == "__main__":
    test_inner_pass_width_validation()
