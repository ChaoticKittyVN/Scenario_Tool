"""
配置管理模块
提供类型安全的配置管理功能
"""
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import yaml
from core.logger import get_logger

logger = get_logger()


def _known_dataclass_values(config_class, values: Any) -> Dict[str, Any]:
    """只提取当前配置模型认识的字段，允许新版配置被旧 GUI 读取。"""
    if not isinstance(values, dict):
        return {}
    known_names = {field_info.name for field_info in fields(config_class)}
    return {key: value for key, value in values.items() if key in known_names}


def _deep_merge(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """递归合并配置字典，保留 updates 未涉及的字段。"""
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _read_config_data(config_path: Path) -> Dict[str, Any]:
    config_path = Path(config_path)
    if not config_path.exists():
        return {}
    if config_path.suffix == '.json':
        with open(config_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    elif config_path.suffix in ['.yaml', '.yml']:
        with open(config_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
    else:
        raise ValueError(f"不支持的配置文件格式: {config_path.suffix}")
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError("配置文件根节点必须是映射")
    return data


def _write_config_data(config_path: Path, data: Dict[str, Any]) -> None:
    config_path = Path(config_path)
    if config_path.suffix == '.json':
        with open(config_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
    elif config_path.suffix in ['.yaml', '.yml']:
        with open(config_path, 'w', encoding='utf-8') as file:
            yaml.safe_dump(data, file, allow_unicode=True, sort_keys=False)
    else:
        raise ValueError(f"不支持的配置文件格式: {config_path.suffix}")


@dataclass
class PathConfig:
    """路径配置"""
    input_dir: Path = Path("./input")
    output_dir: Path = Path("./output")
    param_config_dir: Path = Path("./param_config")
    log_dir: Path = Path("./logs")
    input_voice_dir: Path = Path("./input/voice")

    def __post_init__(self):
        """确保路径是 Path 对象"""
        self.input_dir = Path(self.input_dir)
        self.output_dir = Path(self.output_dir)
        self.param_config_dir = Path(self.param_config_dir)
        self.log_dir = Path(self.log_dir)
        self.input_voice_dir = Path(self.input_voice_dir)

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
    multi_project_mode: bool = False


@dataclass
class VariantAgentExportConfig:
    """Agent 差分文档导出配置。"""

    enabled: bool = False
    output_file: str = "variant_agent_data.json"
    group_columns: List[str] = field(default_factory=lambda: ["情绪"])
    item_key_column: str = "序号"
    alias_columns: List[str] = field(default_factory=lambda: ["适用情绪"])
    parameter_template: Optional[str] = "{情绪}{序号}"
    sheet_profiles: Dict[str, Dict[str, Any]] = field(default_factory=dict)


@dataclass
class EngineDiscoveryConfig:
    """控制项目允许使用的可选引擎。空列表表示使用全部已安装引擎。"""

    enabled: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.enabled is None:
            self.enabled = []
        if isinstance(self.enabled, str):
            self.enabled = [self.enabled]
        self.enabled = list(dict.fromkeys(str(name) for name in self.enabled))


@dataclass
class EngineConfig:
    """引擎配置基类"""
    engine_type: str
    file_extension: str
    indent_size: int = 0
    use_macro: bool = False

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
    from core.engine_loader import load_engine

    try:
        engine_meta = load_engine(engine_type)
    except Exception as e:
        raise ValueError(f"无法获取引擎 '{engine_type}' 的配置类: {e}")

    # 创建配置实例
    config_class = engine_meta.config_class
    
    # 如果提供了配置数据，使用数据创建；否则使用默认值
    if engine_data and isinstance(engine_data, dict):
        # 过滤掉engine_type，因为它是类属性
        filtered_data = _known_dataclass_values(config_class, engine_data)
        filtered_data.pop('engine_type', None)
        engine = config_class(**filtered_data)
    else:
        engine = config_class()

    return engine


def _create_default_engine_config(
    enabled: Optional[List[str]] = None,
) -> EngineConfig:
    from core.engine_loader import select_default_engine_name

    return _create_engine_config(select_default_engine_name(enabled))

@dataclass
class ResourceConfig:
    """资源配置"""
    project_root: Path = Path("./project")
    source_root: Path = Path("./resource_library")
    validate_source: bool = True
    filename_normalization: Dict[str, List[str]] = field(default_factory=dict)
    reference_sample_limit: int = 8
    extensions: Dict[str, List[str]] = field(default_factory=lambda: {
        "图片": [".png", ".jpg", ".jpeg", ".webp"],
        "音频": [".ogg", ".mp3", ".wav", ".m4a"],
        "视频": [".mp4", ".webm", ".ogv"]
    })

    def __post_init__(self):
        """确保路径是 Path 对象"""
        self.project_root = Path(self.project_root)
        self.source_root = Path(self.source_root)
        self.reference_sample_limit = max(0, int(self.reference_sample_limit))


@dataclass
class AppConfig:
    """应用总配置"""
    paths: PathConfig = field(default_factory=PathConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    engine: EngineConfig = field(default_factory=_create_default_engine_config)
    engines: EngineDiscoveryConfig = field(default_factory=EngineDiscoveryConfig)
    resources: ResourceConfig = field(default_factory=ResourceConfig)
    variant_agent_export: VariantAgentExportConfig = field(
        default_factory=VariantAgentExportConfig
    )
    projects: Dict[str, str] = field(default_factory=dict)

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

        return cls.from_dict(_read_config_data(config_path))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppConfig':
        """
        从字典创建配置

        Args:
            data: 配置字典

        Returns:
            AppConfig: 配置对象
        """
        if not isinstance(data, dict):
            raise ValueError("配置数据必须是映射")
        paths = PathConfig(**_known_dataclass_values(PathConfig, data.get('paths', {})))
        processing = ProcessingConfig(
            **_known_dataclass_values(ProcessingConfig, data.get('processing', {}))
        )
        engines = EngineDiscoveryConfig(
            **_known_dataclass_values(
                EngineDiscoveryConfig,
                data.get('engines', {}),
            )
        )
        resources = ResourceConfig(
            **_known_dataclass_values(ResourceConfig, data.get('resources', {}))
        )
        variant_agent_export = VariantAgentExportConfig(
            **_known_dataclass_values(
                VariantAgentExportConfig,
                data.get('variant_agent_export', {}),
            )
        )
        projects_data = data.get('projects', {}) or {}
        if not isinstance(projects_data, dict):
            raise ValueError("projects 配置必须是项目键到文件名识别文本的映射")
        projects = {str(key): str(value) for key, value in projects_data.items()}

        # 根据引擎类型创建对应配置
        engine_data = data.get('engine', {})

        # 如果只提供了 engine_type，使用默认配置
        if isinstance(engine_data, str):
            engine_type = engine_data
            engine_data = {}
        else:
            engine_type = engine_data.get('engine_type')

        if not engine_type:
            from core.engine_loader import select_default_engine_name

            engine_type = select_default_engine_name(engines.enabled)
        if engines.enabled and engine_type not in engines.enabled:
            raise ValueError(
                f"当前引擎 '{engine_type}' 未包含在 engines.enabled 中: "
                f"{', '.join(engines.enabled)}"
            )

        # 通过引擎注册表动态创建配置实例
        engine = _create_engine_config(engine_type, engine_data)

        return cls(
            paths=paths,
            processing=processing,
            engine=engine,
            engines=engines,
            resources=resources,
            variant_agent_export=variant_agent_export,
            projects=projects,
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为完整的项目配置字典。"""
        data = {
            'paths': {
                'input_dir': str(self.paths.input_dir),
                'output_dir': str(self.paths.output_dir),
                'param_config_dir': str(self.paths.param_config_dir),
                'log_dir': str(self.paths.log_dir),
                'input_voice_dir': str(self.paths.input_voice_dir),
            },
            'processing': {
                'ignore_mode': self.processing.ignore_mode,
                'ignore_words': self.processing.ignore_words,
                'batch_size': self.processing.batch_size,
                'enable_progress_bar': self.processing.enable_progress_bar,
                'multi_project_mode': self.processing.multi_project_mode,
            },
            'engine': {
                'engine_type': self.engine.engine_type,
            },
            'engines': {
                'enabled': self.engines.enabled,
            },
            'resources': {
                'project_root': str(self.resources.project_root),
                'source_root': str(self.resources.source_root),
                'validate_source': self.resources.validate_source,
                'filename_normalization': self.resources.filename_normalization,
                'reference_sample_limit': self.resources.reference_sample_limit,
                'extensions': self.resources.extensions,
            },
            'variant_agent_export': {
                'enabled': self.variant_agent_export.enabled,
                'output_file': self.variant_agent_export.output_file,
                'group_columns': self.variant_agent_export.group_columns,
                'item_key_column': self.variant_agent_export.item_key_column,
                'alias_columns': self.variant_agent_export.alias_columns,
                'parameter_template': self.variant_agent_export.parameter_template,
                'sheet_profiles': self.variant_agent_export.sheet_profiles,
            },
            'projects': self.projects,
        }

        # 将引擎配置的所有字段添加到engine字典中
        # 使用dataclasses.fields获取所有字段
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

        return data

    def to_file(self, config_path: Path):
        """保存完整的项目配置。"""
        _write_config_data(Path(config_path), self.to_dict())

    @classmethod
    def update_file(
        cls,
        config_path: Path,
        updates: Dict[str, Any],
        replace_sections: Optional[List[str]] = None,
    ) -> 'AppConfig':
        """局部更新项目配置，保留 GUI 尚不认识的字段。"""
        config_path = Path(config_path)
        data = _read_config_data(config_path)
        for section in replace_sections or []:
            if section in updates:
                data[section] = updates[section]
        merge_updates = {
            key: value
            for key, value in updates.items()
            if key not in set(replace_sections or [])
        }
        _deep_merge(data, merge_updates)
        _write_config_data(config_path, data)
        return cls.from_dict(data)

    @classmethod
    def create_default(cls, engine_type: Optional[str] = None) -> 'AppConfig':
        """
        创建默认配置

        Args:
            engine_type: 引擎类型

        Returns:
            AppConfig: 默认配置对象
        """
        if engine_type is None:
            engine = _create_default_engine_config()
        else:
            engine = _create_engine_config(engine_type)

        return cls(
            paths=PathConfig(),
            processing=ProcessingConfig(),
            engine=engine,
            engines=EngineDiscoveryConfig(),
            resources=ResourceConfig(),
            variant_agent_export=VariantAgentExportConfig(),
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
    - LetsGalConfig
    """
    engine_config_map = {
        'RenpyConfig': 'engines.renpy.config',
        'NaninovelConfig': 'engines.naninovel.config',
        'UtageConfig': 'engines.utage.config',
        'LetsGalConfig': 'engines.letsgal.config',
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
