---
name: data-analysis
description: Use this skill when the user uploads Excel (.xlsx/.xlsm) files and wants to inspect sheets, summarize table data, answer questions from workbook content, or perform lightweight structured data analysis.
---

# Excel Data Analysis

本项目中，Excel 解析的稳定入口是后端工具 `parse_excel_file`，不要优先尝试写脚本、执行命令或访问历史 skill 中的 `/mnt/user-data` 路径。

## 优先规则

当用户提到已经上传 Excel 文件，或消息中出现 `/uploads/*.xlsx`、`/uploads/*.xlsm` 路径时：

1. 先调用 `parse_excel_file(file_path=...)` 读取文件结构和预览数据。
2. 如果用户没有指定文件路径，先调用 `list_uploaded_excel_files()` 查询当前会话可用的 Excel 文件。
3. 基于工具返回的 sheet 名、行列数、预览行和截断标记回答问题。
4. 如果结果显示 `truncated=true`，说明只读取了前若干行预览；需要更完整分析时，明确告诉用户当前工具只返回预览数据。

## 路径约定

- 上传后的 Excel 文件位于当前会话沙箱的 `/uploads/` 目录。
- 示例路径：`/uploads/sales.xlsx`、`/uploads/report.xlsm`。
- 不要使用 `/mnt/user-data/uploads/`、`/mnt/skills/public/` 这类路径，它们不是当前项目的文件上传路径。

## 推荐调用方式

```text
parse_excel_file(file_path="/uploads/data.xlsx", max_rows_per_sheet=50)
```

如果用户只说“分析我刚上传的表格”，但没有给出文件路径：

```text
list_uploaded_excel_files()
```

然后选择列表中的 Excel 文件再调用：

```text
parse_excel_file(file_path="/uploads/xxx.xlsx")
```

## 回答要求

- 先说明识别到的 workbook/sheet 信息。
- 对用户问题直接给出结论，不要只复述表格内容。
- 对不确定结论说明原因，例如只读取到预览数据或字段含义不明确。
- 如果用户需要统计、筛选、汇总，尽量基于已解析数据完成；若预览数据不足，提示用户需要扩展工具读取更多行。
