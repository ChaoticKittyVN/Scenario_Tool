# core/scenario_output/base.py
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from enum import Enum

class OutputFormat(Enum):
    """输出格式枚举"""
    TEXT = "text"      # 纯文本
    EXCEL = "excel"    # Excel文件
    JSON = "json"      # JSON文件
    CSV = "csv"        # CSV文件
    XML = "xml"        # XML文件

class OutputConfig:
    """输出配置"""
    def __init__(
        self,
        format: Union[str, OutputFormat],
        engine_config: Any,
        encoding: str = "utf-8",
        auto_format: bool = True,
        **kwargs
    ):
        self.format = OutputFormat(format) if isinstance(format, str) else format
        self.engine_config = engine_config
        self.encoding = encoding
        self.auto_format = auto_format
        self.kwargs = kwargs

class IOutputWriter(ABC):
    """输出器接口"""

    @abstractmethod
    def write(self, data: List[Any], output_path: Path, config: OutputConfig) -> bool:
        """写入数据"""
        pass

    @abstractmethod
    def supports_format(self, format: OutputFormat) -> bool:
        """是否支持该格式"""
        pass

    @abstractmethod
    def get_extension(self) -> str:
        """获取文件扩展名"""
        pass

class IFormatter(ABC):
    """格式器接口 - 负责将结构化数据转换为特定格式"""

    @abstractmethod
    def format(self, structured_data: Dict[str, Any]) -> Any:
        """格式化数据"""
        pass

    @abstractmethod
    def format_output(self, data: Any, engine_config: Any) -> Any:
        """格式化输出数据

        Args:
            data: 输入数据
            engine_config: 引擎配置

        Returns:
            格式化后的数据
        """
        pass

    @abstractmethod
    def get_format_type(self) -> str:
        """获取格式类型"""
        pass

    @abstractmethod
    def get_engine_type(self) -> str:
        """获取引擎类型"""
        pass