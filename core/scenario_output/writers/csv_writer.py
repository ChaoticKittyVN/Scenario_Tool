"""CSV输出器"""
import csv
from pathlib import Path
from typing import Any, List, Dict
from core.scenario_output.base import IOutputWriter, OutputFormat, OutputConfig
from core.logger import get_logger

logger = get_logger(__name__)


class CsvScenarioWriter(IOutputWriter):
    """CSV输出器 - 用于简单的表格数据导出"""

    def __init__(self):
        self.supported_formats = [OutputFormat.CSV]
    
    def write(self, data: Any, output_path: Path, config: OutputConfig) -> bool:
        """
        写入CSV文件
        
        Args:
            data: 字典列表，每个字典代表一行
            output_path: 输出路径
            config: 输出配置
        """
        try:
            # 确保目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 准备数据
            rows = self._prepare_data(data, config)
            
            if not rows:
                logger.warning("没有数据可写入CSV文件")
                return False
            
            # 获取所有字段名
            fieldnames = set()
            for row in rows:
                if isinstance(row, dict):
                    fieldnames.update(row.keys())
            fieldnames = sorted(list(fieldnames))
            
            # 写入CSV文件
            with open(output_path, 'w', encoding=config.encoding, newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    if isinstance(row, dict):
                        writer.writerow(row)
            
            logger.info(f"CSV文件已保存: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存CSV文件失败: {e}")
            return False
    
    def _prepare_data(self, data: Any, config: OutputConfig) -> List[Dict[str, Any]]:
        """准备数据"""
        if isinstance(data, list):
            # 如果是字典列表，直接使用
            if all(isinstance(item, dict) for item in data):
                return data
            # 如果是其他类型的列表，尝试转换
            rows = []
            for item in data:
                if isinstance(item, dict):
                    rows.append(item)
                elif hasattr(item, '__dict__'):
                    rows.append(item.__dict__)
            return rows
        
        elif isinstance(data, dict):
            # 单个字典，转换为列表
            return [data]
        
        # 默认返回空列表
        return []
    
    def supports_format(self, format: OutputFormat) -> bool:
        return format in self.supported_formats
    
    def get_extension(self) -> str:
        return ".csv"

