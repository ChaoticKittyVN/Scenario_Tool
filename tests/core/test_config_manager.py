"""
测试 ConfigManager 模块
"""
import pytest
import json
import yaml
from pathlib import Path
from core.config_manager import (
    PathConfig,
    ProcessingConfig,
    EngineConfig,
    RenpyConfig,
    NaninovelConfig,
    AppConfig
)


class TestPathConfig:
    """测试 PathConfig 类"""

    def test_default_paths(self):
        """测试默认路径"""
        config = PathConfig()
        assert config.input_dir == Path("./input")
        assert config.output_dir == Path("./output")
        assert config.param_config_dir == Path("./param_config")
        assert config.log_dir == Path("./logs")

    def test_custom_paths(self):
        """测试自定义路径"""
        config = PathConfig(
            input_dir=Path("./custom_input"),
            output_dir=Path("./custom_output"),
            param_config_dir=Path("./custom_param"),
            log_dir=Path("./custom_logs")
        )
        assert config.input_dir == Path("./custom_input")
        assert config.output_dir == Path("./custom_output")
        assert config.param_config_dir == Path("./custom_param")
        assert config.log_dir == Path("./custom_logs")

    def test_post_init_converts_to_path(self):
        """测试 __post_init__ 将字符串转换为 Path 对象"""
        config = PathConfig(
            input_dir="./string_input",
            output_dir="./string_output"
        )
        assert isinstance(config.input_dir, Path)
        assert isinstance(config.output_dir, Path)

    def test_ensure_dirs_exist(self, tmp_path):
        """测试创建目录"""
        config = PathConfig(
            input_dir=tmp_path / "input",
            output_dir=tmp_path / "output",
            param_config_dir=tmp_path / "param_config",
            log_dir=tmp_path / "logs"
        )

        # 确保目录不存在
        assert not config.input_dir.exists()
        assert not config.output_dir.exists()

        # 创建目录
        config.ensure_dirs_exist()

        # 验证目录已创建
        assert config.input_dir.exists()
        assert config.output_dir.exists()
        assert config.param_config_dir.exists()
        assert config.log_dir.exists()


class TestProcessingConfig:
    """测试 ProcessingConfig 类"""

    def test_default_config(self):
        """测试默认配置"""
        config = ProcessingConfig()
        assert config.ignore_mode is True
        assert config.ignore_words == [""]
        assert config.batch_size == 100
        assert config.enable_progress_bar is True

    def test_custom_config(self):
        """测试自定义配置"""
        config = ProcessingConfig(
            ignore_mode=False,
            ignore_words=["test", "ignore"],
            batch_size=50,
            enable_progress_bar=False
        )
        assert config.ignore_mode is False
        assert config.ignore_words == ["test", "ignore"]
        assert config.batch_size == 50
        assert config.enable_progress_bar is False


class TestEngineConfig:
    """测试 EngineConfig 基类"""

    def test_get_output_filename(self):
        """测试生成输出文件名"""
        config = EngineConfig(
            engine_type="test",
            file_extension=".txt"
        )
        assert config.get_output_filename("chapter1") == "chapter1.txt"
        assert config.get_output_filename("scene_01") == "scene_01.txt"


class TestRenpyConfig:
    """测试 RenpyConfig 类"""

    def test_default_config(self):
        """测试默认配置"""
        config = RenpyConfig()
        assert config.engine_type == "renpy"
        assert config.file_extension == ".rpy"
        assert config.indent_size == 4
        assert config.label_indent is False
        assert config.default_transition == "dissolve"

    def test_get_output_filename(self):
        """测试生成输出文件名"""
        config = RenpyConfig()
        assert config.get_output_filename("script") == "script.rpy"


class TestNaninovelConfig:
    """测试 NaninovelConfig 类"""

    def test_default_config(self):
        """测试默认配置"""
        config = NaninovelConfig()
        assert config.engine_type == "naninovel"
        assert config.file_extension == ".nani"
        assert config.command_prefix == "@"

    def test_get_output_filename(self):
        """测试生成输出文件名"""
        config = NaninovelConfig()
        assert config.get_output_filename("chapter1") == "chapter1.nani"


