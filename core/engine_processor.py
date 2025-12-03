"""
引擎处理器模块
基于管道模式的协调器，负责协调数据在生成器管道中的流动
"""
from typing import List, Dict, Any
import pandas as pd
from core.sentence_generator_manager import SentenceGeneratorManager
from core.param_translator import ParamTranslator
from core.config_manager import EngineConfig
from core.logger import get_logger
from core.excel_management.dataframe_processor import DataFrameProcessor

logger = get_logger()


class EngineProcessor:
    """
    引擎处理器 - 基于管道模式的协调器

    职责：
    1. 管理生成器管道（固定顺序）
    2. 协调数据在管道中的流动
    3. 处理异常和日志
    """

    def __init__(
        self,
        engine_type: str,
        translator: ParamTranslator,
        engine_config: EngineConfig
    ):
        """
        初始化管道处理器

        Args:
            engine_type: 引擎类型
            translator: 参数翻译器
            engine_config: 引擎配置
        """
        self.engine_type = engine_type
        self.translator = translator
        self.engine_config = engine_config
        self.generators = []
        self.generator_param_map = {}

        # 初始化生成器管理器
        self.generator_manager = SentenceGeneratorManager(engine_type)
        self.generator_manager.load()

        # DataFrame处理器
        self.df_processor = DataFrameProcessor(engine_config)

        logger.info(f"引擎处理器初始化: {engine_type}")

    def setup(self):
        """设置处理器，初始化生成器和参数提取器"""

        # 通过生成器管理器创建生成器实例
        self.generators = self.generator_manager.create_generator_instances(
            self.translator,
            self.engine_config
        )

        self.generator_param_map = self._build_generator_param_map()
        logger.info(f"引擎处理器设置完成，共 {len(self.generators)} 个生成器")

    def _build_generator_param_map(self) -> Dict:
        """构建generator到参数的映射"""
        generator_param_map = {}
        for generator in self.generators:
            params = []
            generator_params = getattr(generator, "param_config", {}) or {}
            generator_params_keys = (
                generator_params.keys()
                if isinstance(generator_params, dict)
                else generator_params
            )

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
        results = []

        # 使用DataFrameProcessor提取所有生成器需要的参数

        generator_params = {}

        for generator, needed_params in self.generator_param_map.items():
            params = self.df_processor.extract_parameters(row_data, needed_params)
            if params:
                generator_params[generator] = params

        for generator, params in generator_params.items():
            # 原有的管道处理逻辑
            if params:
                try:
                    commands = generator.process(params)
                    if commands:
                        results.extend(commands)
                        logger.debug(
                            f"{generator.__class__.__name__} 生成了 "
                            f"{len(commands)} 条命令"
                        )
                except Exception as e:
                    logger.error(
                        f"{generator.__class__.__name__} 处理失败: {e}",
                        exc_info=True
                    )

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
                "type": getattr(generator, 'category', 'unknown'),
                "priority": generator.priority
            }
            info["pipeline"].append(stage_info)

        return info

    def get_generator_manager(self) -> SentenceGeneratorManager:
        """获取生成器管理器实例"""
        return self.generator_manager
