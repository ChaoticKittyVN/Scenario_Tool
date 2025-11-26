"""
统计字数模块
该模块提供用于统计文本中字数的功能。
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Tuple, Dict, Any, Optional, Callable
from core.text_processor import TextProcessor, PunctuationFilter
import pandas as pd

class WordCounter(ABC):
    """
    字数统计器基类
    定义字数统计的统一接口
    """

    @abstractmethod
    def count(self, text: List[str]) -> int:
        """
        统计文本中的字数

        Args:
            text: 输入文本列表

        Returns:
            int: 统计的字数
        """
        pass

    @abstractmethod
    def count_by(self, text: List[Tuple[str, str]]) -> Dict[str, int]:
        """
        按类别统计文本中的字数

        Args:
            text: 输入文本列表，每个元素为 (类别, 文本) 元组

        Returns:
            Dict[str, int]: 每个类别对应的字数统计结果
        """
        pass

class BasicWordCounter(WordCounter):
    """
    最基础的字数统计器
    实现了基本的字数统计功能，支持按类别统计
    统计字数时默认会使用 PunctuationFilter 过滤标点符号，可选传入自定义的文本处理器
    """

    def __init__(self, filter: Optional[TextProcessor] = None):
        """
        初始化字数统计器

        Args:
            filter: 可选的文本处理器，用于在统计前处理文本，默认使用 PunctuationFilter 过滤标点符号
        """
        self.filter = filter if filter is not None else PunctuationFilter()

    def count(self, text: List[str]) -> int:
        """
        统计文本中的字数

        Args:
            text: 输入文本列表

        Returns:
            int: 统计的字数
        """
        total_count = 0
        for line in text:
            if line is None or pd.isna(line): # 跳过空行
                continue

            line = str(line) # 确保 line 是字符串类型
            processed_line = self.filter(line) if self.filter else line
            total_count += len(processed_line)
        
        return total_count
    
    def count_by(self, text: List[Tuple[str, str]]) -> Dict[str, int]:
        """
        按类别统计文本中的字数

        Args:
            text: 输入文本列表，每个元素为 (类别, 文本) 元组

        Returns:
            Dict[str, int]: 每个类别对应的字数统计结果
        """
        counts: Dict[str, int] = {}
        for category, line in text:
            if category is None or pd.isna(category):
                category = "unrecognized"

            if line is None or pd.isna(line): # 跳过空行
                continue

            category = str(category) # 确保 category 是字符串类型
            line = str(line) # 确保 line 是字符串类型
            processed_line = self.filter(line) if self.filter else line
            line_count = len(processed_line)
            counts.setdefault(category, 0)
            counts[category] += line_count

        return counts