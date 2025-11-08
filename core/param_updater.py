import pandas as pd
import os
import json
import core.data_reader as reader
from openpyxl import load_workbook
from openpyxl.styles import Alignment
from core.config import PARAM_FILE, TARGET_PATH, MAPPINGS_FILE, VARIENT_DATA_FILE, VARIENT_MAPPINGS_FILE
from core.config import CURRENT_PARAM_NAMES as PARAM_NAMES
from openpyxl.utils import get_column_letter
    
def generate_mappings_from_sheets(sheets, allowed_sheets=None):
    """
    通用的映射生成函数
    
    参数:
    sheets: 字典，工作表名 -> DataFrame
    allowed_sheets: 允许处理的工作表列表，None表示处理所有工作表
    
    返回:
    映射字典
    """
    mappings = {}
    
    # 确定要处理的工作表
    sheets_to_process = sheets.keys() if allowed_sheets is None else allowed_sheets
    
    for param_name in sheets_to_process:
        if param_name not in sheets:
            print(f"警告: {param_name} 工作表不存在")
            continue
            
        df = sheets[param_name]
        
        # 检查是否有足够的列
        if len(df.columns) < 2:
            print(f"警告: {param_name} 表没有足够的列")
            continue
        
        # 检查是否包含所需的列
        if "ExcelParam" not in df.columns or "ScenarioParam" not in df.columns:
            print(f"警告: {param_name} 表不包含 'ExcelParam' 或 'ScenarioParam' 列")
            continue
        
        # 构建映射
        param_mapping = {}
        for _, row in df.iterrows():
            excel_param = row["ExcelParam"]
            scenario_param = row["ScenarioParam"]
            
            if pd.notna(excel_param) and pd.notna(scenario_param):
                param_mapping[str(excel_param)] = str(scenario_param)
        
        mappings[param_name] = param_mapping
        print(f"已处理 {param_name} 表，生成 {len(param_mapping)} 个映射")
    
    return mappings


