# core/generator_loader.py
import importlib
import pkgutil
import inspect
from typing import List, Type
from core.base_sentence_generator import BaseSentenceGenerator

def discover_generators(engine_type: str ,format_config, translator) -> List[BaseSentenceGenerator]:
    """
    自动发现指定引擎的所有生成器
    
    Args:
        engine_type: 引擎类型，如 "renpy"
        
    Returns:
        List[BaseSentenceGenerator]: 生成器实例列表，按类名排序
    """
    generators = []
    
    # 构建生成器包路径
    generators_package = f"engines.{engine_type}.sentence_generators"
    
    try:
        # 导入生成器包
        package = importlib.import_module(generators_package)
        
        print(f"正在发现 {generators_package} 中的生成器...")
        
        # 遍历包中的所有模块
        for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
            if is_pkg:
                continue  # 跳过子包
                
            # 只处理以 _generator 结尾的模块
            if not module_name.endswith('_generator'):
                continue
                
            try:
                # 导入生成器模块
                full_module_name = f"{generators_package}.{module_name}"
                module = importlib.import_module(full_module_name)
                
                # 查找所有继承自 BaseSentenceGenerator 的类
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, BaseSentenceGenerator) and 
                        obj != BaseSentenceGenerator and
                        obj.__module__ == module.__name__):
                        
                        # 创建生成器实例
                        generator = obj(format_config, translator)
                        generators.append(generator)
                        print(f"发现生成器: {name}")
                        
            except Exception as e:
                print(f"导入模块 {module_name} 时出错: {e}")
                continue
                
    except ImportError as e:
        print(f"导入生成器包 {generators_package} 时出错: {e}")
        return []
    
    # 按类名排序，确保执行顺序一致
    generators.sort(key=lambda g: g.priority)
    
    print(f"共发现 {len(generators)} 个生成器，执行顺序:")
    for i, generator in enumerate(generators, 1):
        print(f"  {i}. {generator.__class__.__name__} (优先级: {generator.priority})")
    
    return generators