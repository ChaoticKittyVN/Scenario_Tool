"""Naninovel 格式器"""
from typing import Any, List
from core.scenario_output.base import IFormatter
from core.logger import get_logger

logger = get_logger(__name__)


class NaninovelFormatter(IFormatter):
    """Naninovel 引擎格式器"""
    
    def format(self, structured_data: dict) -> Any:
        """格式化结构化数据（保留接口兼容性）"""
        return structured_data
    
    def format_output(self, data: Any, engine_config: Any) -> List[str]:
        """
        格式化输出数据
        
        Args:
            data: 命令列表（List[str]）
            engine_config: 引擎配置（NaninovelConfig）
            
        Returns:
            格式化后的命令列表
        """
        if not isinstance(data, list):
            return []
        
        formatted_lines = []
        for line in data:
            if not isinstance(line, str):
                line = str(line)
            # Naninovel 通常不需要特殊缩进处理，直接返回
            formatted_lines.append(line)
        
        return formatted_lines
    
    def get_format_type(self) -> str:
        return "text"
    
    def get_engine_type(self) -> str:
        return "naninovel"

