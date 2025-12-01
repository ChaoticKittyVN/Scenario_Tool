"""
配置管理模块
提供类型安全的配置管理功能
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import yaml


@dataclass
class PathConfig:
    """路径配置"""
    input_dir: Path = Path("./input")
    output_dir: Path = Path("./output")
    param_config_dir: Path = Path("./param_config")
    log_dir: Path = Path("./logs")

    def __post_init__(self):
        """确保路径是 Path 对象"""
        self.input_dir = Path(self.input_dir)
        self.output_dir = Path(self.output_dir)
        self.param_config_dir = Path(self.param_config_dir)
        self.log_dir = Path(self.log_dir)

    def ensure_dirs_exist(self):
        """确保所有目录存在"""
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.param_config_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class ProcessingConfig:
    """处理配置"""
    ignore_mode: bool = True
    ignore_words: List[str] = field(default_factory=lambda: [""])
    batch_size: int = 100
    enable_progress_bar: bool = True


@dataclass
class EngineConfig:
    """引擎配置基类"""
    engine_type: str
    file_extension: str
    indent_size: int = 0

    def get_output_filename(self, sheet_name: str) -> str:
        """
        生成输出文件名

        Args:
            sheet_name: 工作表名称

        Returns:
            str: 输出文件名
        """
        return f"{sheet_name}{self.file_extension}"


@dataclass
class RenpyConfig(EngineConfig):
    """Ren'Py 引擎配置"""
    engine_type: str = "renpy"
    file_extension: str = ".rpy"
    indent_size: int = 4
    label_indent: bool = False
    default_transition: str = "dissolve"


@dataclass
class NaninovelConfig(EngineConfig):
    """Naninovel 引擎配置"""
    engine_type: str = "naninovel"
    file_extension: str = ".nani"
    command_prefix: str = "@"


@dataclass
class ResourceConfig:
    """资源配置"""
    project_root: Path = Path("./project")
    source_root: Path = Path("./resource_library")
    extensions: Dict[str, List[str]] = field(default_factory=lambda: {
        "图片": [".png", ".jpg", ".jpeg", ".webp"],
        "音频": [".ogg", ".mp3", ".wav", ".m4a"],
        "视频": [".mp4", ".webm", ".ogv"]
    })

    def __post_init__(self):
        """确保路径是 Path 对象"""
        self.project_root = Path(self.project_root)
        self.source_root = Path(self.source_root)


@dataclass
class AppConfig:
    """应用总配置"""
    paths: PathConfig = field(default_factory=PathConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    engine: EngineConfig = field(default_factory=NaninovelConfig)
    resources: ResourceConfig = field(default_factory=ResourceConfig)

    @classmethod
    def from_file(cls, config_path: Path) -> 'AppConfig':
        """
        从配置文件加载

        Args:
            config_path: 配置文件路径

        Returns:
            AppConfig: 配置对象

        Raises:
            ValueError: 不支持的配置文件格式
        """
        config_path = Path(config_path)

        if config_path.suffix == '.json':
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        elif config_path.suffix in ['.yaml', '.yml']:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        else:
            raise ValueError(f"不支持的配置文件格式: {config_path.suffix}")

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppConfig':
        """
        从字典创建配置

        Args:
            data: 配置字典

        Returns:
            AppConfig: 配置对象
        """
        paths = PathConfig(**data.get('paths', {}))
        processing = ProcessingConfig(**data.get('processing', {}))
        resources = ResourceConfig(**data.get('resources', {}))

        # 根据引擎类型创建对应配置
        engine_data = data.get('engine', {})

        # 如果只提供了 engine_type，使用默认配置
        if isinstance(engine_data, str):
            engine_type = engine_data
        else:
            engine_type = engine_data.get('engine_type', 'naninovel')

        # 根据引擎类型创建默认配置，然后用用户提供的值覆盖
        if engine_type == 'renpy':
            engine = RenpyConfig()
            # 只覆盖用户明确提供的配置项
            if isinstance(engine_data, dict):
                for key, value in engine_data.items():
                    if hasattr(engine, key) and key != 'engine_type':
                        setattr(engine, key, value)
        elif engine_type == 'naninovel':
            engine = NaninovelConfig()
            if isinstance(engine_data, dict):
                for key, value in engine_data.items():
                    if hasattr(engine, key) and key != 'engine_type':
                        setattr(engine, key, value)
        else:
            raise ValueError(f"不支持的引擎类型: {engine_type}")

        return cls(paths=paths, processing=processing, engine=engine, resources=resources)

    def to_file(self, config_path: Path):
        """
        保存到配置文件

        Args:
            config_path: 配置文件路径
        """
        config_path = Path(config_path)

        data = {
            'paths': {
                'input_dir': str(self.paths.input_dir),
                'output_dir': str(self.paths.output_dir),
                'param_config_dir': str(self.paths.param_config_dir),
                'log_dir': str(self.paths.log_dir),
            },
            'processing': {
                'ignore_mode': self.processing.ignore_mode,
                'ignore_words': self.processing.ignore_words,
                'batch_size': self.processing.batch_size,
                'enable_progress_bar': self.processing.enable_progress_bar,
            },
            'engine': {
                'engine_type': self.engine.engine_type,
                'file_extension': self.engine.file_extension,
                'indent_size': self.engine.indent_size,
            },
            'resources': {
                'project_root': str(self.resources.project_root),
                'source_root': str(self.resources.source_root),
                'extensions': self.resources.extensions,
            }
        }

        # 添加引擎特定配置
        if isinstance(self.engine, RenpyConfig):
            data['engine']['label_indent'] = self.engine.label_indent
            data['engine']['default_transition'] = self.engine.default_transition
        elif isinstance(self.engine, NaninovelConfig):
            data['engine']['command_prefix'] = self.engine.command_prefix

        if config_path.suffix == '.json':
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        elif config_path.suffix in ['.yaml', '.yml']:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, allow_unicode=True)

    @classmethod
    def create_default(cls, engine_type: str = "naninovel") -> 'AppConfig':
        """
        创建默认配置

        Args:
            engine_type: 引擎类型

        Returns:
            AppConfig: 默认配置对象
        """
        if engine_type == "renpy":
            engine = RenpyConfig()
        elif engine_type == "naninovel":
            engine = NaninovelConfig()
        else:
            raise ValueError(f"不支持的引擎类型: {engine_type}")

        return cls(
            paths=PathConfig(),
            processing=ProcessingConfig(),
            engine=engine,
            resources=ResourceConfig()
        )
