# core/sentence_generator_manager.py
import importlib
import pkgutil
import inspect
from typing import List, Dict, Set, Type

class SentenceGeneratorManager:
    """
    句子生成器管理器 - 静态配置收集器
    无需实例化即可获取所有参数配置
    """

    def __init__(self, engine_type: str):
        self.engine_type = engine_type
        self.generator_classes = []  # 生成器类列表
        self.param_configs = {}      # 参数配置字典
        self._loaded = False

    def load(self):
        """加载所有生成器类和参数配置"""
        if self._loaded:
            return

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

                    # 查找所有继承自 BaseSentenceGenerator 的类
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if (self._is_generator_class(obj) and
                            obj.__module__ == module.__name__):

                            self.generator_classes.append(obj)

                except Exception as e:
                    print(f"导入模块 {module_name} 时出错: {e}")
                    continue

        except ImportError as e:
            print(f"导入生成器包 {generators_package} 时出错: {e}")

    def _is_generator_class(self, obj):
        """检查是否为有效的生成器类"""
        from core.base_sentence_generator import BaseSentenceGenerator
        return (issubclass(obj, BaseSentenceGenerator) and
                obj != BaseSentenceGenerator)

    def _collect_param_configs(self):
        """收集所有生成器的参数配置（不实例化）"""
        total_params = 0
        for generator_class in self.generator_classes:
            # 通过类属性获取 param_config
            param_config = getattr(generator_class, 'param_config', {})
            if param_config and isinstance(param_config, dict):
                self.param_configs.update(param_config)
                total_params += len(param_config)
                # print(f"收集参数配置 from {generator_class.__name__}: {list(param_config.keys())}")
        # 只输出总结信息，不输出每个生成器的详情
        print(f"从 {len(self.generator_classes)} 个生成器收集了 {total_params} 个参数配置")

    def get_all_param_names(self) -> List[str]:
        """获取所有参数名称"""
        self.load()
        return sorted(list(self.param_configs.keys()))

    def get_translatable_param_names(self) -> List[str]:
        """获取需要翻译的参数名称"""
        self.load()

        translatable_params = []
        for param_name, config in self.param_configs.items():
            if config.get('translate_type') or config.get('translate_types'):
                translatable_params.append(param_name)

        return sorted(translatable_params)

    def get_generator_param_mapping(self) -> Dict[Type, List[str]]:
        """获取生成器与参数的映射关系"""
        self.load()

        mapping = {}
        for generator_class in self.generator_classes:
            param_config = getattr(generator_class, 'param_config', {})
            param_names = list(param_config.keys()) if param_config else []
            mapping[generator_class] = param_names

        return mapping

    def create_generator_instances(self, translator):
        """创建生成器实例（用于 engine_processor）"""
        self.load()

        instances = []
        for generator_class in self.generator_classes:
            try:
                instance = generator_class(translator)
                instances.append(instance)
            except Exception as e:
                print(f"创建 {generator_class.__name__} 实例失败: {e}")

        # 按优先级排序
        instances.sort(key=lambda g: getattr(g, 'priority', 0))

        print(f"共发现 {len(instances)} 个生成器，执行顺序:")
        for i, generator in enumerate(instances, 1):
            print(f"  {i}. {generator.__class__.__name__} (优先级: {generator.priority})")

        return instances

    def get_generator_info(self) -> Dict:
        """获取生成器信息（用于调试）"""
        self.load()

        info = {
            "engine_type": self.engine_type,
            "generator_count": len(self.generator_classes),
            "param_count": len(self.param_configs),
            "generators": [],
            "translatable_params": self.get_translatable_param_names()
        }

        for generator_class in self.generator_classes:
            generator_info = {
                "name": generator_class.__name__,
                "category": getattr(generator_class, 'category', 'unknown'),
                "priority": getattr(generator_class, 'priority', 0),
                "param_count": len(getattr(generator_class, 'param_config', {}))
            }
            info["generators"].append(generator_info)

        return info

    def get_param_config(self, param_name: str) -> Dict:
        """获取特定参数的配置"""
        self.load()
        return self.param_configs.get(param_name, {})

    def get_translate_type(self, param_name: str) -> str:
        """获取参数的翻译类型（translate_type）"""
        config = self.get_param_config(param_name)
        return config.get('translate_type', param_name)

    def get_translate_types(self, param_name: str) -> List[str]:
        """获取参数的所有翻译类型"""
        config = self.get_param_config(param_name)
        
        translate_types = []
        if 'translate_type' in config:
            translate_types.append(config['translate_type'])
        elif 'translate_types' in config:
            translate_types.extend(config['translate_types'])
        else:
            translate_types.append(param_name)
        
        return translate_types