import pandas as pd
import os

# 最新的道路行业产品库文件路径
source_file = "/Users/opple/Downloads/行业产品参数表-工作表1.csv"

# 要更新的道路行业产品库文件路径
target_file = "/Users/opple/Desktop/iso/isolution_ai/data/道路行业产品库.csv"

updated_info = "/Users/opple/Desktop/iso/isolution_ai/data/update_info.csv"
# 根据行业更新：
# 有2种更新模式：1.添加。 2.更新
# 输入参数，如果 source 的 【行业】 那一列 包含该值，如果要更新则覆盖 则根据material code，覆盖 target 文件中的那一行
# 如果是添加，则添加该行到 target 文件中，如果 material code 已经存在，则不添加

# 系列 ： 1、灯盘，色温：4000k,功率：不限，尺寸：600*600；600*1200；系列：佳IV、众IV、昱
# 系列 ： 1、灯盘，色温：1800K~12000K,功率：不限，尺寸：600*600；600*1200；系列：天境


def update_product_database(source_path, target_path, updated_info_path,
                            industry, mode='add', category_filter=None,
                            series_filter=None, size_filter=None):
    """
    根据指定行业和模式更新目标产品库文件。

    Args:
        source_path (str): 源文件路径 (最新的产品库).
        target_path (str): 目标文件路径 (要更新的产品库).
        updated_info_path (str): 用于保存更新记录的文件路径.
        industry (str): 要筛选的行业名称.
        mode (str): 更新模式, 'add' (添加) 或 'update' (更新).
        category_filter (list, optional): 要筛选的一级分类列表. 默认为 None.
        series_filter (list, optional): 要筛选的产品系列列表. 默认为 None.
        size_filter (list, optional): 要筛选的尺寸列表(长*宽). 默认为 None.

    Returns:
        list: 一个包含所有被添加或更新的产品的物料号的列表。
              如果操作失败或没有产品更新，则返回空列表。
    """
    if series_filter is None:
        series_filter = []
    if category_filter is None:
        category_filter = []
    if size_filter is None:
        size_filter = []
    try:
        # 定义列名映射关系
        column_mapping = {
            '物料代码': '物料号', '一级分类': '一级分类名称', '二级分类': '二级分类名称',
            '物料描述': '物料描述', '产品系列': '系列', '行业': '行业',
            '功率': '功率(w)', '色温': '色温(k)', '尺寸': '尺寸',
            '光束角': '光束角', '光通量': '光通量(lm)', '颜色': '颜色',
            '行业普遍水平（光效）': '行业普遍水平(光效)', '显色指数': '显色指数(ra)',
            '开孔': '开孔', '安装方式': '安装方式', '防水等级': '防水等级',
            '光效': '光效(lm/w)', '产品定位': '定位', '价格': '产品价格',
            '标准灯杆': '标准灯杆', '灯杆灯臂类型': '灯杆灯臂类型',
            '捆绑二级分类': '捆绑二级分类', 'status': 'status'
        }
        source_material_col = '物料代码'
        target_material_col = '物料号'
        updated_codes = []

        # 读取源文件和目标文件
        source_df = pd.read_csv(source_path)
        target_df = pd.read_csv(target_path)
        print(f"成功读取源文件: {source_path}")
        print(f"成功读取目标文件: {target_path}")

        # 检查关键列是否存在
        industry_col_name = '行业'
        if industry_col_name not in source_df.columns:
            print(f"错误: 源文件中未找到 '{industry_col_name}' 列。")
            return []
        if source_material_col not in source_df.columns:
            print(f"错误: 源文件中未找到 '{source_material_col}' 列。")
            return []
        if target_material_col not in target_df.columns:
            print(f"错误: 目标文件中未找到 '{target_material_col}' 列。")
            return []

        # 1. 筛选出特定行业的产品
        filtered_df = source_df[
            source_df[industry_col_name].str.contains(industry, na=False)
        ].copy()

        # 应用一级分类筛选
        if category_filter:
            filtered_df = filtered_df[
                filtered_df['一级分类'].isin(category_filter)
            ]

        # 应用系列筛选
        if series_filter:
            filtered_df = filtered_df[
                filtered_df['产品系列'].isin(series_filter)
            ]

        # 应用尺寸筛选 (忽略高度)
        if size_filter:
            # 规范化筛选条件中的尺寸，只取前两部分
            normalized_size_filters = {
                '*'.join(s.split('*')[:2]) for s in size_filter
            }
            # 规范化DataFrame中的尺寸列，并进行匹配
            filtered_df = filtered_df[
                filtered_df['尺寸'].str.split('*').str[:2].str.join('*').isin(
                    normalized_size_filters
                )
            ]

        source_industry_df = filtered_df
        print(f"在源文件中找到 {len(source_industry_df)} 个 "
              f"与筛选条件相关的产品。")

        if source_industry_df.empty:
            print("没有找到需要处理的产品，程序退出。")
            return []

        # 2. 根据映射关系，筛选并重命名源df的列
        source_cols = list(column_mapping.keys())
        # 确保所有需要的源列都存在
        missing_cols = [c for c in source_cols if c not in source_df.columns]
        if missing_cols:
            print(f"错误: 源文件中缺少以下列: {missing_cols}")
            return []

        processed_source_df = source_industry_df[source_cols].rename(
            columns=column_mapping
        )

        if mode == 'update':
            print("执行 'update' 模式...")
            # 使用物料号作为索引方便更新
            target_df.set_index(target_material_col, inplace=True)
            processed_source_df.set_index(target_material_col, inplace=True)

            # 更新已存在的产品信息
            target_df.update(processed_source_df)
            updated_codes = processed_source_df.index.tolist()

            # 准备日志信息
            log_df = processed_source_df.reset_index()

            # 重置索引
            target_df.reset_index(inplace=True)
            print(f"更新完成。共处理 {len(processed_source_df)} 条记录。")

        elif mode == 'add':
            print("执行 'add' 模式...")
            # 找出目标文件中已存在的物料号
            existing_codes = set(target_df[target_material_col])

            # 筛选出源文件中不存在于目标文件的新产品
            new_products_df = processed_source_df[
                ~processed_source_df[target_material_col].isin(existing_codes)
            ]

            if not new_products_df.empty:
                # 将新产品添加到目标 DataFrame
                updated_df = pd.concat(
                    [target_df, new_products_df], ignore_index=True
                )
                print(f"添加了 {len(new_products_df)} 个新产品。")
                target_df = updated_df
                updated_codes = new_products_df[target_material_col].tolist()
                # 准备日志信息
                log_df = new_products_df.copy()
            else:
                print("没有需要添加的新产品。")
                log_df = pd.DataFrame()

        else:
            print(f"错误: 无效的模式 '{mode}'。请选择 'add' 或 'update'。")
            return []

        # 3. 保存更新记录到 updated_info.csv
        if not log_df.empty:
            log_df['mode'] = mode
            log_df['update_time'] = pd.to_datetime('now').strftime(
                '%Y-%m-%d %H:%M:%S'
            )
            try:
                # 如果文件存在，则追加；否则，创建新文件
                header = not os.path.exists(updated_info_path)
                log_df.to_csv(
                    updated_info_path, mode='a', header=header, index=False
                )
                print(f"已将 {len(log_df)} 条更新记录保存到 {updated_info_path}")
            except Exception as e:
                print(f"错误: 保存更新记录失败: {e}")

        # 保存更新后的目标文件
        target_df.to_csv(target_path, index=False)
        print(f"成功将更新后的数据保存到: {target_path}")
        return updated_codes

    except FileNotFoundError as e:
        print(f"文件未找到错误: {e}")
        return []
    except pd.errors.EmptyDataError as e:
        print(f"文件为空或格式错误: {e}")
        return []
    except KeyError as e:
        print(f"文件中缺少关键列: {e}")
        return []
    except Exception as e:
        print(f"发生未知错误: {e}")
        return []


if __name__ == '__main__':
    # --- 使用示例 ---
    # 1. 添加模式:
    # 将 source_file 中属于 "道路" 行业且 "material code"
    # 不存在于 target_file 的产品添加到 target_file
    print("--- 开始执行添加模式 ---")
    # updated_roads = update_product_database(
    #     source_file,
    #     target_file,
    #     updated_info,
    #     industry="道路",
    #     mode='add'
    # )
    # print(f"道路行业新增产品物料号: {updated_roads}")
    print("\n" + "="*50 + "\n")

    print("---  ---")
    added_rail_codes = update_product_database(
        source_file, target_file,
        updated_info,
        industry="办公",
        mode='add',
        category_filter=['射灯'],
        series_filter=['皓II'],
        # size_filter=['600*600', '600*1200']
    )
    print(f"轨交行业新增产品物料号: {added_rail_codes}")
    assert len(added_rail_codes) == len(set(added_rail_codes))
