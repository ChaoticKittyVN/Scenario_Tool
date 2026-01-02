"""
Ren'Py Engine Module
Ren'Py 引擎实现
"""
from core.engine_registry import register_engine
from core.engine_processor import EngineProcessor
from .config import RenpyConfig


@register_engine(
    name="renpy",
    display_name="Ren'Py",
    file_extension=".rpy",
    config_class=RenpyConfig,
    description="Ren'Py 视觉小说引擎"
)
def create_renpy_processor(config: RenpyConfig, translator):
    """创建 Ren'Py 处理器工厂函数"""
    processor = EngineProcessor("renpy", translator, config)
    processor.setup()
    return processor
