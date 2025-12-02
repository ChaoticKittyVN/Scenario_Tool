from typing import Optional

# ==================== 异常定义 ====================
class ExcelManagerError(Exception):
    """Excel读取基础异常"""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error
        self.message = message


class ExcelFileNotFoundError(ExcelManagerError):
    """文件不存在异常"""
    pass


class ExcelFormatError(ExcelManagerError):
    """文件格式错误"""
    pass


class ExcelDataError(ExcelManagerError):
    """数据内容错误"""
    pass


class ExcelWriteError(ExcelManagerError):
    """写入错误"""
    pass




# ==================== 导出 ====================
__all__ = [
    'ExcelManagerError',
    'ExcelFileNotFoundError',
    'ExcelFormatError',
    'ExcelDataError',
    'ExcelWriteError',
]