"""
Utage 引擎配置
"""
from dataclasses import dataclass, field
from typing import List, Dict
from core.config_manager import EngineConfig


@dataclass
class UtageConfig(EngineConfig):
    """Utage 引擎配置"""
    engine_type: str = "utage"
    file_extension: str = ".xls"
    output_format: str = "excel"

    # 表格列配置
    columns: List[str] = field(default_factory=lambda: [
        "", "Command", "Arg1", "Arg2", "Arg3", "Arg4", "Arg5", "Arg6",
        "WaitType", "Text", "PageCtrl", "Voice", "WindowType"
    ])

    # 列映射（从输入列到输出列）
    column_mapping: Dict[str, str] = field(default_factory=dict)

