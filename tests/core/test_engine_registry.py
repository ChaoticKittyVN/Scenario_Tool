"""
测试 engine_registry 模块
"""
import pytest
from unittest.mock import Mock
from core.engine_registry import (
    EngineMetadata,
    EngineRegistry,
    register_engine
)
from core.config_manager import EngineConfig, RenpyConfig, NaninovelConfig
from core.exceptions import EngineNotRegisteredError


class TestEngineMetadata:
    """测试 EngineMetadata 类"""

    def test_create_metadata(self):
        """测试创建引擎元数据"""
        processor_factory = Mock()
        validator_factory = Mock()

        metadata = EngineMetadata(
            name="test_engine",
            display_name="Test Engine",
            file_extension=".test",
            config_class=EngineConfig,
            processor_factory=processor_factory,
            validator_factory=validator_factory,
            description="A test engine"
        )

        assert metadata.name == "test_engine"
        assert metadata.display_name == "Test Engine"
        assert metadata.file_extension == ".test"
        assert metadata.config_class == EngineConfig
        assert metadata.processor_factory == processor_factory
        assert metadata.validator_factory == validator_factory
        assert metadata.description == "A test engine"

    def test_create_metadata_without_optional_fields(self):
        """测试创建引擎元数据（不包含可选字段）"""
        processor_factory = Mock()

        metadata = EngineMetadata(
            name="minimal_engine",
            display_name="Minimal Engine",
            file_extension=".min",
            config_class=EngineConfig,
            processor_factory=processor_factory
        )

        assert metadata.name == "minimal_engine"
        assert metadata.validator_factory is None
        assert metadata.description == ""


class TestEngineRegistry:
    """测试 EngineRegistry 类"""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """每个测试前重置注册表"""
        EngineRegistry.reset()
        yield
        EngineRegistry.reset()

    def test_singleton_pattern(self):
        """测试单例模式"""
        registry1 = EngineRegistry()
        registry2 = EngineRegistry()

        assert registry1 is registry2

    def test_register_engine(self):
        """测试注册引擎"""
        processor_factory = Mock()
        metadata = EngineMetadata(
            name="renpy",
            display_name="Ren'Py",
            file_extension=".rpy",
            config_class=RenpyConfig,
            processor_factory=processor_factory
        )

        EngineRegistry.register(metadata)

        assert EngineRegistry.is_registered("renpy")

    def test_register_duplicate_engine(self):
        """测试注册重复引擎（应该覆盖）"""
        processor_factory1 = Mock()
        processor_factory2 = Mock()

        metadata1 = EngineMetadata(
            name="test",
            display_name="Test 1",
            file_extension=".test",
            config_class=EngineConfig,
            processor_factory=processor_factory1
        )

        metadata2 = EngineMetadata(
            name="test",
            display_name="Test 2",
            file_extension=".test2",
            config_class=EngineConfig,
            processor_factory=processor_factory2
        )

        EngineRegistry.register(metadata1)
        EngineRegistry.register(metadata2)

        # 应该被覆盖为第二个
        retrieved = EngineRegistry.get("test")
        assert retrieved.display_name == "Test 2"
        assert retrieved.file_extension == ".test2"

    def test_get_registered_engine(self):
        """测试获取已注册引擎"""
        processor_factory = Mock()
        metadata = EngineMetadata(
            name="naninovel",
            display_name="Naninovel",
            file_extension=".nani",
            config_class=NaninovelConfig,
            processor_factory=processor_factory,
            description="Naninovel engine"
        )

        EngineRegistry.register(metadata)
        retrieved = EngineRegistry.get("naninovel")

        assert retrieved.name == "naninovel"
        assert retrieved.display_name == "Naninovel"
        assert retrieved.file_extension == ".nani"
        assert retrieved.config_class == NaninovelConfig
        assert retrieved.description == "Naninovel engine"

    def test_get_unregistered_engine(self):
        """测试获取未注册引擎（应该抛出异常）"""
        with pytest.raises(EngineNotRegisteredError, match="引擎 'nonexistent' 未注册"):
            EngineRegistry.get("nonexistent")

    def test_is_registered_true(self):
        """测试检查已注册引擎"""
        processor_factory = Mock()
        metadata = EngineMetadata(
            name="test",
            display_name="Test",
            file_extension=".test",
            config_class=EngineConfig,
            processor_factory=processor_factory
        )

        EngineRegistry.register(metadata)

        assert EngineRegistry.is_registered("test") is True

    def test_is_registered_false(self):
        """测试检查未注册引擎"""
        assert EngineRegistry.is_registered("nonexistent") is False

    def test_list_engines_empty(self):
        """测试列出引擎（空注册表）"""
        engines = EngineRegistry.list_engines()

        assert engines == {}
        assert isinstance(engines, dict)

    def test_list_engines_with_multiple_engines(self):
        """测试列出多个引擎"""
        processor1 = Mock()
        processor2 = Mock()

        metadata1 = EngineMetadata(
            name="renpy",
            display_name="Ren'Py",
            file_extension=".rpy",
            config_class=RenpyConfig,
            processor_factory=processor1
        )

        metadata2 = EngineMetadata(
            name="naninovel",
            display_name="Naninovel",
            file_extension=".nani",
            config_class=NaninovelConfig,
            processor_factory=processor2
        )

        EngineRegistry.register(metadata1)
        EngineRegistry.register(metadata2)

        engines = EngineRegistry.list_engines()

        assert len(engines) == 2
        assert "renpy" in engines
        assert "naninovel" in engines
        assert engines["renpy"].display_name == "Ren'Py"
        assert engines["naninovel"].display_name == "Naninovel"

    def test_list_engines_returns_copy(self):
        """测试 list_engines 返回副本（不影响原注册表）"""
        processor = Mock()
        metadata = EngineMetadata(
            name="test",
            display_name="Test",
            file_extension=".test",
            config_class=EngineConfig,
            processor_factory=processor
        )

        EngineRegistry.register(metadata)
        engines = EngineRegistry.list_engines()

        # 修改返回的字典
        engines.clear()

        # 原注册表不应该被影响
        assert EngineRegistry.is_registered("test") is True

    def test_reset_registry(self):
        """测试重置注册表"""
        processor = Mock()
        metadata = EngineMetadata(
            name="test",
            display_name="Test",
            file_extension=".test",
            config_class=EngineConfig,
            processor_factory=processor
        )

        EngineRegistry.register(metadata)
        assert EngineRegistry.is_registered("test") is True

        EngineRegistry.reset()
        assert EngineRegistry.is_registered("test") is False
        assert EngineRegistry.list_engines() == {}


