"""文本输出器"""
from pathlib import Path
from typing import Any, List, Dict
from core.scenario_output.base import IOutputWriter, OutputFormat, OutputConfig
from core.logger import get_logger

logger = get_logger(__name__)


class TextScenarioWriter(IOutputWriter):
    """文本输出器 - 用于Ren'Py、Naninovel等脚本"""

    def __init__(self):
        self.supported_formats = [OutputFormat.TEXT]
    
    def write(self, data: Any, output_path: Path, config: OutputConfig) -> bool:
        """
        写入文本文件
        
        Args:
            data: 可以是字符串列表或字典
            output_path: 输出路径
            config: 输出配置
        """
        try:
            # 确保目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 将数据转换为行列表
            lines = self._prepare_data(data, config)
            
            # 写入文件
            with open(output_path, 'w', encoding=config.encoding) as f:
                f.write('\n'.join(lines))
            
            logger.info(f"文本文件已保存: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存文本文件失败: {e}")
            return False
    
    def _prepare_data(self, data: Any, config: OutputConfig) -> List[str]:
        """准备数据"""
        if isinstance(data, list):
            # 如果是字符串列表，直接使用
            if all(isinstance(item, str) for item in data):
                return data
            # 如果是字典列表，尝试提取命令
            elif all(isinstance(item, dict) for item in data):
                lines = []
                for item in data:
                    if 'commands' in item and isinstance(item['commands'], list):
                        lines.extend(item['commands'])
                return lines
        
        elif isinstance(data, dict):
            # 如果是字典，尝试提取命令
            if 'commands' in data and isinstance(data['commands'], list):
                return data['commands']
        
        # 默认返回空列表
        return []
    
    def supports_format(self, format: OutputFormat) -> bool:
        return format in self.supported_formats
    
    def get_extension(self) -> str:
        return ".txt"