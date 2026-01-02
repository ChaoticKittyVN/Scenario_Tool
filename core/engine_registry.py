"""
引擎注册表模块
实现引擎的动态注册和管理
"""
from typing import Dict, Type, Optional, Callable
from dataclasses import dataclass
from core.config_manager import EngineConfig
from core.logger import get_logger
from core.exceptions import EngineNotRegisteredError

logger = get_logger()


@dataclass
class EngineMetadata:
    """引擎元数据"""
    name: str
    display_name: str
    file_extension: str
    config_class: Type[EngineConfig]  # 引擎配置类，通常定义在各自的引擎模块中（如 engines.renpy.config.RenpyConfig）
    processor_factory: Callable
    validator_factory: Optional[Callable] = None
    description: str = ""


class EngineRegistry:
    """引擎注册表（单例模式）"""

    _instance: Optional['EngineRegistry'] = None
    _engines: Dict[str, EngineMetadata] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, metadata: EngineMetadata):
        """
        注册引擎

        Args:
            metadata: 引擎元数据
        """
        instance = cls()
        if metadata.name in instance._engines:
            logger.warning(f"引擎 '{metadata.name}' 已存在，将被覆盖")
        instance._engines[metadata.name] = metadata
        logger.info(f"注册引擎: {metadata.display_name} ({metadata.name})")

    @classmethod
    def get(cls, engine_name: str) -> EngineMetadata:
        """
        获取引擎元数据

        Args:
            engine_name: 引擎名称

        Returns:
            EngineMetadata: 引擎元数据

        Raises:
            EngineNotRegisteredError: 引擎未注册
        """
        instance = cls()
        if engine_name not in instance._engines:
            raise EngineNotRegisteredError(f"引擎 '{engine_name}' 未注册")
        return instance._engines[engine_name]

    @classmethod
    def list_engines(cls) -> Dict[str, EngineMetadata]:
        """
        列出所有已注册引擎

        Returns:
            Dict[str, EngineMetadata]: 引擎字典
        """
        instance = cls()
        return instance._engines.copy()

    @classmethod
    def is_registered(cls, engine_name: str) -> bool:
        """
        检查引擎是否已注册

        Args:
            engine_name: 引擎名称

        Returns:
            bool: 是否已注册
        """
        instance = cls()
        return engine_name in instance._engines

    @classmethod
    def reset(cls):
        """重置注册表（主要用于测试）"""
        instance = cls()
        instance._engines.clear()
        logger.debug("引擎注册表已重置")


def register_engine(
    name: str,
    display_name: str,
    file_extension: str,
    config_class: Type[EngineConfig],
    validator_factory: Optional[Callable] = None,
    description: str = ""
):
    """
    引擎注册装饰器

    Args:
        name: 引擎名称
        display_name: 显示名称
        file_extension: 文件扩展名
        config_class: 配置类，必须继承自 EngineConfig。
                     通常定义在各自的引擎模块中（如 engines.renpy.config.RenpyConfig）
        validator_factory: 验证器工厂函数（可选）
        description: 引擎描述（可选）

    Returns:
        装饰器函数

    Example:
        ```python
        from engines.renpy.config import RenpyConfig
        
        @register_engine(
            name="renpy",
            display_name="Ren'Py",
            file_extension=".rpy",
            config_class=RenpyConfig,
            description="Ren'Py 视觉小说引擎"
        )
        def create_renpy_processor(config: RenpyConfig, translator):
            # ...
        ```
    """
    def decorator(processor_factory: Callable):
        metadata = EngineMetadata(
            name=name,
            display_name=display_name,
            file_extension=file_extension,
            config_class=config_class,
            processor_factory=processor_factory,
            validator_factory=validator_factory,
            description=description
        )
        EngineRegistry.register(metadata)
        return processor_factory
    return decorator