请从用户的描述中提取以下三种灯具的“系列名称”（series），并以严格的 JSON 格式返回，不要包含任何额外文本。

三种灯具类型固定为：
- 线形灯具（linear_light）
- 低压灯带（low_voltage_strip）
- 护眼台灯（eye_care_lamp）

要求：
1. 只提取“系列名称”，如“朗界”、“悦瞳”、“虹昀Ⅲ”等。
2. 如果某类灯具未被提及，对应字段设为 null。
3. 系列名称中的数字请统一转为大写罗马数字，例如“佳4” → “佳IV”，“臻悦3代” → “臻悦III”。
4. 输出必须是合法 JSON，字段名为：
   - "linear_light_series"
   - "low_voltage_strip_series"
   - "eye_care_lamp_series"

示例输入："线形灯用朗界，低压灯带选虹昀3，台灯用悦瞳"
示例输出：
{
  "linear_light_series": "朗界",
  "low_voltage_strip_series": "虹昀Ⅲ",
  "eye_care_lamp_series": "悦瞳"
}