def save_mappings_to_file(mappings, file_path, variable_name="PARAM_MAPPINGS"):
    """
    通用的映射保存函数
    
    参数:
    mappings: 映射字典
    file_path: 保存路径
    variable_name: 变量名
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("# 自动生成的参数映射\n")
            f.write("# 请不要手动编辑此文件\n\n")
            f.write(f"{variable_name} = ")
            f.write(repr(mappings))
        print(f"映射已保存到 Python 模块: {file_path}")
        return True
    except Exception as e:
        print(f"保存映射文件失败: {e}")
        return False 


def generate_base_param_mappings():
    """生成基础参数映射（param_data.xlsx）"""
    try:
        param_sheets = pd.read_excel(PARAM_FILE,sheet_name=None)
    except Exception as e:
        print(f"读取基础参数文件失败: {e}")
        return {}
    
    # 使用通用函数生成映射
    mappings = generate_mappings_from_sheets(param_sheets)
    
    # 保存映射
    save_mappings_to_file(mappings, MAPPINGS_FILE, "PARAM_MAPPINGS")
    
    return mappings

def generate_varient_param_mappings():
    """生成差分参数映射（varient_data.xlsx）"""
    if not os.path.exists(VARIENT_DATA_FILE):
        print(f"差分参数文件不存在: {VARIENT_DATA_FILE}")
        return {}, []
    
    try:
        # 读取所有工作表（角色名作为工作表名）
        varient_sheets = pd.read_excel(VARIENT_DATA_FILE, sheet_name=None)
    except Exception as e:
        print(f"读取差分参数文件失败: {e}")
        return {}, []
    
    # 使用通用函数生成映射（处理所有工作表）
    mappings = generate_mappings_from_sheets(varient_sheets)
    
    # 提取所有差分参数名（用于参数表更新）
    all_varient_params = set()
    for character_name, mapping in mappings.items():
        all_varient_params.update(mapping.keys())
    
    # 保存差分映射到单独文件
    save_mappings_to_file(mappings, VARIENT_MAPPINGS_FILE, "VARIENT_MAPPINGS")
    
    return mappings, sorted(list(all_varient_params))

def collect_validation_data():
    """收集所有验证数据（基础参数 + 差分参数）"""
    validation_data = {}
    
    # 1. 收集基础参数
    try:
        base_sheets = pd.read_excel(PARAM_FILE, sheet_name=None)
    except Exception as e:
        print(f"读取基础参数文件失败: {e}")
        return {}
    
    for param_name in PARAM_NAMES:
        if param_name in base_sheets:
            df = base_sheets[param_name]
            params = reader.read_column_from_dataframe(df, "ExcelParam")
            if params:
                validation_data[param_name] = params
    
    # 2. 收集差分参数
    varient_mappings, varient_params = generate_varient_param_mappings()
    if varient_params:
        # 将差分参数合并到Varient列
        if "Varient" in validation_data:
            # 合并去重
            existing_varients = set(validation_data["Varient"])
            combined_varients = existing_varients.union(set(varient_params))
            validation_data["Varient"] = sorted(list(combined_varients))
        else:
            validation_data["Varient"] = varient_params
    
    return validation_data


def validation_update():
    """更新表格的数据验证参数并创建/更新命名区域"""
    # 使用新的数据收集函数获取所有验证数据（基础参数 + 差分参数）
    validation_data = collect_validation_data()
    
    if not validation_data:
        print("错误: 没有收集到验证数据")
        return False
    
    # 确保目标路径存在
    if not os.path.exists(TARGET_PATH):
        print(f"错误: 目标路径不存在: {TARGET_PATH}")
        return False
    
    # 处理每个Excel文件
    files = os.listdir(TARGET_PATH)
    excel_files = [f for f in files if f.endswith(".xlsx") and not f.startswith("~")]
    
    if not excel_files:
        print(f"警告: 在 {TARGET_PATH} 中没有找到Excel文件")
        return True
    
    success_count = 0
    for file in excel_files:
        file_path = os.path.join(TARGET_PATH, file)
        
        try:
            # 加载工作簿
            wb = load_workbook(file_path)
            
            # 检查是否存在"参数表"工作表
            if "参数表" not in wb.sheetnames:
                print(f"警告: {file} 中没有'参数表'工作表，跳过")
                continue
                
            validation_ws = wb["参数表"]
            
            # 创建居中对齐样式
            center_alignment = Alignment(horizontal='center', vertical='center')
            
            # 按照固定顺序更新参数表（使用PARAM_NAMES的顺序）
            for col_idx, param_name in enumerate(PARAM_NAMES, 1):
                # 检查这个参数是否有数据
                params = validation_data.get(param_name, [])
                
                # 检查是否需要更新这一列
                needs_update = False
                
                # 检查表头是否匹配
                current_header = validation_ws.cell(row=1, column=col_idx).value
                if current_header != param_name:
                    needs_update = True
                    print(f"表头不匹配: 当前'{current_header}'，期望'{param_name}'")
                else:
                    # 检查参数内容是否匹配
                    current_params = []
                    row_idx = 2
                    while row_idx <= validation_ws.max_row:
                        cell_value = validation_ws.cell(row=row_idx, column=col_idx).value
                        if cell_value is None:
                            break
                        current_params.append(str(cell_value))
                        row_idx += 1
                    
                    # 如果参数数量或内容有变化，需要更新
                    if current_params != [str(p) for p in params]:
                        needs_update = True
                        print(f"参数内容变化: 当前{len(current_params)}个，期望{len(params)}个")
                
                # 如果需要更新，重新写入这一列
                if needs_update:
                    print(f"更新 {file} 中的 {param_name} 参数")
                    
                    # 清除这一列的内容（从第1行到最大行）
                    for row_idx in range(1, validation_ws.max_row + 1):
                        validation_ws.cell(row=row_idx, column=col_idx).value = None
                    
                    # 写入表头
                    header_cell = validation_ws.cell(row=1, column=col_idx, value=param_name)
                    header_cell.alignment = center_alignment
                    
                    # 写入参数数据
                    for row_idx, param_value in enumerate(params, 2):
                        cell = validation_ws.cell(row=row_idx, column=col_idx, value=param_value)
                        cell.alignment = center_alignment
                    
                    print(f"写入 {len(params)} 个参数")
                else:
                    print(f"{param_name} 列无需更新")
                
                # 为所有列创建或更新命名区域
                range_name = f"{param_name}List"

                # 计算期望的动态公式
                col_letter = get_column_letter(col_idx)
                expected_dynamic_range = f"OFFSET(参数表!${col_letter}$2,0,0,COUNTA(参数表!${col_letter}:${col_letter})-1,1)"

                # 检查是否已存在同名区域
                if range_name in wb.defined_names:
                    existing_named_range = wb.defined_names[range_name]
                    existing_range = existing_named_range.attr_text
                    
                    # 如果现有区域已经是正确的动态公式，则跳过
                    if existing_range == expected_dynamic_range:
                        print(f"动态命名区域 {range_name} 已存在且公式正确，无需更新")
                        continue
                    else:
                        print(f"命名区域 {range_name} 的公式不匹配，需要更新")
                        print(f"当前公式: {existing_range}")
                        print(f"期望公式: {expected_dynamic_range}")
                else:
                    print(f"动态命名区域 {range_name} 不存在，将创建")

                # 创建或更新命名区域
                try:
                    from openpyxl.workbook.defined_name import DefinedName
                    # 删除已存在的区域（如果存在）
                    if range_name in wb.defined_names:
                        del wb.defined_names[range_name]
                    
                    # 创建新的命名区域
                    wb.defined_names[range_name] = DefinedName(name=range_name, attr_text=expected_dynamic_range)
                    print(f"成功{'更新' if range_name in wb.defined_names else '创建'}动态命名区域: {range_name}")
                    
                except Exception as e:
                    print(f"处理动态命名区域 {range_name} 时发生错误: {e}")
            
            # 保存工作簿
            try:
                wb.save(file_path)
                print(f"成功保存文件: {file}")
                success_count += 1
            except Exception as e:
                print(f"保存失败: {e}")
                # 尝试关闭工作簿以防止文件锁定
                try:
                    wb.close()
                except:
                    pass
                
        except Exception as e:
            print(f"处理文件 {file} 时发生错误: {e}")
            # 尝试关闭工作簿以防止文件锁定
            try:
                wb.close()
            except:
                pass
    
    print(f"处理完成，成功更新 {success_count}/{len(excel_files)} 个文件")
    return success_count > 0