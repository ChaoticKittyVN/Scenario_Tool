import pandas as pd
from pathlib import Path
from typing import Dict, List, Any

from core.logger import get_logger
from core.constants import SheetName, ColumnName, Marker

from .excel_decorators import handle_excel_operation
from .excel_exceptions import ExcelDataError

logger = get_logger(__name__)

# ==================== DataFrame处理器 ====================
class DataFrameProcessor:
    """
    数据框处理器
    负责DataFrame数据的提取、过滤和验证
    """
    
    def __init__(self, config=None):
        """
        初始化数据框处理器
        
        Args:
            config: 应用配置对象
        """
        self.config = config
    
    @handle_excel_operation
    def extract_valid_rows(self, df: pd.DataFrame, sheet_name: str = "") -> pd.DataFrame:
        """
        提取有效行数据（基于END标记和忽略规则）
        
        Args:
            df: 输入的DataFrame
            sheet_name: 工作表名称（用于日志）
            
        Returns:
            pd.DataFrame: 有效行的DataFrame
            
        Raises:
            ExcelDataError: 数据格式错误
        """
        try:
            if df.empty:
                logger.warning(f"数据框为空，工作表: {sheet_name}")
                return df
            
            # 查找END标记位置
            end_index = self.find_marker_position(df, ColumnName.NOTE.value, Marker.END.value)
            if end_index == -1:
                logger.warning(f"未找到END标记，工作表: {sheet_name}")
                return pd.DataFrame()
            
            # 提取END标记之前的行
            valid_df = df.iloc[:end_index].copy()
            
            # 应用忽略规则（如果配置存在）
            if self.config and hasattr(self.config, 'processing'):
                valid_df = self._apply_ignore_rules(valid_df)
            
            logger.info(f"提取有效行: {sheet_name}, 原始行数: {len(df)}, 有效行数: {len(valid_df)}")
            return valid_df
            
        except Exception as e:
            logger.error(f"提取有效行失败: {sheet_name}", exc_info=True)
            raise ExcelDataError(f"提取有效行失败: {sheet_name}", e)
    
    def _apply_ignore_rules(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        应用忽略规则过滤数据
        
        Args:
            df: 输入的DataFrame
            
        Returns:
            pd.DataFrame: 过滤后的DataFrame
        """
        ignore_mode = getattr(self.config.processing, 'ignore_mode', False) if self.config and hasattr(self.config, 'processing') else False
        ignore_words = getattr(self.config.processing, 'ignore_words', []) if self.config and hasattr(self.config, 'processing') else []

        if not ignore_mode:
            return df

        ignore_column = ColumnName.IGNORE.value
        if ignore_column not in df.columns:
            return df

        # 过滤掉标记为忽略的行
        mask = ~df[ignore_column].isin(ignore_words)
        filtered_df = df[mask].reset_index(drop=True)

        ignored_count = len(df) - len(filtered_df)
        if ignored_count > 0:
            logger.info(f"忽略 {ignored_count} 行数据")

        return filtered_df
    
    def get_column_data(self, df: pd.DataFrame, column_name: str, default_value: Any = "") -> pd.Series:
        """
        安全获取列数据（处理列不存在的情况）
        
        Args:
            df: 输入的DataFrame
            column_name: 列名
            default_value: 列不存在时的默认值
            
        Returns:
            pd.Series: 列数据
        """
        if column_name in df.columns:
            return df[column_name]
        else:
            logger.warning(f"列不存在: {column_name}，返回默认值")
            return pd.Series([default_value] * len(df))
    
    def find_marker_position(self, df: pd.DataFrame, marker_column: str, marker_value: str) -> int:
        """
        查找标记位置（如END标记）
        
        Args:
            df: 输入的DataFrame
            marker_column: 标记列名
            marker_value: 标记值
            
        Returns:
            int: 标记位置索引，未找到返回-1
        """
        try:
            if marker_column not in df.columns:
                logger.debug(f"标记列不存在: {marker_column}")
                return -1
            
            # 查找包含标记值的行
            matches = df[df[marker_column] == marker_value]
            if not matches.empty:
                position = matches.index[0]
                logger.debug(f"找到标记 '{marker_value}' 在位置 {position}")
                return position
                
            logger.debug(f"未找到标记 '{marker_value}'")
            return -1
            
        except Exception as e:
            logger.error(f"查找标记位置失败: {marker_column}={marker_value}", exc_info=True)
            # 这里不抛出异常，返回-1表示未找到
            return -1
    
    def validate_dataframe(self, df: pd.DataFrame, required_columns: List[str]) -> bool:
        """
        验证DataFrame是否包含必需的列
        
        Args:
            df: 输入的DataFrame
            required_columns: 必需的列名列表
            
        Returns:
            bool: 是否验证通过
        """
        if df.empty:
            logger.warning("数据框为空")
            return False

        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.warning(f"缺少必需列: {missing_columns}")
            return False

        return True
    
    def has_valid_data(self, value: Any) -> bool:
        """检查值是否有效（非空且非NaN）"""
        if pd.isna(value):
            return False
        if value == "":
            return False
        if value is None:
            return False
        return True
    
    def extract_parameters(self, row_data: pd.Series | Dict, needed_params: List[str]) -> Dict[str, Any]:
        """
        从行数据中提取指定参数
        
        Args:
            row_data: pandas Series，一行的所有数据
            needed_params: 需要的参数名列表
            
        Returns:
            Dict[str, Any]: 提取的参数字典
        """
        if row_data is pd.Series:
            row_data = row_data.to_dict()
        
        params = {}

        for param_name in needed_params:
            if param_name in row_data:
                value = row_data[param_name]
                if self.has_valid_data(value):
                    params[param_name] = value
        
        return params
    
    def extract_mapping_columns(self, df: pd.DataFrame, key_column: str, value_column: str) -> Dict[str, str]:
        """
        从DataFrame中提取两列构建映射字典
        
        Args:
            df: 输入的DataFrame
            key_column: 键列名
            value_column: 值列名
            
        Returns:
            Dict[str, str]: 映射字典
        """
        mapping = {}

        if key_column not in df.columns or value_column not in df.columns:
            logger.warning(f"缺少必需的列: {key_column} 或 {value_column}")
            return mapping

        for _, row in df.iterrows():
            key = row[key_column]
            value = row[value_column]
            
            if self.has_valid_data(key) and self.has_valid_data(value):
                mapping[str(key)] = str(value)

        return mapping

    def extract_param_names(self, df: pd.DataFrame, param_column: str = "ExcelParam") -> List[str]:
        """
        从DataFrame中提取参数名列表（用于填写参数表）
        
        Args:
            df: 输入的DataFrame
            param_column: 参数列名
            
        Returns:
            List[str]: 去重后的参数名列表
        """
        if param_column not in df.columns:
            logger.warning(f"参数列不存在: {param_column}")
            return []

        param_names = set()
        for _, row in df.iterrows():
            param = row[param_column]
            if self.has_valid_data(param):
                param_names.add(str(param))

        return sorted(list(param_names))

    def extract_columns_for_statistics(self, df: pd.DataFrame, columns: List[str], 
                                    keep_all_rows: bool = False) -> Dict[str, pd.Series]:
        """
        提取用于统计的列

        Args:
            df: 输入的DataFrame
            columns: 要提取的列名列表
            keep_all_rows: 是否保持所有行（用None填充无效值）

        Returns:
            Dict[str, pd.Series]: 列名到Series的映射
        """
        result = {}

        for column in columns:
            if column in df.columns:
                if keep_all_rows:
                    # 保持所有行，无效值填充为None
                    series = df[column].apply(
                        lambda x: str(x).strip() if self.has_valid_data(x) else None
                    )
                else:
                    # 只保留有效数据的行
                    series = df[column][df[column].apply(self.has_valid_data)]
                result[column] = series
            else:
                logger.warning(f"统计列不存在: {column}")
                result[column] = pd.Series(dtype=object)
        
        return result