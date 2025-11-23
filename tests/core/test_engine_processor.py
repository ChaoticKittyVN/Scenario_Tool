"""
测试 engine_processor 模块
"""
import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from core.engine_processor import EngineProcessor
from core.base_sentence_generator import BaseSentenceGenerator
from core.param_translator import ParamTranslator
from core.config_manager import EngineConfig
from core.sentence_generator_manager import SentenceGeneratorManager


# 创建测试用的生成器类
class MockMusicGenerator(BaseSentenceGenerator):
    """测试音乐生成器"""

    param_config = {
        "Music": {"format": "play music {value}"},
        "Sound": {"format": "play sound {value}"}
    }

    @property
    def category(self):
        return "music"

    @property
    def priority(self):
        return 10

    def process(self, data):
        commands = []
        if "Music" in data:
            commands.append(f"play music {data['Music']}")
        if "Sound" in data:
            commands.append(f"play sound {data['Sound']}")
        return commands if commands else None


class MockSceneGenerator(BaseSentenceGenerator):
    """测试场景生成器"""

    param_config = {
        "Background": {"format": "scene {value}"},
        "Character": {"format": "show {value}"}
    }

    @property
    def category(self):
        return "scene"

    @property
    def priority(self):
        return 5

    def process(self, data):
        commands = []
        if "Background" in data:
            commands.append(f"scene {data['Background']}")
        if "Character" in data:
            commands.append(f"show {data['Character']}")
        return commands if commands else None


class MockDialogueGenerator(BaseSentenceGenerator):
    """测试对话生成器"""

    param_config = {
        "Speaker": {"format": "{value}"},
        "Text": {"format": "\"{value}\""}
    }

    @property
    def category(self):
        return "dialogue"

    @property
    def priority(self):
        return 20

    def process(self, data):
        if "Speaker" in data and "Text" in data:
            return [f"{data['Speaker']} \"{data['Text']}\""]
        return None


class BrokenGenerator(BaseSentenceGenerator):
    """会抛出异常的生成器"""

    param_config = {
        "Broken": {"format": "{value}"}
    }

    @property
    def category(self):
        return "broken"

    @property
    def priority(self):
        return 30

    def process(self, data):
        raise ValueError("Intentional error for testing")


