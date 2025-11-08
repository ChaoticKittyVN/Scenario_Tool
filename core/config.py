# vn_config.py - 视觉小说工具通用配置

# 引擎类型配置
# ENGINE_TYPE = "renpy"  # 可选: "renpy", "naninovel", "utage"
ENGINE_TYPE = "naninovel"

# 文件路径配置
PARAM_DATA_FILE = "./param_config/param_data.xlsx"
VARIENT_DATA_FILE = "./param_config/varient_data.xlsx"
TARGET_PATH = "./input/"
OUTPUT_PATH = "./output/"
MAPPINGS_FILE = "./param_config/param_mappings.py"
PARAM_FILE = f"./param_config/param_data_{ENGINE_TYPE}.xlsx"
VARIENT_MAPPINGS_FILE = "./param_config/varient_mappings.py"

# 忽略模式
IGNORE_MODE = True
IGNORE_WORDS = [""]

# 动态导入当前引擎的参数名称
try:
    if ENGINE_TYPE == "renpy":
        from engines.renpy.engine_param_config import PARAM_NAMES as CURRENT_PARAM_NAMES
    elif ENGINE_TYPE == "naninovel":
        from engines.naninovel.engine_param_config import PARAM_NAMES as CURRENT_PARAM_NAMES
    else:
        CURRENT_PARAM_NAMES = []
        print(f"警告: 未知的引擎类型: {ENGINE_TYPE}")
except ImportError as e:
    CURRENT_PARAM_NAMES = []
    print(f"警告: 无法导入 {ENGINE_TYPE} 参数名称: {e}")

# 确保 CURRENT_PARAM_NAMES 有效
if not CURRENT_PARAM_NAMES:
    print(f"错误: 引擎 {ENGINE_TYPE} 没有可用的参数名称配置")
    # 可以选择退出或使用默认值

# Ren'Py 特定配置
RENPY_CONFIG = {
    "indent_size": 4,
    "label_indent": False,  # 标签是否缩进
    "default_transition": "dissolve"
}

# Unity 特定配置（预留）
NANINOVEL_CONFIG = {
    # 将来可以添加 Unity 相关的配置
}

# Godot 特定配置（预留）
UTAGE_CONFIG = {
    # 将来可以添加 Godot 相关的配置
}

# 根据引擎类型获取当前配置
def get_engine_config():
    if ENGINE_TYPE == "renpy":
        return RENPY_CONFIG
    elif ENGINE_TYPE == "naninovel":
        return NANINOVEL_CONFIG
    elif ENGINE_TYPE == "utage":
        return UTAGE_CONFIG
    else:
        return {}