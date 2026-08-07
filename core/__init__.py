"""
Core module
核心模块，提供基础设施和框架功能
"""
from core.logger import get_logger, ScenarioToolLogger
from core.exceptions import (
    ScenarioToolError,
    ConfigError,
    EngineError,
    GeneratorError,
    TranslationError,
    FileValidationError,
    ExcelParseError,
    EngineNotRegisteredError,
    InvalidParameterError
)
from core.config_manager import (
    AppConfig,
    PathConfig,
    ProcessingConfig,
    EngineConfig,
    EngineDiscoveryConfig,
)
from core.engine_registry import EngineRegistry, register_engine
from core.param_process.param_translator import ParamTranslator
from core.base_sentence_generator import BaseSentenceGenerator
from core.sentence_generator_manager import SentenceGeneratorManager
from core.engine_processor import EngineProcessor

__all__ = [
    'get_logger',
    'ScenarioToolLogger',
    'ScenarioToolError',
    'ConfigError',
    'EngineError',
    'GeneratorError',
    'TranslationError',
    'FileValidationError',
    'ExcelParseError',
    'EngineNotRegisteredError',
    'InvalidParameterError',
    'AppConfig',
    'PathConfig',
    'ProcessingConfig',
    'EngineConfig',
    'EngineDiscoveryConfig',
    'EngineRegistry',
    'register_engine',
    'ParamTranslator',
    'BaseSentenceGenerator',
    'SentenceGeneratorManager',
    'EngineProcessor',
]


def __getattr__(name):
    """Keep explicit legacy config imports lazy and optional."""
    if name in {"RenpyConfig", "NaninovelConfig", "UtageConfig"}:
        from core import config_manager

        return getattr(config_manager, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