class TestEngineProcessor:
    """测试 EngineProcessor 类"""

    @pytest.fixture
    def mock_translator(self):
        """创建模拟翻译器"""
        return Mock(spec=ParamTranslator)

    @pytest.fixture
    def mock_config(self):
        """创建模拟配置"""
        config = Mock(spec=EngineConfig)
        config.engine_type = "test_engine"
        config.file_extension = ".test"
        return config

    @pytest.fixture
    def mock_generator_manager(self):
        """创建模拟生成器管理器"""
        manager = Mock(spec=SentenceGeneratorManager)
        manager.load = Mock()
        return manager

    @pytest.fixture
    def processor(self, mock_translator, mock_config):
        """创建处理器实例"""
        with patch('core.engine_processor.SentenceGeneratorManager') as MockManager:
            mock_manager = Mock(spec=SentenceGeneratorManager)
            mock_manager.load = Mock()
            MockManager.return_value = mock_manager

            processor = EngineProcessor("test_engine", mock_translator, mock_config)
            return processor

    def test_init(self, mock_translator, mock_config):
        """测试初始化"""
        with patch('core.engine_processor.SentenceGeneratorManager') as MockManager:
            mock_manager = Mock(spec=SentenceGeneratorManager)
            mock_manager.load = Mock()
            MockManager.return_value = mock_manager

            processor = EngineProcessor("test_engine", mock_translator, mock_config)

            assert processor.engine_type == "test_engine"
            assert processor.translator == mock_translator
            assert processor.engine_config == mock_config
            assert processor.generators == []
            assert processor.generator_param_map == {}
            mock_manager.load.assert_called_once()

    def test_setup(self, processor, mock_translator, mock_config):
        """测试设置处理器"""
        # 创建模拟生成器实例
        mock_gen1 = MockMusicGenerator(mock_translator, mock_config)
        mock_gen2 = MockSceneGenerator(mock_translator, mock_config)

        # 设置 generator_manager 的返回值
        processor.generator_manager.create_generator_instances = Mock(
            return_value=[mock_gen1, mock_gen2]
        )

        processor.setup()

        # 验证生成器已创建
        assert len(processor.generators) == 2
        assert processor.generators[0] == mock_gen1
        assert processor.generators[1] == mock_gen2

        # 验证参数映射已构建
        assert len(processor.generator_param_map) == 2
        assert mock_gen1 in processor.generator_param_map
        assert mock_gen2 in processor.generator_param_map

    def test_build_generator_param_map(self, processor, mock_translator, mock_config):
        """测试构建生成器参数映射"""
        # 创建生成器
        gen1 = MockMusicGenerator(mock_translator, mock_config)
        gen2 = MockSceneGenerator(mock_translator, mock_config)

        processor.generators = [gen1, gen2]
        param_map = processor._build_generator_param_map()

        # 验证映射
        assert gen1 in param_map
        assert gen2 in param_map
        assert "Music" in param_map[gen1]
        assert "Sound" in param_map[gen1]
        assert "Background" in param_map[gen2]
        assert "Character" in param_map[gen2]

    def test_build_generator_param_map_no_param_config(self, processor, mock_translator, mock_config):
        """测试构建参数映射（生成器没有 param_config）"""
        # 创建一个没有 param_config 的生成器
        class NoConfigGenerator(BaseSentenceGenerator):
            @property
            def category(self):
                return "no_config"

            def process(self, data):
                return []

        gen = NoConfigGenerator(mock_translator, mock_config)
        processor.generators = [gen]

        param_map = processor._build_generator_param_map()

        # 应该有映射，但参数列表为空
        assert gen in param_map
        assert param_map[gen] == []

    def test_build_generator_param_map_none_param_config(self, processor, mock_translator, mock_config):
        """测试构建参数映射（param_config 为 None）"""
        # 创建一个 param_config 为 None 的生成器
        class NoneConfigGenerator(BaseSentenceGenerator):
            param_config = None

            @property
            def category(self):
                return "none_config"

            def process(self, data):
                return []

        gen = NoneConfigGenerator(mock_translator, mock_config)
        processor.generators = [gen]

        param_map = processor._build_generator_param_map()

        # 应该有映射，但参数列表为空
        assert gen in param_map
        assert param_map[gen] == []


