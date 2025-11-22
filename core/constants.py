"""
常量定义模块
集中管理项目中使用的所有常量
"""
from enum import Enum


class WindowMode(str, Enum):
    """对话框模式"""
    SHOW = "显示"
    HIDE = "隐藏"
    SHOW_AND_HIDE = "显示和隐藏"


class SpecialSpeaker(str, Enum):
    """特殊说话者（用于直接输入引擎命令）"""
    RENPY_COMMAND = "renpy"
    NANINOVEL_COMMAND = "naninovel"


class FileType(str, Enum):
    """文件类型"""
    BACKGROUND = "Background"
    CHARACTER = "Character"
    MUSIC = "Music"
    SOUND = "Sound"
    VOICE = "Voice"
    EVENT = "Event"


class SheetName(str, Enum):
    """特殊工作表名称"""
    PARAM_SHEET = "参数表"


class ColumnName(str, Enum):
    """Excel 列名"""
    NOTE = "Note"
    IGNORE = "Ignore"
    SPEAKER = "Speaker"
    TEXT = "Text"
    CHARACTER = "Character"
    BACKGROUND = "Background"


class Marker(str, Enum):
    """标记符号"""
    END = "END"


# 默认值
DEFAULT_INDENT_SIZE = 4
DEFAULT_BATCH_SIZE = 100
DEFAULT_TRANSITION = "dissolve"

# 文件扩展名
EXCEL_EXTENSIONS = ['.xlsx', '.xls']
RENPY_EXTENSION = '.rpy'
NANINOVEL_EXTENSION = '.nani'

# 忽略的文件前缀
TEMP_FILE_PREFIX = '~'
