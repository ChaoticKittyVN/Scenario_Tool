"""
配置管理模块
提供类型安全的配置管理功能
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import yaml
from core.logger import get_logger

logger = get_logger()


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


def _create_engine_config(engine_type: str, engine_data: Optional[Dict[str, Any]] = None) -> EngineConfig:
    """
    通过引擎注册表创建引擎配置实例

    Args:
        engine_type: 引擎类型
        engine_data: 引擎配置数据字典（可选）

    Returns:
        EngineConfig: 引擎配置实例

    Raises:
        ValueError: 引擎未注册或无法创建配置
    """
    # 延迟导入以避免循环导入
    from core.engine_registry import EngineRegistry
    
    # 如果引擎未注册，尝试动态导入
    if not EngineRegistry.is_registered(engine_type):
        # 尝试动态导入引擎模块
        engine_module_map = {
            "renpy": "engines.renpy",
            "naninovel": "engines.naninovel",
            "utage": "engines.utage"
        }
        if engine_type in engine_module_map:
            try:
                __import__(engine_module_map[engine_type])
            except ImportError as e:
                logger.warning(f"无法导入引擎模块 {engine_module_map[engine_type]}: {e}")

    # 从注册表获取引擎元数据
    try:
        engine_meta = EngineRegistry.get(engine_type)
    except Exception as e:
        raise ValueError(f"无法获取引擎 '{engine_type}' 的配置类: {e}")

    # 创建配置实例
    config_class = engine_meta.config_class
    
    # 如果提供了配置数据，使用数据创建；否则使用默认值
    if engine_data and isinstance(engine_data, dict):
        # 过滤掉engine_type，因为它是类属性
        filtered_data = {k: v for k, v in engine_data.items() if k != 'engine_type'}
        engine = config_class(**filtered_data)
    else:
        engine = config_class()

    return engine

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
    engine: EngineConfig = field(default_factory=lambda: _create_engine_config("renpy"))
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
            engine_data = {}
        else:
            engine_type = engine_data.get('engine_type', 'renpy')

        # 通过引擎注册表动态创建配置实例
        engine = _create_engine_config(engine_type, engine_data)

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
            },
            'resources': {
                'project_root': str(self.resources.project_root),
                'source_root': str(self.resources.source_root),
                'extensions': self.resources.extensions,
            }
        }

        # 将引擎配置的所有字段添加到engine字典中
        # 使用dataclasses.fields获取所有字段
        from dataclasses import fields
        for field_info in fields(self.engine):
            if field_info.name != 'engine_type':  # engine_type已经在上面添加了
                value = getattr(self.engine, field_info.name)
                # 处理Path对象和复杂对象
                if isinstance(value, Path):
                    data['engine'][field_info.name] = str(value)
                elif isinstance(value, (list, dict)):
                    data['engine'][field_info.name] = value
                else:
                    data['engine'][field_info.name] = value

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
        engine = _create_engine_config(engine_type)

        return cls(
            paths=PathConfig(),
            processing=ProcessingConfig(),
            engine=engine,
            resources=ResourceConfig()
        )


# 向后兼容：提供从引擎模块导入配置类的快捷方式
# 这样现有代码仍然可以使用 from core.config_manager import RenpyConfig
def __getattr__(name: str):
    """
    动态导入引擎配置类以提供向后兼容性
    
    支持的名称：
    - RenpyConfig
    - NaninovelConfig
    - UtageConfig
    """
    engine_config_map = {
        'RenpyConfig': 'engines.renpy.config',
        'NaninovelConfig': 'engines.naninovel.config',
        'UtageConfig': 'engines.utage.config',
    }
    
    if name in engine_config_map:
        module_path = engine_config_map[name]
        try:
            module = __import__(module_path, fromlist=[name])
            return getattr(module, name)
        except (ImportError, AttributeError) as e:
            raise AttributeError(
                f"无法导入 {name}。请使用 'from {module_path} import {name}' 或确保引擎模块已正确安装。"
            ) from e
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
