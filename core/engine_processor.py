"""
引擎处理器模块
基于管道模式的协调器，负责协调数据在生成器管道中的流动
"""
from typing import List, Dict, Any
import pandas as pd
from core.sentence_generator_manager import SentenceGeneratorManager
from core.param_process.param_translator import ParamTranslator
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
        engine_config: EngineConfig,
        generator_categories: List[str] = []
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

        self.generator_categories = generator_categories
        self.generators = []
        self.generator_param_map = {}

        # 初始化生成器管理器
        self.generator_manager = SentenceGeneratorManager(engine_type)
        self.generator_manager.load()

        # DataFrame处理器
        self.df_processor = DataFrameProcessor(engine_config)

        logger.info(f"引擎处理器初始化: {engine_type}")

    @staticmethod
    def _is_empty_value(value: Any) -> bool:
        """识别缺失值；纯空格字符串仍视为有效参数。"""
        if value is None:
            return True
        if isinstance(value, str) and value == "":
            return True
        try:
            missing = pd.isna(value)
            return bool(missing)
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _run_generator(generator, params: Dict[str, Any]) -> list:
        """执行单个生成器，并隔离该生成器自身的异常。"""
        try:
            commands = generator.process(params)
            return list(commands) if commands else []
        except Exception as exc:
            logger.error(
                f"生成器 {generator.__class__.__name__} 处理失败: {exc}",
                exc_info=True,
            )
            return []

    def setup(self):
        """设置处理器，初始化生成器和参数提取器"""

        # 通过生成器管理器创建生成器实例
        all_generators = self.generator_manager.create_generator_instances(
            self.translator,
            self.engine_config
        )
        # 根据类别过滤
        if self.generator_categories:
            self.generators = [
                g for g in all_generators 
                if getattr(g, 'category', '') in self.generator_categories
            ]
        else:
            self.generators = all_generators

        self.generator_param_map = self._build_generator_param_map()
        logger.info(f"引擎处理器设置完成，共 {len(self.generators)} 个生成器")
        if self.generator_categories:
            logger.info(f"已过滤，仅保留类别: {self.generator_categories}")
    def _build_generator_param_map(self) -> Dict:
        """构建generator到参数的映射"""
        generator_param_map = {}
        for generator in self.generators:
            # 检查是否有特殊标记：接收所有参数（用于Macro生成器）
            if getattr(generator, 'RECEIVE_ALL_PARAMS', False):
                generator_param_map[generator] = None  # None表示接收所有参数
                continue
            
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

    def has_exclusive_generator(self, row_data: pd.Series) -> bool:
        """
        检查行数据是否包含独占模式生成器需要处理的参数
        
        Args:
            row_data: pandas Series，一行的所有数据
            
        Returns:
            bool: 如果包含独占模式生成器需要的参数且值不为空，返回True
        """
        if self.engine_type != "utage":
            return False

        row_dict = row_data.to_dict()

        # 检查是否有任何独占模式生成器需要处理的参数
        for generator in self.generators:
            if getattr(generator, 'EXCLUSIVE_MODE', False):
                # 检查生成器的参数配置
                if hasattr(generator, 'param_config'):
                    for param_name in generator.param_config.keys():
                        if (
                            param_name in row_dict
                            and not self._is_empty_value(row_dict[param_name])
                        ):
                            return True

        return False

    def _find_exclusive_generator(self):
        """
        查找独占模式生成器实例
        
        Returns:
            独占模式生成器实例，如果不存在则返回None
        """
        if self.engine_type != "utage":
            return None

        for generator in self.generators:
            if (getattr(generator, 'EXCLUSIVE_MODE', False) or
                getattr(generator, 'RECEIVE_ALL_PARAMS', False)):
                return generator
        return None

    def process_exclusive_row(self, row_data: pd.Series) -> List[str] | List[Dict[str, Any]] | None:
        """
        独占模式处理流程（仅用于utage引擎）
        
        处理逻辑：
        1. 优先处理独占模式生成器（接收所有非空参数）
        2. 只处理标记为ALLOWED_WITH_EXCLUSIVE的生成器
        3. 其他生成器全部跳过
        
        Args:
            row_data: pandas Series，一行的所有数据
            
        Returns:
            List[str] | List[Dict[str, Any]]: 生成的命令列表
        """
        if self.engine_type != "utage":
            # 非utage引擎不应该调用此方法，降级为普通处理
            return self.process_row(row_data)
        
        results = []
        row_dict = row_data.to_dict()
        
        # 查找独占模式生成器
        exclusive_generator = self._find_exclusive_generator()
        if not exclusive_generator:
            logger.warning("未找到独占模式生成器，但检测到独占指令，降级为普通处理")
            return self.process_row(row_data)
        
        # 1. 处理独占模式生成器（接收所有参数）
        exclusive_params = {
            key: value
            for key, value in row_dict.items()
            if not self._is_empty_value(value)
        }
        if exclusive_params:
            results.extend(self._run_generator(exclusive_generator, exclusive_params))
        
        # 2. 处理允许与独占模式生成器一起处理的生成器
        for generator, needed_params in self.generator_param_map.items():
            # 跳过独占模式生成器本身
            if generator == exclusive_generator:
                continue
            
            # 只处理标记为ALLOWED_WITH_EXCLUSIVE的生成器
            if not getattr(generator, 'ALLOWED_WITH_EXCLUSIVE', False):
                continue
            
            # 提取该生成器需要的参数
            if needed_params is None:
                # 接收所有参数的生成器
                generator_params = {
                    key: value
                    for key, value in row_dict.items()
                    if not self._is_empty_value(value)
                }
            else:
                # 只提取需要的参数
                generator_params = {}
                for param_name in needed_params:
                    if param_name in row_dict:
                        value = row_dict[param_name]
                        if not self._is_empty_value(value):
                            generator_params[param_name] = value
            
            if generator_params:
                results.extend(self._run_generator(generator, generator_params))
        
        return results

    def process_row(self, row_data: pd.Series) -> List[str] | List[Dict[str, Any]] | None:
        """
        处理单行数据 - 管道模式

        Args:
            row_data: pandas Series，一行的所有数据

        Returns:
            List[str] | List[Dict[str, Any]]: 生成的命令列表
        """
        # 对于utage引擎，检查是否需要独占模式处理
        if self.engine_type == "utage":
            if self.has_exclusive_generator(row_data):
                return self.process_exclusive_row(row_data)

        # 原有的普通处理逻辑
        results = []
        row_dict = row_data.to_dict()

        for generator, needed_params in self.generator_param_map.items():
            # 处理接收所有参数的生成器（如Macro生成器）
            if needed_params is None:
                # 接收所有非空参数
                generator_params = {
                    key: value
                    for key, value in row_dict.items()
                    if not self._is_empty_value(value)
                }
                if generator_params:
                    results.extend(self._run_generator(generator, generator_params))
                continue
            
            # 快速检查：这个generator需要的参数是否存在于行数据中
            if not any(param in row_dict for param in needed_params):
                continue
            
            # 只提取这个generator需要的参数
            generator_params = {}
            for param_name in needed_params:
                if param_name in row_dict:
                    value = row_dict[param_name]
                    if not self._is_empty_value(value):
                        generator_params[param_name] = value
            
            if generator_params:
                results.extend(self._run_generator(generator, generator_params))

        return results

    def has_macro(self, row_data: pd.Series) -> bool:
        """
        检查行数据中是否包含Macro指令（仅用于utage引擎）
        
        Args:
            row_data: pandas Series，一行的所有数据
            
        Returns:
            bool: 如果包含Macro指令且值不为空，返回True
        """
        if self.engine_type != "utage":
            return False
        
        row_dict = row_data.to_dict()
        return "Macro" in row_dict and not self._is_empty_value(row_dict.get("Macro"))

    def _find_macro_generator(self):
        """
        查找Macro生成器实例（仅用于utage引擎）
        
        Returns:
            Macro生成器实例，如果不存在则返回None
        """
        if self.engine_type != "utage":
            return None
        
        for generator in self.generators:
            if (getattr(generator, 'EXCLUSIVE_MODE', False) and 
                getattr(generator, 'RECEIVE_ALL_PARAMS', False)):
                return generator
        return None

    def process_macro_row(self, row_data: pd.Series) -> List[str] | List[Dict[str, Any]] | None:
        """
        Macro专用处理流程（仅用于utage引擎）
        
        处理逻辑：
        1. 优先处理Macro生成器（接收所有非空参数）
        2. 只处理标记为ALLOWED_WITH_MACRO的生成器（如Text相关）
        3. 其他生成器全部跳过
        
        Args:
            row_data: pandas Series，一行的所有数据
            
        Returns:
            List[str] | List[Dict[str, Any]]: 生成的命令列表
        """
        if self.engine_type != "utage":
            # 非utage引擎不应该调用此方法，降级为普通处理
            return self.process_row(row_data)
        
        results = []
        row_dict = row_data.to_dict()
        
        # 查找Macro生成器
        macro_generator = self._find_macro_generator()
        if not macro_generator:
            logger.warning("未找到Macro生成器，但检测到Macro指令，降级为普通处理")
            return self.process_row(row_data)
        
        # 1. 处理Macro生成器（接收所有参数）
        macro_params = {
            key: value
            for key, value in row_dict.items()
            if not self._is_empty_value(value)
        }
        if macro_params:
            results.extend(self._run_generator(macro_generator, macro_params))
        
        # 2. 处理允许与Macro一起处理的生成器
        for generator, needed_params in self.generator_param_map.items():
            # 跳过Macro生成器本身
            if generator == macro_generator:
                continue
            
            # 只处理标记为ALLOWED_WITH_MACRO的生成器
            if not getattr(generator, 'ALLOWED_WITH_MACRO', False):
                continue
            
            # 提取该生成器需要的参数
            if needed_params is None:
                # 接收所有参数的生成器
                generator_params = {
                    key: value
                    for key, value in row_dict.items()
                    if not self._is_empty_value(value)
                }
            else:
                # 只提取需要的参数
                generator_params = {}
                for param_name in needed_params:
                    if param_name in row_dict:
                        value = row_dict[param_name]
                        if not self._is_empty_value(value):
                            generator_params[param_name] = value
            
            if generator_params:
                results.extend(self._run_generator(generator, generator_params))
        
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
