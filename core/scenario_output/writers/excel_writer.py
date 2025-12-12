# core/output/writers/excel_writer.py
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from core.scenario_output.base import IOutputWriter, OutputFormat, OutputConfig
from core.logger import get_logger

logger = get_logger(__name__)

class ExcelScenarioWriter(IOutputWriter):
    """Excel输出器 - 特别适合Utage引擎"""
    
    def __init__(self):
        self.supported_formats = [OutputFormat.EXCEL]
        
    def write(self, data: List[Dict[str, Any]], output_path: Path, config: OutputConfig) -> bool:
        """
        写入Excel文件
        
        Args:
            data: 结构化数据列表，每个字典代表一行
            output_path: 输出路径
            config: 输出配置
        """
        try:
            # 确保目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 将数据转换为DataFrame
            df = pd.DataFrame(data)
            
            # 应用引擎特定的格式配置
            df = self._apply_engine_formatting(df, config)
            
            # 保存Excel
            df.to_excel(output_path, index=False, engine='openpyxl')
            
            logger.info(f"Excel文件已保存: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存Excel文件失败: {e}")
            return False
    
    def _apply_engine_formatting(self, df: pd.DataFrame, config: OutputConfig) -> pd.DataFrame:
        """应用引擎特定的格式"""
        engine_type = config.engine_config.engine_type
        
        if engine_type == "utage":
            # Utage引擎特定的列顺序和格式
            required_columns = ["Character", "Text", "Expression", "Position", "Voice"]
            # 确保所有必需列都存在
            for col in required_columns:
                if col not in df.columns:
                    df[col] = ""
            # 重新排序列
            existing_columns = [col for col in required_columns if col in df.columns]
            other_columns = [col for col in df.columns if col not in required_columns]
            df = df[existing_columns + other_columns]
        
        return df
    
    def supports_format(self, format: OutputFormat) -> bool:
        return format in self.supported_formats
    
    def get_extension(self) -> str:
        return ".xlsx"