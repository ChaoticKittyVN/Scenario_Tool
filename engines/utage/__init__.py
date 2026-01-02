# engines/utage/__init__.py
"""
Utage Engine Module
Utage 引擎实现
"""
from core.engine_registry import register_engine
from core.config_manager import UtageConfig
from core.engine_processor import EngineProcessor


@register_engine(
    name="utage",
    display_name="Utage",
    file_extension=".xlsx",  # Utage 使用 Excel 文件
    config_class=UtageConfig,
    description="Utage 视觉小说引擎（Excel格式）"
)
def create_utage_processor(config: UtageConfig, translator):
    """创建 Utage 处理器工厂函数"""
    processor = EngineProcessor("utage", translator, config)
    processor.setup()
    return processor