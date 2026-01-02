"""
Ren'Py 引擎配置
"""
from dataclasses import dataclass
from core.config_manager import EngineConfig


@dataclass
class RenpyConfig(EngineConfig):
    """Ren'Py 引擎配置"""
    engine_type: str = "renpy"
    file_extension: str = ".rpy"
    indent_size: int = 4
    label_indent: bool = False
    default_transition: str = "dissolve"

