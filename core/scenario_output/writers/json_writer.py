"""JSON输出器"""
import json
from pathlib import Path
from typing import Any, List, Dict
from core.scenario_output.base import IOutputWriter, OutputFormat, OutputConfig
from core.logger import get_logger

logger = get_logger(__name__)


class JsonScenarioWriter(IOutputWriter):
    """JSON输出器 - 用于数据交换和配置存储"""

    def __init__(self):
        self.supported_formats = [OutputFormat.JSON]
    
    def write(self, data: Any, output_path: Path, config: OutputConfig) -> bool:
        """
        写入JSON文件
        
        Args:
            data: 可以是字典、列表或其他可序列化的数据
            output_path: 输出路径
            config: 输出配置
        """
        try:
            # 确保目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 准备数据
            json_data = self._prepare_data(data, config)
            
            # 写入文件
            with open(output_path, 'w', encoding=config.encoding) as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"JSON文件已保存: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存JSON文件失败: {e}")
            return False
    
    def _prepare_data(self, data: Any, config: OutputConfig) -> Any:
        """准备数据"""
        # 如果已经是可序列化的格式，直接返回
        if isinstance(data, (dict, list, str, int, float, bool, type(None))):
            return data
        
        # 如果是其他类型，尝试转换为字典或列表
        if hasattr(data, '__dict__'):
            return data.__dict__
        
        # 默认返回原数据（可能会失败，但让json.dump来处理错误）
        return data
    
    def supports_format(self, format: OutputFormat) -> bool:
        return format in self.supported_formats
    
    def get_extension(self) -> str:
        return ".json"

