# core/output/writers/excel_writer.py
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Union
from core.scenario_output.base import IOutputWriter, OutputFormat, OutputConfig
from core.logger import get_logger

logger = get_logger(__name__)

class ExcelScenarioWriter(IOutputWriter):
    """Excel输出器 - 特别适合Utage引擎"""

    def __init__(self):
        self.supported_formats = [OutputFormat.EXCEL]

    def write(self, data: Union[List[Dict[str, Any]], pd.DataFrame, Dict[str, Any]], 
              output_path: Path, config: OutputConfig) -> bool:
        """
        写入Excel文件

        Args:
            data: 可以是字典列表、DataFrame或字典（sheet_name -> sheet_data）
            output_path: 输出路径
            config: 输出配置
        """
        try:
            # 确保目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 处理字典类型（多sheet情况，如Utage引擎）
            if isinstance(data, dict):
                # 检查是否是sheet字典（键是字符串，值是列表或DataFrame）
                # 如果所有值都是列表或DataFrame，则认为是多sheet结构
                is_sheet_dict = all(
                    isinstance(k, str) and 
                    isinstance(v, (list, pd.DataFrame))
                    for k, v in data.items()
                ) if data else False
                
                if is_sheet_dict:
                    # 多sheet写入
                    from engines.utage.formatter import UtageFormatter
                    formatter = UtageFormatter()
                    
                    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                        sheet_written = False
                        for sheet_name, sheet_data in data.items():
                            try:
                                # 格式化数据
                                df = formatter.format_output(sheet_data, config.engine_config)
                                
                                # 检查DataFrame是否为空
                                if df.empty:
                                    logger.warning(f"Sheet '{sheet_name}' 为空，跳过")
                                    continue
                                
                                # 确保DataFrame中不包含DataFrame对象（额外安全检查）
                                df = self._clean_dataframe_for_excel(df)
                                
                                # 再次验证DataFrame中没有DataFrame对象
                                self._validate_dataframe_for_excel(df, sheet_name)
                                
                                # 确保sheet名称有效（Excel限制31个字符，且不能包含某些字符）
                                valid_sheet_name = self._sanitize_sheet_name(sheet_name)
                                
                                # 写入sheet
                                df.to_excel(writer, sheet_name=valid_sheet_name, index=False)
                                sheet_written = True
                                logger.debug(f"已写入sheet: {valid_sheet_name} ({len(df)} 行)")
                            except Exception as e:
                                logger.error(f"写入sheet '{sheet_name}' 时出错: {e}", exc_info=True)
                                continue
                        
                        if not sheet_written:
                            logger.error("所有sheet均为空或写入失败，未生成Excel文件")
                            return False
                    
                    # 统计成功写入的sheet数量
                    written_sheets = []
                    for k, v in data.items():
                        if isinstance(v, pd.DataFrame):
                            if not v.empty:
                                written_sheets.append(k)
                        elif isinstance(v, list) and len(v) > 0:
                            written_sheets.append(k)
                        elif isinstance(v, list) and len(v) == 0:
                            pass  # 空列表，跳过
                        else:
                            written_sheets.append(k)  # 其他类型，假设已写入
                    
                    logger.info(f"Excel文件已保存: {output_path} (共 {len(written_sheets)} 个sheet)")
                    return True
                else:
                    # 普通字典，转换为DataFrame
                    df = pd.DataFrame([data])
            
            elif isinstance(data, pd.DataFrame):
                df = data
            elif isinstance(data, list):
                df = self._list_to_dataframe(data)
            else:
                logger.error(f"不支持的数据类型: {type(data)}")
                return False

            # 应用引擎特定的格式配置
            df = self._apply_engine_formatting(df, config)
            
            # 检查DataFrame是否为空
            if df.empty:
                logger.warning("DataFrame为空，未写入任何内容")
                return False

            # 保存Excel（单sheet）
            df.to_excel(output_path, index=False, engine='openpyxl')

            logger.info(f"Excel文件已保存: {output_path} ({len(df)} 行)")
            return True

        except ImportError as e:
            logger.error(f"缺少必要的依赖库（openpyxl）: {e}")
            logger.error("请运行: pip install openpyxl")
            return False
        except Exception as e:
            logger.error(f"保存Excel文件失败: {e}", exc_info=True)
            return False
    
    def _validate_dataframe_for_excel(self, df: pd.DataFrame, sheet_name: str) -> None:
        """
        验证DataFrame是否适合写入Excel
        
        Args:
            df: 要验证的DataFrame
            sheet_name: sheet名称（用于错误信息）
        """
        # 检查是否有DataFrame对象（使用安全的检查方式）
        try:
            for col in df.columns:
                if df[col].dtype == 'object':
                    # 采样检查（避免对大数据集进行全量检查）
                    sample_size = min(10, len(df))
                    sample_indices = list(df.index[:sample_size])
                    for idx in sample_indices:
                        try:
                            value = df.at[idx, col]
                            if isinstance(value, pd.DataFrame):
                                raise ValueError(
                                    f"Sheet '{sheet_name}' 列 '{col}' 行 {idx} 包含DataFrame对象，"
                                    "这会导致Excel写入失败。请检查数据源。"
                                )
                        except (KeyError, IndexError):
                            continue
        except Exception as e:
            # 如果验证过程出错，记录警告但继续执行
            logger.warning(f"验证DataFrame时出错（可能不影响写入）: {e}")
    
    def _clean_dataframe_for_excel(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清理DataFrame，确保所有值都可以写入Excel
        
        Args:
            df: 要清理的DataFrame
            
        Returns:
            清理后的DataFrame
        """
        # 创建一个副本，避免修改原始DataFrame
        df_clean = df.copy()
        
        # 清理函数：将复杂对象转换为字符串
        def clean_value(value):
            # 使用type检查，避免对DataFrame进行布尔判断
            value_type = type(value)
            if value_type == pd.DataFrame:
                return str(value)
            elif value_type in (list, dict) and not isinstance(value, str):
                return str(value)
            else:
                return value
        
        # 只对object类型的列进行检查和清理
        for col in df_clean.columns:
            if df_clean[col].dtype == 'object':
                try:
                    # 使用astype(str)作为后备方案，确保所有值都是字符串
                    # 但先尝试清理，保留原始值的字符串表示
                    df_clean[col] = df_clean[col].apply(clean_value)
                except Exception as e:
                    # 如果清理失败，直接转换为字符串
                    logger.warning(f"清理列 '{col}' 时出错，将全部转换为字符串: {e}")
                    df_clean[col] = df_clean[col].astype(str)
        
        return df_clean
    
    def _sanitize_sheet_name(self, sheet_name: str) -> str:
        """
        清理sheet名称，确保符合Excel要求
        
        Args:
            sheet_name: 原始sheet名称
            
        Returns:
            清理后的sheet名称
        """
        # Excel限制：最多31个字符，不能包含: \ / ? * [ ]
        invalid_chars = [':', '\\', '/', '?', '*', '[', ']']
        sanitized = sheet_name
        
        # 替换无效字符
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # 截断到31个字符
        if len(sanitized) > 31:
            sanitized = sanitized[:31]
        
        # 如果为空，使用默认名称
        if not sanitized.strip():
            sanitized = "Sheet1"
        
        return sanitized

    def _list_to_dataframe(self, data_list: List[Dict[str, Any]]) -> pd.DataFrame:
        """将字典列表转换为DataFrame"""
        if not data_list:
            return pd.DataFrame()

        return pd.DataFrame(data_list)

    def _apply_engine_formatting(self, df: pd.DataFrame, config: OutputConfig) -> pd.DataFrame:
        """应用引擎特定的格式"""
        engine_type = config.engine_config.engine_type

        if engine_type == "utage":
            # Utage引擎标准的列顺序（根据你提供的）
            utage_columns = [
                "Command", "Arg1", "Arg2", "Arg3", "Arg4", "Arg5", "Arg6",
                "WaitType", "Text", "PageCtrl", "Voice", "WindowType"
            ]

            # 确保所有列都存在（添加缺失的列为空）
            for col in utage_columns:
                if col not in df.columns:
                    df[col] = ""

            # 重新排序，保持Utage标准顺序，其他列放在后面
            existing_utage_cols = [col for col in utage_columns if col in df.columns]
            other_columns = [col for col in df.columns if col not in utage_columns]

            return df[existing_utage_cols + other_columns]

        return df

    def supports_format(self, format: OutputFormat) -> bool:
        return format in self.supported_formats

    def get_extension(self) -> str:
        return ".xlsx"