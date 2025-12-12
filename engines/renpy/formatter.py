"""Ren'Py 格式器"""
from typing import Any, List
from core.scenario_output.base import IFormatter
from core.logger import get_logger

logger = get_logger(__name__)


class RenpyFormatter(IFormatter):
    """Ren'Py 引擎格式器 - 处理缩进等格式"""
    
    def format(self, structured_data: dict) -> Any:
        """格式化结构化数据（保留接口兼容性）"""
        return structured_data
    
    def format_output(self, data: Any, engine_config: Any) -> List[str]:
        """
        格式化输出数据 - 应用 Ren'Py 特定的缩进规则
        
        Args:
            data: 命令列表（List[str]）
            engine_config: 引擎配置（RenpyConfig）
            
        Returns:
            格式化后的命令列表
        """
        if not isinstance(data, list):
            return []
        
        formatted_lines = []
        indent_size = getattr(engine_config, 'indent_size', 4)
        
        for line in data:
            if not isinstance(line, str):
                line = str(line)
            
            # Ren'Py 特定的缩进处理
            stripped = line
            if stripped.startswith("label "):
                # label 行不缩进
                formatted_lines.append(stripped)
            else:
                # 其他行添加缩进
                indent = " " * indent_size
                formatted_lines.append(indent + line)
        
        return formatted_lines
    
    def get_format_type(self) -> str:
        return "text"
    
    def get_engine_type(self) -> str:
        return "renpy"