class TestProcessRow:
    """测试 process_row 方法"""

    @pytest.fixture
    def mock_translator(self):
        """创建模拟翻译器"""
        return Mock(spec=ParamTranslator)

    @pytest.fixture
    def mock_config(self):
        """创建模拟配置"""
        config = Mock(spec=EngineConfig)
        config.engine_type = "test_engine"
        return config

    @pytest.fixture
    def processor_with_generators(self, mock_translator, mock_config):
        """创建带有生成器的处理器"""
        with patch('core.engine_processor.SentenceGeneratorManager') as MockManager:
            mock_manager = Mock(spec=SentenceGeneratorManager)
            mock_manager.load = Mock()
            MockManager.return_value = mock_manager

            processor = EngineProcessor("test_engine", mock_translator, mock_config)

            # 手动设置生成器
            gen1 = MockSceneGenerator(mock_translator, mock_config)
            gen2 = MockMusicGenerator(mock_translator, mock_config)
            gen3 = MockDialogueGenerator(mock_translator, mock_config)

            processor.generators = [gen1, gen2, gen3]
            processor.generator_param_map = processor._build_generator_param_map()

            return processor

    def test_process_row_with_all_params(self, processor_with_generators):
        """测试处理包含所有参数的行"""
        row_data = pd.Series({
            "Background": "bg_room",
            "Character": "alice",
            "Music": "bgm_main",
            "Sound": "sfx_door",
            "Speaker": "Alice",
            "Text": "Hello!"
        })

        results = processor_with_generators.process_row(row_data)

        # 验证所有生成器都生成了命令
        assert len(results) > 0
        assert "scene bg_room" in results
        assert "show alice" in results
        assert "play music bgm_main" in results
        assert "play sound sfx_door" in results
        assert "Alice \"Hello!\"" in results

    def test_process_row_with_partial_params(self, processor_with_generators):
        """测试处理部分参数的行"""
        row_data = pd.Series({
            "Background": "bg_room",
            "Music": "bgm_main"
        })

        results = processor_with_generators.process_row(row_data)

        # 只有相关生成器生成命令
        assert len(results) == 2
        assert "scene bg_room" in results
        assert "play music bgm_main" in results

    def test_process_row_with_empty_values(self, processor_with_generators):
        """测试处理包含空值的行"""
        row_data = pd.Series({
            "Background": "bg_room",
            "Character": "",  # 空字符串
            "Music": None,  # None
            "Speaker": "Alice",
            "Text": ""  # 空字符串
        })

        results = processor_with_generators.process_row(row_data)

        # 只有非空值生成命令
        assert len(results) == 1
        assert "scene bg_room" in results

    def test_process_row_with_nan_values(self, processor_with_generators):
        """测试处理包含 NaN 值的行"""
        row_data = pd.Series({
            "Background": "bg_room",
            "Character": pd.NA,  # pandas NA
            "Music": float('nan'),  # NaN
            "Sound": "sfx_door"
        })

        results = processor_with_generators.process_row(row_data)

        # NaN 值应该被过滤
        assert "scene bg_room" in results
        assert "play sound sfx_door" in results
        assert len(results) == 2

    def test_process_row_with_no_matching_params(self, processor_with_generators):
        """测试处理没有匹配参数的行"""
        row_data = pd.Series({
            "UnknownParam1": "value1",
            "UnknownParam2": "value2"
        })

        results = processor_with_generators.process_row(row_data)

        # 没有生成器能处理这些参数
        assert results == []

    def test_process_row_with_generator_error(self, mock_translator, mock_config):
        """测试生成器抛出异常时的处理"""
        with patch('core.engine_processor.SentenceGeneratorManager') as MockManager:
            mock_manager = Mock(spec=SentenceGeneratorManager)
            mock_manager.load = Mock()
            MockManager.return_value = mock_manager

            processor = EngineProcessor("test_engine", mock_translator, mock_config)

            # 添加一个正常生成器和一个会出错的生成器
            gen1 = MockMusicGenerator(mock_translator, mock_config)
            gen2 = BrokenGenerator(mock_translator, mock_config)

            processor.generators = [gen1, gen2]
            processor.generator_param_map = processor._build_generator_param_map()

            row_data = pd.Series({
                "Music": "bgm_main",
                "Broken": "test"
            })

            # 应该捕获异常并继续处理
            results = processor.process_row(row_data)

            # 正常生成器应该生成命令
            assert "play music bgm_main" in results
            # 出错的生成器不应该影响结果
            assert len(results) == 1

    def test_process_row_empty_row(self, processor_with_generators):
        """测试处理空行"""
        row_data = pd.Series({})

        results = processor_with_generators.process_row(row_data)

        assert results == []

    @pytest.mark.parametrize("return_value,category_name", [
        (None, "none"),
        ([], "empty"),
    ])
    def test_process_row_generator_returns_empty(self, mock_translator, mock_config, return_value, category_name):
        """测试生成器返回 None 或空列表的情况"""
        with patch('core.engine_processor.SentenceGeneratorManager') as MockManager:
            mock_manager = Mock(spec=SentenceGeneratorManager)
            mock_manager.load = Mock()
            MockManager.return_value = mock_manager

            processor = EngineProcessor("test_engine", mock_translator, mock_config)

            # 创建一个返回指定值的生成器
            class TestGenerator(BaseSentenceGenerator):
                param_config = {"Test": {}}

                @property
                def category(self):
                    return category_name

                def process(self, data):
                    return return_value

            gen = TestGenerator(mock_translator, mock_config)
            processor.generators = [gen]
            processor.generator_param_map = processor._build_generator_param_map()

            row_data = pd.Series({"Test": "value"})
            results = processor.process_row(row_data)

            # 返回 None 或空列表的生成器不应该添加到结果中
            assert results == []


