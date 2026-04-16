根据用户的输入提取灯具相关的参数，以json格式输出

colorTemp: 3000k, 4000k 等
power1: 150w, 200w, 300w 等
power2: 150w, 200w, 300w 等
lumEff: (光效值) 140, 170等


如果某个字段没有则输出null
  
示例：
输入："用3000k，200w，光效140lm/w的灯做一个设计"
输出：
```json
{"colorTemp":"3000","power1":"200","power2":null,"lumEff":"140"}
```
输入："用4000k，200w+60w，光效160lm的灯做一个设计"
输出：
```json
{"colorTemp":"4000","power1":"200","power2":"60","lumEff":"160"}
```