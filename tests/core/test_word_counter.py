"""
测试 word_counter 模块
"""
import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from core.word_counter import *
from core.text_processor import *

class TestBasicWordCounter:
    """
    测试 BasicWordCounter 类
    实现了基本的字数统计功能，支持按类别统计
    统计字数时默认会使用 PunctuationFilter 过滤标点符号，可选传入自定义的文本处理器
    """

    def test_count_empty_text(self):
        """
        测试 count 方法，输入为空文本列表
        """
        counter = BasicWordCounter()
        text = []
        result = counter.count(text)
        assert result == 0

    def test_count_empty_strings(self):
        """
        测试 count 方法，输入为只包含空字符串的列表
        """
        counter = BasicWordCounter()
        text = ["", "", ""]
        result = counter.count(text)
        assert result == 0

    def test_count_without_filter(self):
        """
        测试 count 方法，不使用文本处理器
        """
        counter = BasicWordCounter(filter=IdentityTextProcessor())
        text = ["Hello, world!", "This is a test.", "你好！"]
        result = counter.count(text)
        assert result == 31  # 包含标点符号的字数

    def test_count_with_punctuation_filter(self):
        """
        测试 count 方法，使用 PunctuationFilter 过滤标点符号
        """
        counter = BasicWordCounter()
        text = ["Hello, world!", "This is a test.", "你好！"]
        result = counter.count(text)
        assert result == 23  # 不包含标点符号的字数

    def test_count_with_chinese_extractor(self):
        """
        测试 count 方法，使用 RegexExtractor 提取中文字符
        """
        chinese_extractor = ChineseExtractor()
        counter = BasicWordCounter(filter=chinese_extractor)
        text = ["Hello, world!", "This is a test.", "你好，世界！"]
        result = counter.count(text)
        assert result == 4  # 只统计中文字符的字数

    def test_count_with_custom_filter(self):
        """
        测试 count 方法，使用自定义文本处理器
        """
        class CustomFilter(TextProcessor):
            def process(self, text: str) -> str:
                return text.replace(" ", "")  # 去除空格

        counter = BasicWordCounter(filter=CustomFilter())
        text = ["Hello, world!", "This is a test.", "你好！"]
        result = counter.count(text)
        assert result == 27  # 去除空格后的字数

    def test_count_with_none_and_nan(self):
        """
        测试 count 方法，输入包含 None 和 NaN 的列表
        """
        counter = BasicWordCounter()
        text = ["Hello, world!", None, float('nan'), "This is a test."]
        result = counter.count(text)
        assert result == 21  # 只统计有效字符串的字数

    def test_count_with_nonstrings_convert_to_strings(self):
        """
        测试 count 方法，输入包含非字符串类型的元素
        """
        counter = BasicWordCounter()
        text = ["Hello, world!", 123, True, "This is a test."]
        result = counter.count(text)
        assert result == 28  # 转换为字符串后的字数

    def test_count_with_nonstrings_cannot_convert(self):
        """
        测试 count 方法，输入包含无法转换为字符串的元素
        """
        counter = BasicWordCounter()
        class NonStringable:
            def __str__(self):
                raise TypeError("Cannot convert to string")

        text = ["Hello, world!", NonStringable(), "This is a test."]
        with pytest.raises(TypeError):
            counter.count(text)

    def test_count_by(self):
        """
        测试 count_by 方法，按类别统计字数
        """
        counter = BasicWordCounter()
        text = [
            ("greeting", "Hello, world!"),
            ("statement", "This is a test."),
            ("greeting", "Hi there!")
        ]
        result = counter.count_by(text)
        assert result == {
            "greeting": 17,
            "statement": 11
        }

    def test_count_by_with_none_and_nan(self):
        """
        测试 count_by 方法，输入包含 None 和 NaN 的类别和文本
        """
        counter = BasicWordCounter()
        text = [
            ("greeting", "Hello, world!"),
            (None, "This is a test."),
            ("greeting", None),
            ("statement", float('nan'))
        ]
        result = counter.count_by(text)
        assert result == {
            "greeting": 10,
            "unrecognized": 11
        }