class TestAppConfig:
    """测试 AppConfig 类"""

    def test_default_config(self):
        """测试默认配置"""
        config = AppConfig()
        assert isinstance(config.paths, PathConfig)
        assert isinstance(config.processing, ProcessingConfig)
        assert isinstance(config.engine, NaninovelConfig)

    def test_create_default_naninovel(self):
        """测试创建默认 Naninovel 配置"""
        config = AppConfig.create_default("naninovel")
        assert isinstance(config.engine, NaninovelConfig)
        assert config.engine.engine_type == "naninovel"

    def test_create_default_renpy(self):
        """测试创建默认 Ren'Py 配置"""
        config = AppConfig.create_default("renpy")
        assert isinstance(config.engine, RenpyConfig)
        assert config.engine.engine_type == "renpy"

    def test_create_default_invalid_engine(self):
        """测试创建不支持的引擎配置"""
        with pytest.raises(ValueError, match="不支持的引擎类型"):
            AppConfig.create_default("invalid_engine")

    def test_from_dict_minimal(self):
        """测试从最小字典创建配置"""
        data = {}
        config = AppConfig.from_dict(data)
        assert isinstance(config.paths, PathConfig)
        assert isinstance(config.processing, ProcessingConfig)
        assert isinstance(config.engine, NaninovelConfig)

    def test_from_dict_with_paths(self):
        """测试从包含路径的字典创建配置"""
        data = {
            'paths': {
                'input_dir': './test_input',
                'output_dir': './test_output'
            }
        }
        config = AppConfig.from_dict(data)
        assert config.paths.input_dir == Path('./test_input')
        assert config.paths.output_dir == Path('./test_output')

    def test_from_dict_with_processing(self):
        """测试从包含处理配置的字典创建配置"""
        data = {
            'processing': {
                'ignore_mode': False,
                'batch_size': 50
            }
        }
        config = AppConfig.from_dict(data)
        assert config.processing.ignore_mode is False
        assert config.processing.batch_size == 50

    def test_from_dict_with_renpy_engine(self):
        """测试从字典创建 Ren'Py 引擎配置"""
        data = {
            'engine': {
                'engine_type': 'renpy',
                'indent_size': 2,
                'default_transition': 'fade'
            }
        }
        config = AppConfig.from_dict(data)
        assert isinstance(config.engine, RenpyConfig)
        assert config.engine.engine_type == 'renpy'
        assert config.engine.indent_size == 2
        assert config.engine.default_transition == 'fade'

    def test_from_dict_with_naninovel_engine(self):
        """测试从字典创建 Naninovel 引擎配置"""
        data = {
            'engine': {
                'engine_type': 'naninovel',
                'command_prefix': '#'
            }
        }
        config = AppConfig.from_dict(data)
        assert isinstance(config.engine, NaninovelConfig)
        assert config.engine.command_prefix == '#'

    def test_from_dict_with_engine_string(self):
        """测试从字符串引擎类型创建配置"""
        data = {
            'engine': 'renpy'
        }
        config = AppConfig.from_dict(data)
        assert isinstance(config.engine, RenpyConfig)
        assert config.engine.engine_type == 'renpy'

    def test_from_dict_invalid_engine(self):
        """测试从字典创建不支持的引擎配置"""
        data = {
            'engine': {
                'engine_type': 'invalid'
            }
        }
        with pytest.raises(ValueError, match="不支持的引擎类型"):
            AppConfig.from_dict(data)

    def test_from_file_json(self, tmp_path):
        """测试从 JSON 文件加载配置"""
        config_file = tmp_path / "config.json"
        data = {
            'paths': {
                'input_dir': './json_input'
            },
            'engine': {
                'engine_type': 'renpy'
            }
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f)

        config = AppConfig.from_file(config_file)
        assert config.paths.input_dir == Path('./json_input')
        assert isinstance(config.engine, RenpyConfig)

    def test_from_file_yaml(self, tmp_path):
        """测试从 YAML 文件加载配置"""
        config_file = tmp_path / "config.yaml"
        data = {
            'paths': {
                'input_dir': './yaml_input'
            },
            'engine': {
                'engine_type': 'naninovel'
            }
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f)

        config = AppConfig.from_file(config_file)
        assert config.paths.input_dir == Path('./yaml_input')
        assert isinstance(config.engine, NaninovelConfig)

    def test_from_file_yml_extension(self, tmp_path):
        """测试从 .yml 文件加载配置"""
        config_file = tmp_path / "config.yml"
        data = {
            'engine': {
                'engine_type': 'renpy'
            }
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f)

        config = AppConfig.from_file(config_file)
        assert isinstance(config.engine, RenpyConfig)

    def test_from_file_invalid_format(self, tmp_path):
        """测试从不支持的文件格式加载配置"""
        config_file = tmp_path / "config.txt"
        config_file.write_text("invalid config")

        with pytest.raises(ValueError, match="不支持的配置文件格式"):
            AppConfig.from_file(config_file)

    def test_to_file_json(self, tmp_path):
        """测试保存配置到 JSON 文件"""
        config = AppConfig.create_default("renpy")
        config.paths.input_dir = Path("./test_input")
        config.processing.batch_size = 50

        config_file = tmp_path / "output.json"
        config.to_file(config_file)

        # 验证文件已创建
        assert config_file.exists()

        # 验证文件内容
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert Path(data['paths']['input_dir']) == Path('./test_input')
        assert data['processing']['batch_size'] == 50
        assert data['engine']['engine_type'] == 'renpy'
        assert data['engine']['label_indent'] is False
        assert data['engine']['default_transition'] == 'dissolve'

    def test_to_file_yaml(self, tmp_path):
        """测试保存配置到 YAML 文件"""
        config = AppConfig.create_default("naninovel")
        config.paths.output_dir = Path("./test_output")
        config.processing.ignore_mode = False

        config_file = tmp_path / "output.yaml"
        config.to_file(config_file)

        # 验证文件已创建
        assert config_file.exists()

        # 验证文件内容
        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        assert Path(data['paths']['output_dir']) == Path('./test_output')
        assert data['processing']['ignore_mode'] is False
        assert data['engine']['engine_type'] == 'naninovel'
        assert data['engine']['command_prefix'] == '@'

    def test_to_file_yml_extension(self, tmp_path):
        """测试保存配置到 .yml 文件"""
        config = AppConfig.create_default("renpy")
        config_file = tmp_path / "output.yml"
        config.to_file(config_file)

        assert config_file.exists()

        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        assert data['engine']['engine_type'] == 'renpy'

    def test_roundtrip_json(self, tmp_path):
        """测试 JSON 配置的往返转换"""
        # 创建配置
        original = AppConfig.create_default("renpy")
        original.paths.input_dir = Path("./roundtrip_input")
        original.processing.batch_size = 75

        # 保存到文件
        config_file = tmp_path / "roundtrip.json"
        original.to_file(config_file)

        # 从文件加载
        loaded = AppConfig.from_file(config_file)

        # 验证配置一致
        assert loaded.paths.input_dir == original.paths.input_dir
        assert loaded.processing.batch_size == original.processing.batch_size
        assert loaded.engine.engine_type == original.engine.engine_type

    def test_roundtrip_yaml(self, tmp_path):
        """测试 YAML 配置的往返转换"""
        # 创建配置
        original = AppConfig.create_default("naninovel")
        original.paths.output_dir = Path("./roundtrip_output")
        original.processing.enable_progress_bar = False

        # 保存到文件
        config_file = tmp_path / "roundtrip.yaml"
        original.to_file(config_file)

        # 从文件加载
        loaded = AppConfig.from_file(config_file)

        # 验证配置一致
        assert loaded.paths.output_dir == original.paths.output_dir
        assert loaded.processing.enable_progress_bar == original.processing.enable_progress_bar
        assert loaded.engine.engine_type == original.engine.engine_type
