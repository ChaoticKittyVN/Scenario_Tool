"""
Naninovel Engine Module
Naninovel 引擎实现
"""
from core.engine_registry import register_engine
from core.engine_processor import EngineProcessor
from .config import NaninovelConfig


@register_engine(
    name="naninovel",
    display_name="Naninovel",
    file_extension=".nani",
    config_class=NaninovelConfig,
    description="Unity Naninovel 视觉小说引擎"
)
def create_naninovel_processor(config: NaninovelConfig, translator):
    """创建 Naninovel 处理器工厂函数"""
    processor = EngineProcessor("naninovel", translator, config)
    processor.setup()
    return processor