class TestRegisterEngineDecorator:
    """测试 register_engine 装饰器"""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """每个测试前重置注册表"""
        EngineRegistry.reset()
        yield
        EngineRegistry.reset()

    def test_register_engine_decorator_basic(self):
        """测试基础装饰器功能"""
        @register_engine(
            name="test_engine",
            display_name="Test Engine",
            file_extension=".test",
            config_class=EngineConfig
        )
        def create_processor():
            return Mock()

        # 验证引擎已注册
        assert EngineRegistry.is_registered("test_engine")

        # 验证元数据
        metadata = EngineRegistry.get("test_engine")
        assert metadata.name == "test_engine"
        assert metadata.display_name == "Test Engine"
        assert metadata.file_extension == ".test"
        assert metadata.config_class == EngineConfig

        # 验证装饰器返回原函数
        assert callable(create_processor)

    def test_register_engine_decorator_with_all_params(self):
        """测试装饰器包含所有参数"""
        validator = Mock()

        @register_engine(
            name="full_engine",
            display_name="Full Engine",
            file_extension=".full",
            config_class=RenpyConfig,
            validator_factory=validator,
            description="A fully configured engine"
        )
        def create_processor():
            return Mock()

        metadata = EngineRegistry.get("full_engine")
        assert metadata.name == "full_engine"
        assert metadata.display_name == "Full Engine"
        assert metadata.file_extension == ".full"
        assert metadata.config_class == RenpyConfig
        assert metadata.validator_factory == validator
        assert metadata.description == "A fully configured engine"

    def test_register_engine_decorator_preserves_function(self):
        """测试装饰器保留原函数功能"""
        @register_engine(
            name="func_test",
            display_name="Function Test",
            file_extension=".func",
            config_class=EngineConfig
        )
        def create_processor(config):
            return f"Processor with {config}"

        # 验证函数仍然可以正常调用
        result = create_processor("test_config")
        assert result == "Processor with test_config"

    def test_register_multiple_engines_with_decorator(self):
        """测试使用装饰器注册多个引擎"""
        @register_engine(
            name="engine1",
            display_name="Engine 1",
            file_extension=".e1",
            config_class=EngineConfig
        )
        def create_processor1():
            return "processor1"

        @register_engine(
            name="engine2",
            display_name="Engine 2",
            file_extension=".e2",
            config_class=EngineConfig
        )
        def create_processor2():
            return "processor2"

        # 验证两个引擎都已注册
        assert EngineRegistry.is_registered("engine1")
        assert EngineRegistry.is_registered("engine2")

        engines = EngineRegistry.list_engines()
        assert len(engines) == 2


class TestEngineRegistryIntegration:
    """集成测试：测试完整的引擎注册和使用流程"""

    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """每个测试前重置注册表"""
        EngineRegistry.reset()
        yield
        EngineRegistry.reset()

    def test_full_workflow(self):
        """测试完整工作流程"""
        # 1. 使用装饰器注册引擎
        @register_engine(
            name="renpy",
            display_name="Ren'Py",
            file_extension=".rpy",
            config_class=RenpyConfig,
            description="Ren'Py visual novel engine"
        )
        def create_renpy_processor(config):
            return f"RenpyProcessor({config})"

        # 2. 检查引擎是否已注册
        assert EngineRegistry.is_registered("renpy")

        # 3. 获取引擎元数据
        metadata = EngineRegistry.get("renpy")
        assert metadata.display_name == "Ren'Py"

        # 4. 使用 processor_factory 创建处理器
        processor = metadata.processor_factory("test_config")
        assert processor == "RenpyProcessor(test_config)"

        # 5. 列出所有引擎
        engines = EngineRegistry.list_engines()
        assert "renpy" in engines

    def test_multiple_engines_workflow(self):
        """测试多引擎工作流程"""
        # 注册多个引擎
        @register_engine(
            name="renpy",
            display_name="Ren'Py",
            file_extension=".rpy",
            config_class=RenpyConfig
        )
        def create_renpy():
            return "renpy_processor"

        @register_engine(
            name="naninovel",
            display_name="Naninovel",
            file_extension=".nani",
            config_class=NaninovelConfig
        )
        def create_naninovel():
            return "naninovel_processor"

        # 验证所有引擎
        engines = EngineRegistry.list_engines()
        assert len(engines) == 2

        # 分别获取并使用
        renpy_meta = EngineRegistry.get("renpy")
        nani_meta = EngineRegistry.get("naninovel")

        assert renpy_meta.processor_factory() == "renpy_processor"
        assert nani_meta.processor_factory() == "naninovel_processor"
