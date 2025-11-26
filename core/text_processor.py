"""
文本处理器模块
该模块提供用于文本处理的各种接口，可用于过滤和清理等功能
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Any, Optional, Callable
import re


class TextProcessor(ABC):
    """
    文本处理器基类 - 管道模式
    通过自定义规则对文本进行处理，输入文本，输出过滤后的文本
    """

    @abstractmethod
    def process(self, text: str) -> str:
        """
        处理输入文本

        Args:
            text: 输入文本

        Returns:
            str: 处理后的文本
        """
        pass

    def __call__(self, text: str) -> str:
        """
        使处理器实例可调用，默认调用 process 方法

        Args:
            text: 输入文本

        Returns:
            str: 处理后的文本
        """
        return self.process(text)
    

class IdentityTextProcessor(TextProcessor):
    """
    元文本处理器
    不对文本进行任何处理，直接返回输入文本
    """

    def process(self, text: str) -> str:
        """
        返回输入文本

        Args:
            text: 输入文本

        Returns:
            str: 输入文本
        """
        return text
    

class RegexExtractor(TextProcessor):
    """
    正则表达式提取器
    使用正则表达式从文本中提取匹配的部分
    """

    def __init__(self, pattern: str, get_result: Callable = lambda match: match.group(), delimiter: str = '', flags: int = 0):
        """
        初始化提取器

        Args:
            pattern: 正则表达式模式
            get_result: 从匹配对象中提取结果的函数，默认为返回整个匹配
            delimiter: 提取结果的分隔符，默认为空字符串
            flags: 正则表达式标志，默认为0
        """
        self.pattern = re.compile(pattern, flags)
        self.get_result = get_result
        self.delimiter = delimiter

    def process(self, text: str) -> str:
        """
        使用正则表达式提取文本

        Args:
            text: 输入文本

        Returns:
            str: 提取后的文本
        """
        matches = self.pattern.finditer(text)
        extracted = [self.get_result(match) for match in matches]
        return self.delimiter.join(extracted)
    

class SimpleDialogueContentExtractor(TextProcessor):
    """
    对话内容提取器
    假设对话内容以 `「` 和 `」` 包围，提取其中的内容
    """

    def process(self, text: str) -> str:
        """
        提取对话内容

        Args:
            text: 输入文本

        Returns:
            str: 提取后的对话内容
        """
        state: int = 0 # 表示目前的嵌套层数
        result: str = ''

        for token in text:
            if token == '」': # 遇到右引号，嵌套层数减一
                state -= 1

            if state > 0: # 在对话内容内
                result += token

            if token == '「': # 遇到左引号，嵌套层数加一
                state += 1
        
        return result
    

class ChineseExtractor(TextProcessor):
    """
    中文字符提取器
    提取文本中的所有中文字符
    """

    def process(self, text: str) -> str:
        """
        提取中文字符

        Args:
            text: 输入文本

        Returns:
            str: 提取后的中文字符
        """
        pattern = re.compile(r'[\u4e00-\u9fff]+')
        matches = pattern.findall(text)
        return ''.join(matches)
    

class PunctuationFilter(TextProcessor):
    """
    标点符号过滤器
    过滤文本中的所有标点符号和空格
    """

    def __init__(self, punctuations: Optional[str] = None):
        """
        初始化过滤器

        Args:
            punctuations: 要过滤的标点符号字符串，默认为所有非字母数字字符和空格
        """
        if punctuations is not None:
            escaped_punctuations = re.escape(punctuations)
            self.pattern = re.compile(f'[{escaped_punctuations}]')
        else:
            self.pattern = re.compile(r'[^\w]', re.UNICODE)

    def process(self, text: str) -> str:
        """
        过滤标点符号

        Args:
            text: 输入文本

        Returns:
            str: 过滤后的文本
        """
        return self.pattern.sub('', text)
