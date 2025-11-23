"""
测试 BaseSentenceGenerator 基类
"""
import pytest
from unittest.mock import Mock
from core.base_sentence_generator import BaseSentenceGenerator
from core.param_translator import ParamTranslator
from core.config_manager import EngineConfig


# 创建具体的生成器类用于测试（因为 BaseSentenceGenerator 是抽象类）
# 注意：不要以 Test 开头，否则 pytest 会误认为这是测试类
class ConcreteSentenceGenerator(BaseSentenceGenerator):
    """用于测试的具体生成器实现"""

    param_config = {
        "Music": {
            "translate_type": "Music",
            "format": "play music {value}"
        },
        "Speaker": {
            "translate_type": "Speaker"
        },
        "Background": {
            "translate_types": ["Background", "Scene"],
            "format": "scene {value}"
        },
        "Volume": {
            "default": "100",
            "format": "volume {value}"
        }
    }

    @property
    def category(self) -> str:
        return "test"

    def process(self, data):
        if not data:
            return None
        return [f"test command: {data}"]


class TestBaseSentenceGenerator:
    """测试 BaseSentenceGenerator 基类"""

    @pytest.fixture
    def mock_translator(self):
        """创建模拟的翻译器"""
        translator = Mock(spec=ParamTranslator)
        translator.translate.side_effect = lambda type_, value: f"translated_{value}"
        translator.has_mapping.return_value = True
        return translator

    @pytest.fixture
    def mock_config(self):
        """创建模拟的引擎配置"""
        config = Mock(spec=EngineConfig)
        config.engine_type = "test_engine"
        config.file_extension = ".test"
        return config

    @pytest.fixture
    def generator(self, mock_translator, mock_config):
        """创建测试生成器实例"""
        return ConcreteSentenceGenerator(mock_translator, mock_config)

    def test_init(self, generator, mock_translator, mock_config):
        """测试初始化"""
        assert generator.translator == mock_translator
        assert generator.engine_config == mock_config

    def test_category_property(self, generator):
        """测试 category 属性"""
        assert generator.category == "test"

    def test_priority_default(self, generator):
        """测试默认优先级"""
        # 因为模块名不包含数字前缀，应该返回 999
        assert generator.priority == 999

    @pytest.mark.parametrize("data,expected", [
        ({"key": "value"}, True),
        ({}, False),
        (None, False),
    ])
    def test_can_process(self, generator, data, expected):
        """测试 can_process 方法"""
        assert generator.can_process(data) is expected

    def test_process_method(self, generator):
        """测试 process 方法"""
        data = {"test": "data"}
        result = generator.process(data)
        assert result == ["test command: {'test': 'data'}"]

    def test_process_with_empty_data(self, generator):
        """测试 process 方法（空数据）"""
        result = generator.process({})
        assert result is None

    def test_do_translate_single_type(self, generator, mock_translator):
        """测试翻译单一类型参数"""
        row_data = {"Music": "bgm_main"}

        result = generator.do_translate(row_data)

        assert result["Music"] == "translated_bgm_main"
        mock_translator.translate.assert_called_with("Music", "bgm_main")

    def test_do_translate_multiple_types(self, generator, mock_translator):
        """测试翻译多类型参数"""
        row_data = {"Background": "scene1"}

        result = generator.do_translate(row_data)

        # 应该尝试第一个类型
        assert result["Background"] == "translated_scene1"
        mock_translator.has_mapping.assert_called()

    def test_do_translate_empty_value(self, generator, mock_translator):
        """测试翻译空值"""
        row_data = {"Music": "", "Speaker": None}

        result = generator.do_translate(row_data)

        # 空值不应该被翻译
        assert result["Music"] == ""
        assert result["Speaker"] is None
        mock_translator.translate.assert_not_called()

    def test_do_translate_no_config(self, generator, mock_translator):
        """测试翻译没有配置的参数"""
        row_data = {"UnknownParam": "value"}

        result = generator.do_translate(row_data)

        # 没有配置的参数应该保持原样
        assert result["UnknownParam"] == "value"
        mock_translator.translate.assert_not_called()

    def test_do_translate_preserves_original(self, generator):
        """测试翻译不修改原始数据"""
        original = {"Music": "bgm_main"}
        result = generator.do_translate(original)

        # 原始数据不应该被修改
        assert original == {"Music": "bgm_main"}
        assert result != original  # 应该是新的字典

    @pytest.mark.parametrize("value,expected", [
        # 有效整数
        ("123", 123),
        ("0", 0),
        ("-456", -456),
        # 浮点数（取整）
        ("123.45", 123),
        ("99.9", 99),
        # 无效字符串（返回原值）
        ("abc", "abc"),
        ("", ""),
        # 数字类型
        (123, 123),
        (45.67, 45),
    ])
    def test_get_int(self, generator, value, expected):
        """测试 get_int 方法"""
        assert generator.get_int(value) == expected

    @pytest.mark.parametrize("param_name,expected", [
        ("Music", "play music {value}"),
        ("NonExistent", None),
        ("Speaker", None),  # 没有 format
    ])
    def test_get_format_in_config(self, generator, param_name, expected):
        """测试获取格式字符串"""
        assert generator.get_format_in_config(param_name) == expected

    @pytest.mark.parametrize("param_name,data,use_default,expected", [
        # 存在的值
        ("Music", {"Music": "bgm_main"}, False, "bgm_main"),
        ("Speaker", {"Speaker": "Alice"}, False, "Alice"),
        # 不存在的值
        ("Speaker", {"Music": "bgm_main"}, False, ""),
        # 使用默认值
        ("Volume", {}, True, "100"),
        # 不使用默认值
        ("Volume", {}, False, ""),
        # 自动转换为字符串
        ("Number", {"Number": 123}, False, "123"),
        ("Float", {"Float": 45.67}, False, "45.67"),
    ])
    def test_get_value(self, generator, param_name, data, use_default, expected):
        """测试 get_value 方法"""
        assert generator.get_value(param_name, data, use_default=use_default) == expected

    @pytest.mark.parametrize("param_name,data,use_default,expected", [
        # 有值
        ("Music", {"Music": "bgm_main"}, False, "play music bgm_main"),
        # 无值
        ("Music", {}, False, ""),
        # 使用默认值
        ("Volume", {}, True, "volume 100"),
        # 没有格式字符串
        ("Speaker", {"Speaker": "Alice"}, False, ""),
    ])
    def test_get_sentence(self, generator, param_name, data, use_default, expected):
        """测试 get_sentence 方法"""
        assert generator.get_sentence(param_name, data, use_default=use_default) == expected

    @pytest.mark.parametrize("param_name,data,expected", [
        # 参数存在
        ("Music", {"Music": "bgm_main"}, True),
        ("Speaker", {"Speaker": ""}, True),  # 即使值为空
        # 参数不存在
        ("Speaker", {"Music": "bgm_main"}, False),
    ])
    def test_exists_param(self, generator, param_name, data, expected):
        """测试 exists_param 方法"""
        assert generator.exists_param(param_name, data) is expected

    def test_repr(self, generator):
        """测试字符串表示"""
        repr_str = repr(generator)
        assert "ConcreteSentenceGenerator" in repr_str
        assert "category=test" in repr_str
        assert "priority=999" in repr_str


