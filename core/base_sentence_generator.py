"""
句子生成器基类模块
定义所有生成器的统一接口和通用方法
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from core.param_translator import ParamTranslator
from core.config_manager import EngineConfig
from core.logger import get_logger

logger = get_logger()


class BaseSentenceGenerator(ABC):
    """句子生成器基类 - 管道模式"""

    # 类属性 - 参数配置
    param_config: Dict[str, Dict] = {}

    def __init__(
        self,
        translator: ParamTranslator,
        engine_config: EngineConfig
    ):
        """
        初始化生成器

        Args:
            translator: 参数翻译器
            engine_config: 引擎配置
        """
        self.translator = translator
        self.engine_config = engine_config

    @property
    @abstractmethod
    def category(self) -> str:
        """
        返回生成器处理的句子类型

        Returns:
            str: 类型名称
        """
        pass

    @property
    def priority(self) -> int:
        """
        生成器执行优先级

        Returns:
            int: 优先级数字，越小越先执行
        """
        # 默认从文件名提取数字前缀
        import re
        filename = self.__class__.__module__.split('.')[-1]
        match = re.search(r'^(\d+)_', filename)
        if match:
            return int(match.group(1))
        return 999  # 没有前缀的放在最后

    @abstractmethod
    def process(self, data: Dict[str, Any]) -> Optional[List[str]]:
        """
        处理参数并生成命令（管道模式）

        Args:
            data: 参数字典

        Returns:
            Optional[List[str]]: 生成的命令列表，如果无法处理则返回 None
        """
        pass

    def can_process(self, data: Dict[str, Any]) -> bool:
        """
        判断是否可以处理给定的数据

        Args:
            data: 参数字典

        Returns:
            bool: 是否可以处理
        """
        return bool(data)

    def do_translate(self, row_data: dict) -> dict:
        """
        翻译行数据中的参数

        Args:
            row_data: 原始行数据

        Returns:
            dict: 翻译后的行数据
        """
        new_data = row_data.copy()

        for name, value in row_data.items():
            if not value:
                continue

            param_cfg = self.param_config.get(name, {})
            translate_type = param_cfg.get("translate_type")

            if translate_type:
                # 单一翻译类型
                new_value = self.translator.translate(translate_type, value)
                new_data[name] = new_value
                logger.debug(f"翻译参数 {name}: {value} -> {new_value}")

            elif param_cfg.get("translate_types", []):
                # 多个可能的翻译类型
                for trans_type in param_cfg.get("translate_types", []):
                    if self.translator.has_mapping(trans_type, value):
                        new_value = self.translator.translate(trans_type, value)
                        new_data[name] = new_value
                        logger.debug(f"翻译参数 {name}: {value} -> {new_value}")
                        break

        return new_data

    def get_int(self, num: str) -> Any:
        """
        将字符串转换为整数

        Args:
            num: 数字字符串

        Returns:
            int 或原值: 转换后的整数，如果转换失败则返回原值
        """
        num = str(num)
        try:
            return int(float(num))
        except (ValueError, TypeError):
            logger.warning(f"无法将 '{num}' 转换为整数")
            return num

    def get_format_in_config(self, name: str) -> Optional[str]:
        """
        获取参数配置中的格式字符串

        Args:
            name: 参数名

        Returns:
            Optional[str]: 格式字符串
        """
        return self.param_config.get(name, {}).get("format")

    def get_value(self, name: str, data: Dict[str, Any]) -> str:
        """
        从数据中获取参数值

        Args:
            name: 参数名
            data: 数据字典

        Returns:
            str: 参数值，如果不存在则返回空字符串
        """
        return data.get(name, "")

    def get_value_default(self, name: str, data: Dict[str, Any]) -> str:
        """
        从数据中获取参数值，如果不存在则使用默认值

        Args:
            name: 参数名
            data: 数据字典

        Returns:
            str: 参数值或默认值
        """
        if name in data:
            return str(data[name])
        elif self.param_config.get(name, {}).get("default") is not None:
            return str(self.param_config.get(name, {}).get("default"))
        else:
            return ""

    def get_sentence(self, name: str, data: Dict[str, Any]) -> str:
        """
        根据格式字符串生成句子

        Args:
            name: 参数名
            data: 数据字典

        Returns:
            str: 格式化后的句子
        """
        format_str = self.param_config.get(name, {}).get("format", "")
        if format_str:
            return format_str.format(value=data[name])
        else:
            return ""

    def get_sentence_default(self, name: str, data: dict) -> str:
        """
        根据格式字符串生成句子，使用默认值

        Args:
            name: 参数名
            data: 数据字典

        Returns:
            str: 格式化后的句子
        """
        format_str = self.param_config.get(name, {}).get("format", "")
        value = self.get_value_default(name, data)
        if value:
            return format_str.format(value=value)
        return ""

    def exists_param(self, name: str, data: Dict[str, Any]) -> bool:
        """
        检查参数是否存在

        Args:
            name: 参数名
            data: 数据字典

        Returns:
            bool: 参数是否存在
        """
        return name in data

    def __repr__(self) -> str:
        """字符串表示"""
        return f"{self.__class__.__name__}(category={self.category}, priority={self.priority})"
