"""
测试 engine_processor 模块
"""
import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from core.text_processor import *

class TestIdentityTextProcessor:
    """
    测试 IdentityTextProcessor 类
    该处理器应直接返回输入文本不做任何修改
    """

    def test_process_normal(self):
        """测试正常文本的处理"""
        processor = IdentityTextProcessor()

        input_text = "这是一个测试文本。"
        assert processor.process(input_text) == input_text

    def test_process_empty(self):
        """测试空字符串的处理"""
        processor = IdentityTextProcessor()

        input_text = ""
        assert processor.process(input_text) == input_text

    def test_process_special_characters(self):
        """测试包含特殊字符的文本"""
        processor = IdentityTextProcessor()

        input_text = "包含特殊字符的文本！@#￥%……&*（）"
        assert processor.process(input_text) == input_text


class TestRegexExtractor:
    """
    测试 RegexExtractor 类
    该处理器应根据正则表达式提取文本中的匹配部分
    """

    def test_process_single_match(self):
        """测试单个匹配的处理"""
        pattern = r"\d+"
        processor = RegexExtractor(pattern)

        input_text = "订单号是12345。"
        expected_output = "12345"
        assert processor.process(input_text) == expected_output

    def test_process_multiple_matches(self):
        """测试多个匹配的处理"""
        pattern = r"\d+"
        processor = RegexExtractor(pattern)

        input_text = "订单号12345，金额678元。"
        expected_output = "12345678"
        assert processor.process(input_text) == expected_output

    def test_process_no_match(self):
        """测试未找到匹配的处理"""
        pattern = r"\d+"
        processor = RegexExtractor(pattern)

        input_text = "没有数字的文本。"
        expected_output = ""
        assert processor.process(input_text) == expected_output

    def test_process_empty_string(self):
        """测试空字符串的处理"""
        pattern = r"\d+"
        processor = RegexExtractor(pattern)

        input_text = ""
        expected_output = ""
        assert processor.process(input_text) == expected_output

    def test_process_special_characters(self):
        """测试包含特殊字符的文本"""
        pattern = r"[a-zA-Z]+"
        processor = RegexExtractor(pattern)

        input_text = "测试文本 with special characters !@#"
        expected_output = "withspecialcharacters"
        assert processor.process(input_text) == expected_output

    def test_process_custom_get_result(self):
        """测试自定义 get_result 函数的处理"""
        pattern = r"(\d+)-(\d+)"
        processor = RegexExtractor(pattern, get_result=lambda match: f"{match.group(2)}-{match.group(1)}")

        input_text = "订单号是123-456。"
        expected_output = "456-123"
        assert processor.process(input_text) == expected_output

    def test_process_overlapping_matches(self):
        """测试重叠匹配的处理"""
        pattern = r"(?=(\d{2}))"
        processor = RegexExtractor(pattern, get_result=lambda match: match.group(1))

        input_text = "12345"
        expected_output = "12233445"
        assert processor.process(input_text) == expected_output

    def test_process_multiline_mode(self):
        """测试多行模式的处理"""
        # 测试行首匹配
        pattern = r"^Test"
        processor = RegexExtractor(pattern, flags=re.MULTILINE)

        input_text = "This is a test.\nTest line two.\nAnother Test line.\nTest line four."
        expected_output = "TestTest"
        assert processor.process(input_text) == expected_output

        # 测试行尾匹配
        pattern = r"line\.$"
        processor = RegexExtractor(pattern, flags=re.MULTILINE)
        input_text = "This is first line.\nThis is second line.\nThis is third line."
        expected_output = "line.line.line."
        assert processor.process(input_text) == expected_output

        # 测试点号不匹配换行符
        pattern = r".+"
        processor = RegexExtractor(pattern, flags=re.MULTILINE)
        input_text = "Line one.\nLine two.\nLine three."
        expected_output = "Line one.Line two.Line three."
        assert processor.process(input_text) == expected_output

    def test_process_singleline_mode(self):
        """测试单行模式的处理"""
        # 测试行首匹配
        pattern = r"^Test"
        processor = RegexExtractor(pattern, flags=re.DOTALL)

        input_text = "This is a test.\nTest line two.\nAnother Test line.\nTest line four."
        expected_output = ""
        assert processor.process(input_text) == expected_output

        # 测试行尾匹配
        pattern = r"line\.$"
        processor = RegexExtractor(pattern, flags=re.DOTALL)
        input_text = "This is first line.\nThis is second line.\nThis is third line."
        expected_output = "line."
        assert processor.process(input_text) == expected_output

        # 测试点号匹配换行符
        pattern = r".+"
        processor = RegexExtractor(pattern, flags=re.DOTALL)
        input_text = "Line one.\nLine two.\nLine three."
        expected_output = "Line one.\nLine two.\nLine three."
        assert processor.process(input_text) == expected_output

    def test_process_delimiter(self):
        """测试自定义分隔符的处理"""
        pattern = r"\d+"
        processor = RegexExtractor(pattern, delimiter="|")

        input_text = "订单号12345，金额678元。"
        expected_output = "12345|678"
        assert processor.process(input_text) == expected_output