class TestPipelineInfo:
    """测试管道信息相关方法"""

    @pytest.fixture
    def mock_translator(self):
        """创建模拟翻译器"""
        return Mock(spec=ParamTranslator)

    @pytest.fixture
    def mock_config(self):
        """创建模拟配置"""
        config = Mock(spec=EngineConfig)
        config.engine_type = "test_engine"
        return config

    @pytest.fixture
    def processor_with_generators(self, mock_translator, mock_config):
        """创建带有生成器的处理器"""
        with patch('core.engine_processor.SentenceGeneratorManager') as MockManager:
            mock_manager = Mock(spec=SentenceGeneratorManager)
            mock_manager.load = Mock()
            MockManager.return_value = mock_manager

            processor = EngineProcessor("test_engine", mock_translator, mock_config)

            # 按优先级顺序添加生成器
            gen1 = MockSceneGenerator(mock_translator, mock_config)  # priority=5
            gen2 = MockMusicGenerator(mock_translator, mock_config)  # priority=10
            gen3 = MockDialogueGenerator(mock_translator, mock_config)  # priority=20

            processor.generators = [gen1, gen2, gen3]
            processor.generator_param_map = processor._build_generator_param_map()

            return processor

    def test_get_pipeline_info(self, processor_with_generators):
        """测试获取管道信息"""
        info = processor_with_generators.get_pipeline_info()

        # 验证基本信息
        assert "total_stages" in info
        assert "pipeline" in info
        assert info["total_stages"] == 3

        # 验证管道详情
        pipeline = info["pipeline"]
        assert len(pipeline) == 3

        # 验证第一个阶段
        assert pipeline[0]["stage"] == 1
        assert pipeline[0]["name"] == "MockSceneGenerator"
        assert pipeline[0]["type"] == "scene"
        assert pipeline[0]["priority"] == 5

        # 验证第二个阶段
        assert pipeline[1]["stage"] == 2
        assert pipeline[1]["name"] == "MockMusicGenerator"
        assert pipeline[1]["type"] == "music"
        assert pipeline[1]["priority"] == 10

        # 验证第三个阶段
        assert pipeline[2]["stage"] == 3
        assert pipeline[2]["name"] == "MockDialogueGenerator"
        assert pipeline[2]["type"] == "dialogue"
        assert pipeline[2]["priority"] == 20

    def test_get_pipeline_info_empty(self, mock_translator, mock_config):
        """测试获取空管道信息"""
        with patch('core.engine_processor.SentenceGeneratorManager') as MockManager:
            mock_manager = Mock(spec=SentenceGeneratorManager)
            mock_manager.load = Mock()
            MockManager.return_value = mock_manager

            processor = EngineProcessor("test_engine", mock_translator, mock_config)
            processor.generators = []

            info = processor.get_pipeline_info()

            assert info["total_stages"] == 0
            assert info["pipeline"] == []

    def test_get_pipeline_info_with_category(self, mock_translator, mock_config):
        """测试获取管道信息（验证 category 正确获取）"""
        with patch('core.engine_processor.SentenceGeneratorManager') as MockManager:
            mock_manager = Mock(spec=SentenceGeneratorManager)
            mock_manager.load = Mock()
            MockManager.return_value = mock_manager

            processor = EngineProcessor("test_engine", mock_translator, mock_config)

            # 创建一个有 category 的生成器
            gen = MockMusicGenerator(mock_translator, mock_config)
            processor.generators = [gen]

            info = processor.get_pipeline_info()

            # 验证 category 被正确获取
            assert info["pipeline"][0]["type"] == "music"
            assert info["pipeline"][0]["name"] == "MockMusicGenerator"

    def test_get_generator_manager(self, processor_with_generators):
        """测试获取生成器管理器"""
        manager = processor_with_generators.get_generator_manager()

        assert manager is not None
        assert isinstance(manager, (SentenceGeneratorManager, Mock))


