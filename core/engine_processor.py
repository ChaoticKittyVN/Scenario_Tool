# core/engine_processor.py
from typing import List, Dict, Any
from .param_extractor import ParamExtractor
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
        self.extractor = None  # 稍后初始化
        
    def setup(self, format_config: Dict):
        """设置处理器，初始化参数提取器"""
        self.extractor = ParamExtractor(format_config)
        
    def process_row(self, row_data: pd.Series) -> List[str]:
        """
        处理单行数据 - 管道模式
        
        Args:
            row_data: pandas Series，一行的所有数据
            
        Returns:
            List[str]: 生成的命令列表
        """
        if not self.extractor:
            raise RuntimeError("Processor not setup. Call setup() first.")
            
        results = []
        
        # try:
        # 1. 提取参数（管道入口）
        grouped_params = self.extractor.extract_single_row(row_data)
        
        # 2. 通过管道传递数据
        current_params = grouped_params
        # current_context = self.context
        
        for generator in self.generators:
            # 每个生成器处理数据并可能修改上下文
            commands = generator.process(current_params.get(generator.category))
            if commands:
                results.extend(commands)
        
        return results
            
        # except Exception as e:
        #     print(f"处理行数据时出错: {e}")
        #     return []
    
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
    
    