class TestSimpleDialogueContentExtractor:
    """
    测试 SimpleDialogueContentExtractor 类
    该处理器应提取对话文本中的内容部分，去除说话者标记
    """

    def test_process_empty_string(self):
        """测试空字符串的处理"""
        processor = SimpleDialogueContentExtractor()

        input_text = ""
        expected_output = ""
        assert processor.process(input_text) == expected_output

    def test_process_no_dialogue(self):
        """测试不包含对话标记的文本"""
        processor = SimpleDialogueContentExtractor()

        input_text = "这是一个没有对话标记的文本。"
        expected_output = ""
        assert processor.process(input_text) == expected_output

    def test_process_single_dialogue(self):
        """测试包含单个对话标记的文本"""
        processor = SimpleDialogueContentExtractor()

        input_text = "Alice: 「你好，Bob！」"
        expected_output = "你好，Bob！"
        assert processor.process(input_text) == expected_output

    def test_process_multiple_dialogues(self):
        """测试包含多个对话标记的文本"""
        processor = SimpleDialogueContentExtractor()

        input_text = "Alice: 「你好，Bob！」 Bob: 『这不是单引号』Carol: 这是旁白。Dave: 「再见！」"
        expected_output = "你好，Bob！再见！"
        assert processor.process(input_text) == expected_output

    def test_process_nested_dialogue(self):
        """测试包含嵌套对话标记的文本"""
        processor = SimpleDialogueContentExtractor()

        input_text = "Alice: 「他说：「你好，Bob！」」"
        expected_output = "他说：「你好，Bob！」"
        assert processor.process(input_text) == expected_output

    def test_process_unsymmetric_quotes(self):
        """测试包含不对称引号的文本"""
        processor = SimpleDialogueContentExtractor()

        input_text = "Alice: 「你好，Bob！』"
        expected_output = "你好，Bob！』"
        assert processor.process(input_text) == expected_output

    def test_process_special_characters(self):
        """测试包含特殊字符的文本"""
        processor = SimpleDialogueContentExtractor()

        input_text = "Alice: 「Hello, Bob! @#￥%……&*（）」"
        expected_output = "Hello, Bob! @#￥%……&*（）"
        assert processor.process(input_text) == expected_output


class TestChineseExtractor:
    """
    测试 ChineseExtractor 类
    该处理器应提取文本中的所有中文字符
    """

    def test_process_empty_string(self):
        """测试空字符串的处理"""
        processor = ChineseExtractor()

        input_text = ""
        expected_output = ""
        assert processor.process(input_text) == expected_output

    def test_process_normal(self):
        """测试正常文本的处理"""
        processor = ChineseExtractor()

        input_text = "This is a 测试文本 with some 中文字符."
        expected_output = "测试文本中文字符"
        assert processor.process(input_text) == expected_output

    def test_process_no_chinese(self):
        """测试不包含中文字符的文本"""
        processor = ChineseExtractor()

        input_text = "This is a test text with no Chinese characters."
        expected_output = ""
        assert processor.process(input_text) == expected_output

    def test_process_all_chinese(self):
        """测试全部为中文字符的文本"""
        processor = ChineseExtractor()

        input_text = "这是一个完全由中文字符组成的文本。"
        expected_output = "这是一个完全由中文字符组成的文本"
        assert processor.process(input_text) == expected_output

    def test_process_special_characters(self):
        """测试包含特殊字符的文本"""
        processor = ChineseExtractor()

        input_text = "测试文本！@#￥%……&*（）"
        expected_output = "测试文本"
        assert processor.process(input_text) == expected_output

    def test_process_mixed_languages(self):
        """测试包含多种语言字符的文本"""
        processor = ChineseExtractor()

        input_text = "Hello 你好 مرحبا こんにちは"
        expected_output = "你好"
        assert processor.process(input_text) == expected_output

    def test_process_corner_cases(self):
        """测试边界情况的处理"""
        processor = ChineseExtractor()

        # 测试第一个中文unicode字符
        input_text = "\u4e00 is the first Chinese character."
        expected_output = "一"
        assert processor.process(input_text) == expected_output

        # 测试最后一个中文unicode字符
        input_text = "\u9fff is the last Chinese character."
        expected_output = "鿿"
        assert processor.process(input_text) == expected_output


class TestPunctuationFilter:
    """
    测试 PunctuationFilter 类
    该处理器应过滤文本中的所有标点符号
    """

    def test_process_empty_string(self):
        """测试空字符串的处理"""
        processor = PunctuationFilter()

        input_text = ""
        expected_output = ""
        assert processor.process(input_text) == expected_output

    def test_process_normal(self):
        """测试正常文本的处理"""
        processor = PunctuationFilter()

        input_text = "Hello, world! This is a test."
        expected_output = "HelloworldThisisatest"
        assert processor.process(input_text) == expected_output

    def test_process_no_punctuation(self):
        """测试不包含标点符号的文本"""
        processor = PunctuationFilter()

        input_text = "This is a test with no punctuation"
        expected_output = "Thisisatestwithnopunctuation"
        assert processor.process(input_text) == expected_output

    def test_process_all_punctuation(self):
        """测试全部为标点符号的文本"""
        processor = PunctuationFilter()

        input_text = "!@#￥%……&*（）。，、；：‘’“”《》？"
        expected_output = ""
        assert processor.process(input_text) == expected_output

    def test_process_custom_punctuations(self):
        """测试自定义标点符号的处理"""
        custom_punctuations = ",.!?"
        processor = PunctuationFilter(punctuations=custom_punctuations)

        input_text = "Hello, world! This is a test. ###，"
        expected_output = "Hello world This is a test ###，"
        assert processor.process(input_text) == expected_output