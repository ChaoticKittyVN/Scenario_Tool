"""输出管理器"""
from pathlib import Path
from typing import Any, Dict, List, Optional
import importlib
from core.scenario_output.base import OutputFormat, OutputConfig, IOutputWriter
from core.logger import get_logger

logger = get_logger(__name__)


class OutputManager:
    """输出管理器"""
    
    def __init__(self):
        self._writers: Dict[OutputFormat, IOutputWriter] = {}
        self._formatters: Dict[str, Any] = {}  # 引擎类型 -> 格式器
    
    def register_writer(self, writer: IOutputWriter) -> None:
        """注册输出器"""
        for fmt in writer.supported_formats:
            self._writers[fmt] = writer
            logger.debug(f"注册输出器: {writer.__class__.__name__} -> {fmt}")
    
    def register_formatter(self, engine_type: str, formatter: Any) -> None:
        """注册格式器"""
        self._formatters[engine_type] = formatter
        logger.debug(f"注册格式器: {formatter.__class__.__name__} -> {engine_type}")
    
    def get_writer(self, format: OutputFormat) -> Optional[IOutputWriter]:
        """获取输出器"""
        return self._writers.get(format)
    
    def get_formatter(self, engine_type: str) -> Optional[Any]:
        """
        获取格式器，如果不存在则尝试动态加载
        
        Args:
            engine_type: 引擎类型
            
        Returns:
            格式器实例，如果不存在则返回 None
        """
        # 如果已注册，直接返回
        if engine_type in self._formatters:
            return self._formatters[engine_type]
        
        # 尝试动态加载格式器
        formatter = self._load_formatter(engine_type)
        if formatter:
            self._formatters[engine_type] = formatter
            return formatter
        
        return None
    
    def _load_formatter(self, engine_type: str) -> Optional[Any]:
        """
        动态加载格式器
        
        Args:
            engine_type: 引擎类型
            
        Returns:
            格式器实例，如果加载失败则返回 None
        """
        try:
            # 尝试从 engines.{engine_type}.formatter 导入格式器
            module_name = f"engines.{engine_type}.formatter"
            module = importlib.import_module(module_name)
            
            # 查找格式器类（类名格式：{EngineType}Formatter）
            formatter_class_name = f"{engine_type.capitalize()}Formatter"
            if hasattr(module, formatter_class_name):
                formatter_class = getattr(module, formatter_class_name)
                formatter = formatter_class()
                logger.debug(f"动态加载格式器: {formatter_class_name} -> {engine_type}")
                return formatter
            else:
                logger.warning(f"模块 {module_name} 中未找到格式器类 {formatter_class_name}")
                return None
                
        except ImportError as e:
            logger.debug(f"无法加载引擎 {engine_type} 的格式器: {e}")
            return None
        except Exception as e:
            logger.warning(f"加载格式器时出错: {e}")
            return None
    
    def output(
        self,
        data: Any,
        output_path: Path,
        format: OutputFormat,
        engine_config: Any,
        apply_formatting: bool = True
    ) -> bool:
        """
        输出数据
        
        Args:
            data: 输入数据
            output_path: 输出路径
            format: 输出格式
            engine_config: 引擎配置
            apply_formatting: 是否应用格式器
        """
        # 获取输出器
        writer = self.get_writer(format)
        if not writer:
            logger.error(f"不支持的输出格式: {format}")
            return False
        
        # 应用格式器
        formatted_data = data
        if apply_formatting and hasattr(engine_config, 'engine_type'):
            formatter = self.get_formatter(engine_config.engine_type)
            if formatter:
                try:                    
                    if isinstance(data, dict):
                        formatted_data = {}
                        for sheet_name, sheet_data in data.items():
                            formatted_data[sheet_name] = formatter.format_output(sheet_data, engine_config)
                    else:
                        formatted_data = formatter.format_output(data, engine_config)
                except Exception as e:
                    logger.warning(f"格式器处理失败，使用原始数据: {e}")
        
        # 准备输出配置
        config = OutputConfig(
            format=format,
            engine_config=engine_config,
            encoding="utf-8",
            auto_format=True
        )
        
        # 写入文件
        return writer.write(formatted_data, output_path, config)
    
    @classmethod
    def create_default(cls) -> 'OutputManager':
        """创建默认输出管理器"""
        manager = cls()
        
        # 注册默认输出器
        try:
            from .writers.text_writer import TextScenarioWriter
            from .writers.excel_writer import ExcelScenarioWriter
            from .writers.json_writer import JsonScenarioWriter
            from .writers.csv_writer import CsvScenarioWriter
            from .writers.xml_writer import XmlScenarioWriter
            
            manager.register_writer(TextScenarioWriter())
            manager.register_writer(ExcelScenarioWriter())
            manager.register_writer(JsonScenarioWriter())
            manager.register_writer(CsvScenarioWriter())
            manager.register_writer(XmlScenarioWriter())
            
        except ImportError as e:
            logger.error(f"导入输出器失败: {e}")
        
        return manager