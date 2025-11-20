"""
自定义异常类模块
定义项目中使用的所有异常类型
"""


class ScenarioToolError(Exception):
    """基础异常类"""
    pass


class ConfigError(ScenarioToolError):
    """配置相关错误"""
    pass


class EngineError(ScenarioToolError):
    """引擎相关错误"""
    pass


class GeneratorError(ScenarioToolError):
    """生成器错误"""
    pass


class TranslationError(ScenarioToolError):
    """参数翻译错误"""
    pass


class FileValidationError(ScenarioToolError):
    """文件验证错误"""
    pass


class ExcelParseError(ScenarioToolError):
    """Excel 解析错误"""
    pass


class EngineNotRegisteredError(EngineError):
    """引擎未注册错误"""
    pass


class InvalidParameterError(ScenarioToolError):
    """无效参数错误"""
    pass