class TestEngineProcessorIntegration:
    """集成测试：测试完整的工作流程"""

    @pytest.fixture
    def mock_translator(self):
        """创建模拟翻译器"""
        return Mock(spec=ParamTranslator)

    @pytest.fixture
    def mock_config(self):
        """创建模拟配置"""
        config = Mock(spec=EngineConfig)
        config.engine_type = "test_engine"
        return config

    def test_full_workflow(self, mock_translator, mock_config):
        """测试完整工作流程"""
        with patch('core.engine_processor.SentenceGeneratorManager') as MockManager:
            mock_manager = Mock(spec=SentenceGeneratorManager)
            mock_manager.load = Mock()

            # 创建生成器实例
            gen1 = MockSceneGenerator(mock_translator, mock_config)
            gen2 = MockMusicGenerator(mock_translator, mock_config)
            gen3 = MockDialogueGenerator(mock_translator, mock_config)

            mock_manager.create_generator_instances = Mock(
                return_value=[gen1, gen2, gen3]
            )
            MockManager.return_value = mock_manager

            # 1. 初始化处理器
            processor = EngineProcessor("test_engine", mock_translator, mock_config)
            assert processor.engine_type == "test_engine"

            # 2. 设置处理器
            processor.setup()
            assert len(processor.generators) == 3

            # 3. 获取管道信息
            info = processor.get_pipeline_info()
            assert info["total_stages"] == 3

            # 4. 处理多行数据
            rows = [
                pd.Series({"Background": "bg1", "Music": "bgm1"}),
                pd.Series({"Character": "alice", "Speaker": "Alice", "Text": "Hi"}),
                pd.Series({"Sound": "sfx1"})
            ]

            all_results = []
            for row in rows:
                results = processor.process_row(row)
                all_results.extend(results)

            # 验证所有命令都生成了
            assert len(all_results) > 0
            assert any("scene bg1" in cmd for cmd in all_results)
            assert any("play music bgm1" in cmd for cmd in all_results)
            assert any("show alice" in cmd for cmd in all_results)
            assert any("Alice \"Hi\"" in cmd for cmd in all_results)
            assert any("play sound sfx1" in cmd for cmd in all_results)

    def test_multiple_rows_processing(self, mock_translator, mock_config):
        """测试处理多行数据"""
        with patch('core.engine_processor.SentenceGeneratorManager') as MockManager:
            mock_manager = Mock(spec=SentenceGeneratorManager)
            mock_manager.load = Mock()

            gen = MockMusicGenerator(mock_translator, mock_config)
            mock_manager.create_generator_instances = Mock(return_value=[gen])
            MockManager.return_value = mock_manager

            processor = EngineProcessor("test_engine", mock_translator, mock_config)
            processor.setup()

            # 处理多行
            rows = [
                pd.Series({"Music": "bgm1"}),
                pd.Series({"Music": "bgm2"}),
                pd.Series({"Sound": "sfx1"}),
            ]

            results = [processor.process_row(row) for row in rows]

            # 验证每行都被正确处理
            assert len(results) == 3
            assert "play music bgm1" in results[0]
            assert "play music bgm2" in results[1]
            assert "play sound sfx1" in results[2]
