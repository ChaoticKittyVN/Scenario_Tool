"""
句子生成器管理器模块
负责发现、加载和管理引擎特定的生成器
"""
import importlib
import pkgutil
import inspect
from typing import List, Dict, Type
from core.base_sentence_generator import BaseSentenceGenerator
from core.param_translator import ParamTranslator
from core.config_manager import EngineConfig
from core.logger import get_logger
from core.exceptions import GeneratorError

logger = get_logger()


class SentenceGeneratorManager:
    """句子生成器管理器"""

    def __init__(self, engine_type: str):
        self.engine_type = engine_type
        self.generator_classes: List[Type[BaseSentenceGenerator]] = []
        self.param_configs: Dict = {}
        self._loaded = False

    def load(self):
        """加载所有生成器类和参数配置"""
        if self._loaded:
            return
        logger.info(f"开始加载 {self.engine_type} 引擎的生成器")
        self._discover_generator_classes()
        self._collect_param_configs()
        self._loaded = True

    def _discover_generator_classes(self):
        """发现指定引擎的所有生成器类"""
        generators_package = f"engines.{self.engine_type}.sentence_generators"
        try:
            package = importlib.import_module(generators_package)
            for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
                if is_pkg or not module_name.endswith('_generator'):
                    continue
                try:
                    full_module_name = f"{generators_package}.{module_name}"
                    module = importlib.import_module(full_module_name)
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if (self._is_generator_class(obj) and
                                obj.__module__ == module.__name__):
                            self.generator_classes.append(obj)
                            logger.debug(f"发现生成器: {obj.__name__}")
                except Exception as e:
                    logger.error(f"导入模块 {module_name} 时出错: {e}")
        except ImportError as e:
            logger.error(f"导入生成器包 {generators_package} 时出错: {e}")
            raise GeneratorError(f"无法加载引擎 {self.engine_type} 的生成器") from e

    def _is_generator_class(self, obj) -> bool:
        """检查是否为有效的生成器类"""
        try:
            return (inspect.isclass(obj) and
                    issubclass(obj, BaseSentenceGenerator) and
                    obj != BaseSentenceGenerator)
        except TypeError:
            return False

    def _collect_param_configs(self):
        """收集所有生成器的参数配置"""
        total_params = 0
        for generator_class in self.generator_classes:
            param_config = getattr(generator_class, 'param_config', {})
            if param_config and isinstance(param_config, dict):
                self.param_configs.update(param_config)
                total_params += len(param_config)
        logger.info(f"从 {len(self.generator_classes)} 个生成器收集了 {total_params} 个参数配置")

    def create_generator_instances(
        self,
        translator: ParamTranslator,
        engine_config: EngineConfig
    ) -> List[BaseSentenceGenerator]:
        """创建生成器实例"""
        self.load()
        instances = []
        for generator_class in self.generator_classes:
            try:
                instance = generator_class(translator, engine_config)
                instances.append(instance)
            except Exception as e:
                logger.error(f"创建 {generator_class.__name__} 实例失败: {e}")
        instances.sort(key=lambda g: g.priority)
        logger.info(f"共创建 {len(instances)} 个生成器")
        for i, generator in enumerate(instances, 1):
            logger.info(f"  {i}. {generator.__class__.__name__} (优先级: {generator.priority})")
        return instances

    def get_all_param_names(self) -> List[str]:
        """获取所有参数名称"""
        self.load()
        return sorted(list(self.param_configs.keys()))

    def get_all_translate_types(self) -> List[str]:
        """
        收集所有参数配置中的translate_type值
        
        Returns:
            List[str]: 去重后的translate_type列表
        """
        translate_types = set()
        self.load()
        for generator_class in self.generator_classes:
            param_config = getattr(generator_class, 'param_config', {})
            
            if param_config and isinstance(param_config, dict):
                for param_name, config in param_config.items():
                    if isinstance(config, dict) and "translate_type" in config:
                        translate_type = config["translate_type"]
                        if translate_type:
                            translate_types.add(translate_type)
        
        # 转换为排序后的列表
        result = sorted(list(translate_types))
        logger.info(f"收集到 {len(result)} 个不同的 translate_type: {result}")
        return result
