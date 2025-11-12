# core/engine_processor.py
from typing import List, Dict, Any
import pandas as pd

class EngineProcessor:
    """
    引擎处理器 - 基于管道模式的协调器
    
    职责：
    1. 管理生成器管道（固定顺序）
    2. 协调数据在管道中的流动
    3. 处理异常和日志
    """
    
    def __init__(self, generators: List, translator, context_manager):
        """
        初始化管道处理器
        
        Args:
            generators: 生成器列表，按执行顺序排列
            translator: 参数翻译器
            context_manager: 上下文管理器
        """
        self.generators = generators  # 管道中的各个处理器
        self.translator = translator
        self.context = context_manager
        self.format_config = {} # 稍后初始化

    def _build_generator_param_map(self):
        """构建generator到参数的映射"""
        generator_param_map = {}
        for generator in self.generators:
            # category = generator.category
            # category_params = []
            # for param_name, config in self.format_config.items():
            #     if config.get("category") == category:
            #         category_params.append(param_name)
            # generator_param_map[category] = category_params
            params = []
            # generator.param_config 期望为 dict 或可迭代的键集合
            generator_params = getattr(generator, "param_config", {}) or {}
            generator_params_keys = generator_params.keys() if isinstance(generator_params, dict) else generator_params
            for name in self.format_config.keys():
                if name in generator_params_keys:
                    params.append(name)
            generator_param_map[generator] = params

        return generator_param_map

    def setup(self, format_config: Dict):
        """设置处理器，初始化参数提取器"""
        self.format_config = format_config
        self.generator_param_map = self._build_generator_param_map()
        
    def process_row(self, row_data: pd.Series) -> List[str]:
        """
        处理单行数据 - 管道模式
        
        Args:
            row_data: pandas Series，一行的所有数据
            
        Returns:
            List[str]: 生成的命令列表
        """
        row_dict = row_data.to_dict()
        results = []

        for generator in self.generators:
            needed_params = self.generator_param_map.get(generator, [])
            params = {}

            # 只提取这个generator需要的参数
            for param_name in needed_params:
                if param_name in row_dict:
                    value = row_dict[param_name]
                    if not (pd.isna(value) or value == ""):
                        params[param_name] = value

            # 原有的管道处理逻辑
            if params:
                commands = generator.process(params)
                if commands:
                    results.extend(commands)

        return results

    def get_pipeline_info(self) -> Dict[str, Any]:
        """获取管道信息，用于调试"""
        info = {
            "total_stages": len(self.generators),
            "pipeline": []
        }
        
        for i, generator in enumerate(self.generators):
            stage_info = {
                "stage": i + 1,
                "name": generator.__class__.__name__,
                "type": getattr(generator, 'category', 'unknown')
            }
            info["pipeline"].append(stage_info)
            
        return info
    
    