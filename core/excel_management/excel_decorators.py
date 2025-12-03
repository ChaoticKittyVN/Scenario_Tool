import pandas as pd
from typing import Callable
from functools import wraps
from core.logger import get_logger

from .excel_exceptions import (
    ExcelManagerError,
    ExcelFileNotFoundError,
    ExcelFormatError
)

logger = get_logger(__name__)

# ==================== 错误处理装饰器 ====================
def handle_excel_operation(func) -> Callable:
    """Excel操作统一错误处理装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            logger.error(f"文件不存在: {e}")
            raise ExcelFileNotFoundError(f"Excel文件不存在: {e}", e)
        except pd.errors.EmptyDataError as e:
            logger.error(f"Excel文件为空: {e}")
            raise ExcelFormatError(f"Excel文件为空或格式错误: {e}", e)
        except pd.errors.ParserError as e:
            logger.error(f"Excel解析失败: {e}")
            raise ExcelFormatError(f"Excel文件解析失败: {e}", e)
        except PermissionError as e:
            logger.error(f"文件访问权限不足: {e}")
            raise ExcelFileNotFoundError(f"无法访问Excel文件: {e}", e)
        except ExcelManagerError:
            # 如果是我们自定义的异常，直接抛出
            raise
        except Exception as e:
            logger.error(f"处理Excel时发生未知错误: {e}", exc_info=True)
            raise ExcelManagerError(f"处理Excel失败: {e}", e)
    return wrapper