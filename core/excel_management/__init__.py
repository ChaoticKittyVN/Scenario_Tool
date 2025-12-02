from .excel_exceptions import (
    ExcelManagerError,
    ExcelFileNotFoundError,
    ExcelFormatError,
    ExcelDataError,
    ExcelWriteError,
)

from .excel_file_manager import ExcelFileManager
from .dataframe_processor import DataFrameProcessor
from .excel_writer import ExcelWriter
from .excel_decorators import handle_excel_operation

__all__ = [
    # 异常
    'ExcelManagerError',
    'ExcelFileNotFoundError',
    'ExcelFormatError',
    'ExcelDataError',
    'ExcelWriteError',
    
    # 核心类
    'ExcelFileManager',
    'DataFrameProcessor',
    'ExcelWriter',
    
    # 别名
    'ExcelManager',
    'DataProcessor',
    
    # 装饰器
    'handle_excel_operation',
    
    # 工厂函数
    'create_excel_manager',
    'create_dataframe_processor',
    'create_excel_writer',
]

# 快捷工厂函数
def create_excel_manager(cache_enabled: bool = True) -> ExcelFileManager:
    return ExcelFileManager(cache_enabled=cache_enabled)

def create_dataframe_processor(config=None) -> DataFrameProcessor:
    return DataFrameProcessor(config)

def create_excel_writer() -> ExcelWriter:
    return ExcelWriter()

# 别名
ExcelManager = ExcelFileManager
DataProcessor = DataFrameProcessor