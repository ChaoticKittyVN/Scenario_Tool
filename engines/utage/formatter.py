# engines/utage/formatter.py
from typing import Any, List, Dict
import pandas as pd
from core.scenario_output.base import IFormatter
from core.logger import get_logger

logger = get_logger(__name__)


class UtageFormatter(IFormatter):
    """Utage 引擎格式器 - 处理List[Dict]数据"""

    def format(self, structured_data: dict) -> Any:
        """格式化结构化数据（保留接口兼容性）"""
        return structured_data

    def format_output(self, data: Any, engine_config: Any) -> pd.DataFrame:
        """
        格式化输出数据 - 将List[Dict]转换为DataFrame

        Args:
            data: 命令字典列表 (List[Dict])
            engine_config: 引擎配置

        Returns:
            DataFrame: Utage表格格式的数据
        """
        # 如果已经是DataFrame，直接返回（先检查这个，避免布尔判断问题）
        if isinstance(data, pd.DataFrame):
            logger.debug(f"UtageFormatter接收到DataFrame: {len(data)} 行, {len(data.columns)} 列")
            return self._format_dataframe(data, engine_config)
        
        # 检查是否为空（避免对DataFrame进行布尔判断）
        if data is None:
            logger.debug("UtageFormatter接收到None数据")
            return pd.DataFrame()
        
        # 处理列表类型
        if isinstance(data, list):
            # 检查列表是否为空
            if len(data) == 0:
                logger.debug("UtageFormatter接收到空列表")
                return pd.DataFrame()
            
            # 检查所有元素是否都是字典
            if all(isinstance(item, dict) for item in data):
                logger.debug(f"UtageFormatter接收到字典列表: {len(data)} 项")
                if len(data) > 0:
                    logger.debug(f"第一项示例: {list(data[0].keys())}")
                
                # 清理数据：确保所有值都是标量（不是DataFrame或其他复杂对象）
                cleaned_data = []
                for item in data:
                    cleaned_item = {}
                    for key, value in item.items():
                        # 如果值是DataFrame，转换为字符串
                        if isinstance(value, pd.DataFrame):
                            logger.warning(f"发现DataFrame类型的值，键: {key}，将转换为字符串")
                            cleaned_item[key] = str(value)
                        # 如果值是列表或其他复杂对象，也转换为字符串
                        elif isinstance(value, (list, dict)) and not isinstance(value, str):
                            cleaned_item[key] = str(value)
                        else:
                            cleaned_item[key] = value
                    cleaned_data.append(cleaned_item)
                
                try:
                    df = pd.DataFrame(cleaned_data)
                    return self._format_dataframe(df, engine_config)
                except Exception as e:
                    logger.error(f"创建DataFrame失败: {e}", exc_info=True)
                    return pd.DataFrame()
            
            # 如果是字符串列表
            elif all(isinstance(item, str) for item in data):
                logger.warning("UtageFormatter接收到字符串列表，需要解析")
                return pd.DataFrame()
            
            # 混合类型列表
            else:
                logger.warning(f"UtageFormatter接收到混合类型列表，第一项类型: {type(data[0]) if data else 'N/A'}")
                return pd.DataFrame()

        # 其他不支持的类型
        else:
            logger.error(f"UtageFormatter不支持的数据类型: {type(data)}, 数据: {str(data)[:100]}")
            return pd.DataFrame()

    def _format_dataframe(self, df: pd.DataFrame, engine_config: Any) -> pd.DataFrame:
        """格式化DataFrame为Utage标准格式"""
        # 如果DataFrame为空，返回一个包含标准列的空DataFrame
        if df.empty:
            utage_columns = [
                "Command", "Arg1", "Arg2", "Arg3", "Arg4", "Arg5", "Arg6",
                "WaitType", "Text", "PageCtrl", "Voice", "WindowType"
            ]
            return pd.DataFrame(columns=utage_columns)
        
        # Utage 标准列顺序
        utage_columns = [
            "Command", "Arg1", "Arg2", "Arg3", "Arg4", "Arg5", "Arg6",
            "WaitType", "Text", "PageCtrl", "Voice", "WindowType"
        ]

        # 确保所有标准列都存在（填充空字符串）
        for col in utage_columns:
            if col not in df.columns:
                df[col] = ""

        # 获取其他非标准列
        other_columns = [col for col in df.columns if col not in utage_columns]

        # 重新排序列顺序：先标准列，后其他列
        # 注意：由于我们已经确保所有utage_columns都存在，所以直接使用utage_columns
        try:
            return df[utage_columns + other_columns]
        except Exception as e:
            logger.error(f"格式化DataFrame时出错: {e}, DataFrame形状: {df.shape}, 列: {list(df.columns)}")
            # 如果出错，尝试只返回标准列
            return df[utage_columns] if all(col in df.columns for col in utage_columns) else df

    def get_format_type(self) -> str:
        return "excel"

    def get_engine_type(self) -> str:
        return "utage"