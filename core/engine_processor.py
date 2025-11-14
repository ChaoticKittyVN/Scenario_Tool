# core/engine_processor.py
from typing import List, Dict, Any
import pandas as pd
from core.sentence_generator_manager import SentenceGeneratorManager

class EngineProcessor:
    """
    引擎处理器 - 基于管道模式的协调器
    
    职责：
    1. 管理生成器管道（固定顺序）
    2. 协调数据在管道中的流动
    3. 处理异常和日志
    """
    
    def __init__(self, engine_type: str, translator):
        """
        初始化管道处理器
        
        Args:
            engine_type: 引擎类型
            translator: 参数翻译器
            context_manager: 上下文管理器
        """
        self.engine_type = engine_type
        self.translator = translator
        # self.context = context_manager
        self.generators = []
        self.generator_param_map = {}
        
        # 初始化生成器管理器
        self.generator_manager = SentenceGeneratorManager(engine_type)
        self.generator_manager.load()

    def setup(self):
        """设置处理器，初始化生成器和参数提取器"""
        
        # 通过生成器管理器创建生成器实例
        self.generators = self.generator_manager.create_generator_instances(
            self.translator
        )
        
        self.generator_param_map = self._build_generator_param_map()
        
    def _build_generator_param_map(self):
        """构建generator到参数的映射"""
        generator_param_map = {}
        for generator in self.generators:
            params = []
            generator_params = getattr(generator, "param_config", {}) or {}
            generator_params_keys = generator_params.keys() if isinstance(generator_params, dict) else generator_params

            for name in generator_params_keys:
                params.append(name)
            generator_param_map[generator] = params

        return generator_param_map

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

    def get_generator_manager(self) -> SentenceGeneratorManager:
        """获取生成器管理器实例"""
        return self.generator_manager