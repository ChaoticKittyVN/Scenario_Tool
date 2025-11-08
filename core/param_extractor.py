# core/param_extractor.py
import pandas as pd
from typing import Dict, Any, List

class ParamExtractor:
    """
    参数抓取器 - 从单行Excel数据中提取参数
    
    职责：
    1. 根据FORMAT_CONFIG知道要抓取哪些参数
    2. 从单行数据中提取这些参数的值
    3. 按category分组参数
    """
    
    def __init__(self, format_config: Dict):
        """
        初始化参数抓取器
        
        Args:
            format_config: 格式配置字典，包含所有参数定义
        """
        self.format_config = format_config
        # 从配置中获取所有需要抓取的参数名
        self.all_param_names = list(format_config.keys())
    
    def extract_single_row(self, row_data: pd.Series) -> Dict[str, Dict[str, Any]]:
        """
        从单行数据中提取参数，并按category分组
        
        Args:
            row_data: pandas Series，一行的所有数据
            
        Returns:
            Dict: 按category分组的参数字典
            {
                "note_audio": {"Note": "值", "Music": "值", ...},
                "scene": {"Background": "值", ...},
                ...
            }
        """
        # 初始化分组字典
        grouped_params = {}
        
        # 遍历所有定义的参数
        for param_name in self.all_param_names:
            # 检查该参数在行数据中是否存在
            if param_name in row_data:
                value = row_data[param_name]
                
                # 处理空值
                if pd.isna(value) or value == "":
                    continue
                    
                # 获取参数的category
                config = self.format_config[param_name]
                category = config.get("category", "unknown")
            
                # 添加警告：未知的 category
                if category == "unknown":
                    print(f"警告: 参数 '{param_name}' 未定义 category")

                # 按category分组
                if category not in grouped_params:
                    grouped_params[category] = {}
                
                grouped_params[category][param_name] = value
        
        return grouped_params
    
    def get_all_required_columns(self) -> List[str]:
        """
        获取所有需要的列名（用于验证表格结构）
        
        Returns:
            List[str]: 所有参数名列表
        """
        return self.all_param_names