"""
Naninovel 引擎配置
"""
from dataclasses import dataclass
from core.config_manager import EngineConfig


@dataclass
class NaninovelConfig(EngineConfig):
    """Naninovel 引擎配置"""
    engine_type: str = "naninovel"
    file_extension: str = ".nani"
    command_prefix: str = "@"