class TestPriorityExtraction:
    """测试优先级提取功能"""

    @pytest.fixture
    def mock_translator(self):
        """创建模拟的翻译器"""
        return Mock(spec=ParamTranslator)

    @pytest.fixture
    def mock_config(self):
        """创建模拟的引擎配置"""
        return Mock(spec=EngineConfig)

    def test_priority_with_prefix(self, mock_translator, mock_config):
        """测试带数字前缀的优先级"""
        # 创建一个模拟的生成器，模块名包含数字前缀
        class PrefixedGenerator(BaseSentenceGenerator):
            @property
            def category(self):
                return "prefixed"

            def process(self, data):
                return []

        # 模拟模块名
        generator = PrefixedGenerator(mock_translator, mock_config)
        # 手动设置模块名来测试
        generator.__class__.__module__ = "engines.test.10_test_generator"

        # 应该提取出 10
        assert generator.priority == 10

    def test_priority_without_prefix(self, mock_translator, mock_config):
        """测试不带数字前缀的优先级"""
        class NoPrefixGenerator(BaseSentenceGenerator):
            @property
            def category(self):
                return "no_prefix"

            def process(self, data):
                return []

        generator = NoPrefixGenerator(mock_translator, mock_config)
        generator.__class__.__module__ = "engines.test.test_generator"

        # 应该返回默认值 999
        assert generator.priority == 999


class TestTranslateMultipleTypes:
    """测试多类型翻译的详细场景"""

    @pytest.fixture
    def generator_with_multi_types(self):
        """创建支持多类型翻译的生成器"""
        translator = Mock(spec=ParamTranslator)
        config = Mock(spec=EngineConfig)

        class MultiTypeGenerator(BaseSentenceGenerator):
            param_config = {
                "Asset": {
                    "translate_types": ["Background", "Character", "Music"]
                }
            }

            @property
            def category(self):
                return "multi"

            def process(self, data):
                return []

        return MultiTypeGenerator(translator, config)

    def test_translate_first_match(self, generator_with_multi_types):
        """测试翻译第一个匹配的类型"""
        translator = generator_with_multi_types.translator
        translator.has_mapping.side_effect = [True, False, False]
        translator.translate.return_value = "translated_bg"

        row_data = {"Asset": "bg_001"}
        result = generator_with_multi_types.do_translate(row_data)

        assert result["Asset"] == "translated_bg"
        translator.translate.assert_called_once_with("Background", "bg_001")

    def test_translate_second_match(self, generator_with_multi_types):
        """测试翻译第二个匹配的类型"""
        translator = generator_with_multi_types.translator
        translator.has_mapping.side_effect = [False, True, False]
        translator.translate.return_value = "translated_char"

        row_data = {"Asset": "char_001"}
        result = generator_with_multi_types.do_translate(row_data)

        assert result["Asset"] == "translated_char"
        translator.translate.assert_called_once_with("Character", "char_001")

    def test_translate_no_match(self, generator_with_multi_types):
        """测试没有匹配的类型"""
        translator = generator_with_multi_types.translator
        translator.has_mapping.return_value = False

        row_data = {"Asset": "unknown_001"}
        result = generator_with_multi_types.do_translate(row_data)

        # 没有匹配时应该保持原值
        assert result["Asset"] == "unknown_001"
        translator.translate.assert_not_called()
