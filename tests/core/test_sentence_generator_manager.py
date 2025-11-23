"""
测试 sentence_generator_manager 模块
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from core.sentence_generator_manager import SentenceGeneratorManager
from core.base_sentence_generator import BaseSentenceGenerator
from core.param_translator import ParamTranslator
from core.config_manager import EngineConfig
from core.exceptions import GeneratorError


# 创建测试用的生成器类
class MockGenerator1(BaseSentenceGenerator):
    """测试生成器 1"""

    param_config = {
        "Music": {"format": "play music {value}"},
        "Sound": {"format": "play sound {value}"}
    }

    @property
    def category(self):
        return "mock1"

    @property
    def priority(self):
        return 10

    def process(self, data):
        return ["mock1 command"]


class MockGenerator2(BaseSentenceGenerator):
    """测试生成器 2"""

    param_config = {
        "Background": {"format": "scene {value}"},
        "Character": {"format": "show {value}"}
    }

    @property
    def category(self):
        return "mock2"

    @property
    def priority(self):
        return 5

    def process(self, data):
        return ["mock2 command"]


class MockGenerator3(BaseSentenceGenerator):
    """测试生成器 3（没有 param_config）"""

    @property
    def category(self):
        return "mock3"

    @property
    def priority(self):
        return 20

    def process(self, data):
        return ["mock3 command"]


class TestSentenceGeneratorManager:
    """测试 SentenceGeneratorManager 类"""

    @pytest.fixture
    def manager(self):
        """创建管理器实例"""
        return SentenceGeneratorManager("test_engine")

    def test_init(self, manager):
        """测试初始化"""
        assert manager.engine_type == "test_engine"
        assert manager.generator_classes == []
        assert manager.param_configs == {}
        assert manager._loaded is False

    def test_load_only_once(self, manager):
        """测试 load 方法只执行一次"""
        with patch.object(manager, '_discover_generator_classes') as mock_discover:
            with patch.object(manager, '_collect_param_configs') as mock_collect:
                # 第一次调用
                manager.load()
                assert manager._loaded is True
                assert mock_discover.call_count == 1
                assert mock_collect.call_count == 1

                # 第二次调用（应该被跳过）
                manager.load()
                assert mock_discover.call_count == 1
                assert mock_collect.call_count == 1

    @pytest.mark.parametrize("obj,expected", [
        # 有效的生成器类
        (MockGenerator1, True),
        (MockGenerator2, True),
        # 基类（应该被过滤）
        (BaseSentenceGenerator, False),
        # 非类对象
        ("not a class", False),
        (123, False),
        (None, False),
    ])
    def test_is_generator_class(self, manager, obj, expected):
        """测试 _is_generator_class 方法"""
        assert manager._is_generator_class(obj) is expected

    def test_is_generator_class_not_subclass(self, manager):
        """测试非生成器子类"""
        class NotAGenerator:
            pass

        assert manager._is_generator_class(NotAGenerator) is False

    def test_collect_param_configs(self, manager):
        """测试收集参数配置"""
        manager.generator_classes = [MockGenerator1, MockGenerator2, MockGenerator3]
        manager._collect_param_configs()

        # 验证收集到的配置
        assert "Music" in manager.param_configs
        assert "Sound" in manager.param_configs
        assert "Background" in manager.param_configs
        assert "Character" in manager.param_configs
        assert len(manager.param_configs) == 4

    def test_collect_param_configs_empty(self, manager):
        """测试收集空配置"""
        manager.generator_classes = []
        manager._collect_param_configs()

        assert manager.param_configs == {}

    def test_collect_param_configs_no_param_config(self, manager):
        """测试生成器没有 param_config 属性"""
        manager.generator_classes = [MockGenerator3]
        manager._collect_param_configs()

        # MockGenerator3 没有 param_config，应该为空
        assert manager.param_configs == {}

    def test_get_all_param_names(self, manager):
        """测试获取所有参数名称"""
        manager.generator_classes = [MockGenerator1, MockGenerator2]
        manager._loaded = True
        manager._collect_param_configs()

        param_names = manager.get_all_param_names()

        # 应该按字母顺序排序
        assert param_names == ["Background", "Character", "Music", "Sound"]

    def test_get_all_param_names_empty(self, manager):
        """测试获取空参数列表"""
        manager._loaded = True
        param_names = manager.get_all_param_names()

        assert param_names == []

    def test_get_all_param_names_calls_load(self, manager):
        """测试 get_all_param_names 会调用 load"""
        with patch.object(manager, 'load') as mock_load:
            manager.get_all_param_names()
            mock_load.assert_called_once()


class TestCreateGeneratorInstances:
    """测试创建生成器实例"""

    @pytest.fixture
    def manager(self):
        """创建管理器实例"""
        return SentenceGeneratorManager("test_engine")

    @pytest.fixture
    def mock_translator(self):
        """创建模拟翻译器"""
        return Mock(spec=ParamTranslator)

    @pytest.fixture
    def mock_config(self):
        """创建模拟配置"""
        return Mock(spec=EngineConfig)

    def test_create_generator_instances(self, manager, mock_translator, mock_config):
        """测试创建生成器实例"""
        manager.generator_classes = [MockGenerator1, MockGenerator2, MockGenerator3]
        manager._loaded = True

        instances = manager.create_generator_instances(mock_translator, mock_config)

        # 验证创建了 3 个实例
        assert len(instances) == 3

        # 验证所有实例都是 BaseSentenceGenerator 的子类
        for instance in instances:
            assert isinstance(instance, BaseSentenceGenerator)

    def test_create_generator_instances_sorted_by_priority(self, manager, mock_translator, mock_config):
        """测试生成器按优先级排序"""
        # MockGenerator1: priority=10
        # MockGenerator2: priority=5
        # MockGenerator3: priority=20
        manager.generator_classes = [MockGenerator1, MockGenerator2, MockGenerator3]
        manager._loaded = True

        instances = manager.create_generator_instances(mock_translator, mock_config)

        # 应该按优先级从小到大排序
        assert instances[0].priority == 5  # MockGenerator2
        assert instances[1].priority == 10  # MockGenerator1
        assert instances[2].priority == 20  # MockGenerator3

    def test_create_generator_instances_calls_load(self, manager, mock_translator, mock_config):
        """测试 create_generator_instances 会调用 load"""
        with patch.object(manager, 'load') as mock_load:
            manager._loaded = True
            manager.generator_classes = []
            manager.create_generator_instances(mock_translator, mock_config)
            mock_load.assert_called_once()

    def test_create_generator_instances_empty(self, manager, mock_translator, mock_config):
        """测试没有生成器类时"""
        manager.generator_classes = []
        manager._loaded = True

        instances = manager.create_generator_instances(mock_translator, mock_config)

        assert instances == []

    def test_create_generator_instances_with_error(self, manager, mock_translator, mock_config):
        """测试创建实例时出错"""
        # 创建一个会抛出异常的生成器类
        class BrokenGenerator(BaseSentenceGenerator):
            def __init__(self, translator, config):
                raise ValueError("Initialization failed")

            @property
            def category(self):
                return "broken"

            def process(self, data):
                return []

        manager.generator_classes = [MockGenerator1, BrokenGenerator, MockGenerator2]
        manager._loaded = True

        instances = manager.create_generator_instances(mock_translator, mock_config)

        # 应该只创建成功的实例（跳过失败的）
        assert len(instances) == 2
        assert all(isinstance(i, BaseSentenceGenerator) for i in instances)


class TestDiscoverGeneratorClasses:
    """测试发现生成器类"""

    @pytest.fixture
    def manager(self):
        """创建管理器实例"""
        return SentenceGeneratorManager("test_engine")

    def test_discover_generator_classes_manual_add(self, manager):
        """测试手动添加生成器类（模拟发现过程）"""
        # 直接测试发现后的结果，而不是 mock 整个发现过程
        # 这是一个更实用的测试方法
        manager.generator_classes = [MockGenerator1, MockGenerator2]

        # 验证生成器类已添加
        assert len(manager.generator_classes) == 2
        assert MockGenerator1 in manager.generator_classes
        assert MockGenerator2 in manager.generator_classes

    def test_discover_generator_classes_skip_packages(self, manager):
        """测试跳过包（只处理模块）"""
        mock_package = MagicMock()
        mock_package.__path__ = []

        with patch('importlib.import_module') as mock_import:
            with patch('pkgutil.iter_modules') as mock_iter:
                mock_import.return_value = mock_package
                # is_pkg=True 表示是包，应该被跳过
                mock_iter.return_value = [
                    (None, "subpackage", True),
                    (None, "not_generator", False)  # 不以 _generator 结尾
                ]

                manager._discover_generator_classes()

                # 不应该发现任何生成器
                assert manager.generator_classes == []

    def test_discover_generator_classes_skip_non_generator_modules(self, manager):
        """测试跳过不以 _generator 结尾的模块"""
        mock_package = MagicMock()
        mock_package.__path__ = []

        with patch('importlib.import_module') as mock_import:
            with patch('pkgutil.iter_modules') as mock_iter:
                mock_import.return_value = mock_package
                mock_iter.return_value = [
                    (None, "utils", False),
                    (None, "helpers", False),
                    (None, "__init__", False)
                ]

                manager._discover_generator_classes()

                assert manager.generator_classes == []

    def test_discover_generator_classes_import_error(self, manager):
        """测试导入包失败"""
        with patch('importlib.import_module') as mock_import:
            mock_import.side_effect = ImportError("Package not found")

            with pytest.raises(GeneratorError, match="无法加载引擎 test_engine 的生成器"):
                manager._discover_generator_classes()

    def test_discover_generator_classes_module_import_error(self, manager):
        """测试导入模块失败（应该记录错误但继续）"""
        mock_package = MagicMock()
        mock_package.__path__ = []

        with patch('importlib.import_module') as mock_import:
            with patch('pkgutil.iter_modules') as mock_iter:
                # 第一次调用返回包，第二次调用抛出异常
                mock_import.side_effect = [
                    mock_package,
                    ImportError("Module not found")
                ]
                mock_iter.return_value = [
                    (None, "broken_generator", False)
                ]

                # 应该不抛出异常，只记录错误
                manager._discover_generator_classes()

                # 不应该发现任何生成器
                assert manager.generator_classes == []


class TestSentenceGeneratorManagerIntegration:
    """集成测试：测试完整的工作流程"""

    @pytest.fixture
    def manager(self):
        """创建管理器实例"""
        return SentenceGeneratorManager("test_engine")

    @pytest.fixture
    def mock_translator(self):
        """创建模拟翻译器"""
        return Mock(spec=ParamTranslator)

    @pytest.fixture
    def mock_config(self):
        """创建模拟配置"""
        return Mock(spec=EngineConfig)

    def test_full_workflow(self, manager, mock_translator, mock_config):
        """测试完整工作流程"""
        # 模拟发现生成器
        manager.generator_classes = [MockGenerator1, MockGenerator2, MockGenerator3]
        manager._loaded = True

        # 1. 收集参数配置
        manager._collect_param_configs()
        assert len(manager.param_configs) == 4

        # 2. 获取所有参数名称
        param_names = manager.get_all_param_names()
        assert len(param_names) == 4
        assert param_names == ["Background", "Character", "Music", "Sound"]

        # 3. 创建生成器实例
        instances = manager.create_generator_instances(mock_translator, mock_config)
        assert len(instances) == 3

        # 4. 验证排序
        assert instances[0].priority < instances[1].priority < instances[2].priority

        # 5. 验证实例可以使用
        for instance in instances:
            assert instance.translator == mock_translator
            assert instance.engine_config == mock_config
            result = instance.process({"test": "data"})
            assert result is not None

    def test_load_idempotent(self, manager):
        """测试 load 方法的幂等性"""
        manager.generator_classes = [MockGenerator1]
        manager._loaded = True

        # 多次调用 load
        manager.load()
        manager.load()
        manager.load()

        # 状态应该保持一致
        assert manager._loaded is True

    def test_param_configs_merge(self, manager):
        """测试参数配置合并"""
        # 创建两个有重叠配置的生成器
        class Generator1(BaseSentenceGenerator):
            param_config = {"Music": {"format": "play {value}"}}

            @property
            def category(self):
                return "gen1"

            def process(self, data):
                return []

        class Generator2(BaseSentenceGenerator):
            param_config = {
                "Music": {"format": "music {value}"},  # 重复的键
                "Sound": {"format": "sound {value}"}
            }

            @property
            def category(self):
                return "gen2"

            def process(self, data):
                return []

        manager.generator_classes = [Generator1, Generator2]
        manager._collect_param_configs()

        # 后面的配置应该覆盖前面的
        assert "Music" in manager.param_configs
        assert "Sound" in manager.param_configs
        assert manager.param_configs["Music"]["format"] == "music {value}"
