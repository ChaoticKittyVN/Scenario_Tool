import pandas as pd
import os
from openpyxl import load_workbook
from openpyxl.styles import Alignment

# TODO 未使用
def read_excel_file(file_path, sheet_name=None):
    """
    读取Excel文件，返回所有工作表或指定工作表的DataFrame
    
    参数:
    file_path: Excel文件路径
    sheet_name: 要读取的工作表名称，None表示读取所有工作表
    
    返回:
    如果sheet_name为None，返回包含所有工作表的字典
    如果指定了sheet_name，返回该工作表的DataFrame
    """
    try:
        if sheet_name is None:
            return pd.read_excel(file_path, sheet_name=None)
        else:
            return pd.read_excel(file_path, sheet_name=sheet_name)
    except Exception as e:
        print(f"读取Excel文件失败: {e}")
        return None

def read_column_from_dataframe(df, column_name, fallback_to_first=True):
    """
    从DataFrame中读取指定列的数据
    
    参数:
    df: DataFrame对象
    column_name: 要读取的列名
    fallback_to_first: 如果指定列不存在，是否回退到使用第一列
    
    返回:
    列数据的列表，如果列不存在且不回退则返回空列表
    """
    if df is None or len(df.columns) == 0:
        return []
    
    if column_name in df.columns:
        return df[column_name].dropna().tolist()
    elif fallback_to_first and len(df.columns) > 0:
        print(f"警告: 列 '{column_name}' 不存在，使用第一列数据")
        return df.iloc[:, 0].dropna().tolist()
    else:
        print(f"警告: 列 '{column_name}' 不存在，且未启用回退")
        return []
