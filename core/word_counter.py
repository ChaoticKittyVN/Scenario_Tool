"""
统计字数模块
该模块提供用于统计文本中字数的功能。
"""
from abc import ABC, abstractmethod
import unicodedata
from typing import Dict, List, Optional, Tuple

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


class WordStyleWordCounter(WordCounter):
    """使用接近 Microsoft Word 中文文档的规则统计字数。

    中文字符逐字计数，连续的非中文文字和数字按一个词计数。空白、换行、
    控制字符和 Unicode 格式字符不计数；标点可按需逐字符计数。
    """

    def __init__(self, include_punctuation: bool = False):
        self.include_punctuation = include_punctuation

    @staticmethod
    def _is_chinese_character(character: str) -> bool:
        codepoint = ord(character)
        return (
            0x3400 <= codepoint <= 0x4DBF
            or 0x4E00 <= codepoint <= 0x9FFF
            or 0xF900 <= codepoint <= 0xFAFF
            or 0x20000 <= codepoint <= 0x2FA1F
            or 0x30000 <= codepoint <= 0x323AF
        )

    def _count_line(self, line: str) -> int:
        count = 0
        in_word = False

        for character in line:
            if self._is_chinese_character(character):
                count += 1
                in_word = False
                continue

            if character.isalnum():
                if not in_word:
                    count += 1
                    in_word = True
                continue

            in_word = False
            if self.include_punctuation and unicodedata.category(character).startswith("P"):
                count += 1

        return count

    def count(self, text: List[str]) -> int:
        total_count = 0
        for line in text:
            if line is None or pd.isna(line):
                continue
            total_count += self._count_line(str(line))
        return total_count

    def count_by(self, text: List[Tuple[str, str]]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for category, line in text:
            if line is None or pd.isna(line):
                continue
            if category is None or pd.isna(category):
                category = "unrecognized"

            category = str(category)
            counts.setdefault(category, 0)
            counts[category] += self._count_line(str(line))
        return counts
