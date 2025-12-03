import pandas as pd
from pathlib import Path
from typing import Dict, List, Literal

from core.logger import get_logger
from core.constants import SheetName, ColumnName, Marker

from .excel_decorators import handle_excel_operation
from .excel_exceptions import (
    ExcelManagerError,
    ExcelFileNotFoundError,
    ExcelFormatError,
    ExcelWriteError,
)

logger = get_logger(__name__)


# ==================== Excel文件管理器 ====================
class ExcelFileManager:
    """
    Excel文件管理器
    负责Excel文件的读取、缓存和工作表管理
    """
    
    def __init__(self, cache_enabled: bool = True):
        """
        初始化Excel文件管理器
        
        Args:
            cache_enabled: 是否启用文件缓存
        """
        self._file_cache: Dict[Path, Dict[str, pd.DataFrame]] = {}
        self.cache_enabled = cache_enabled

    @handle_excel_operation
    def load_excel(self, file_path: Path) -> Dict[str, pd.DataFrame]:
        """
        加载Excel文件的所有工作表
        
        Args:
            file_path: Excel文件路径
            
        Returns:
            Dict[str, pd.DataFrame]: 工作表名到DataFrame的映射
            
        Raises:
            ExcelFileNotFoundError: 文件不存在
            ExcelFormatError: 文件格式错误
            ExcelManagerError: 其他读取错误
        """
        if not file_path.exists():
            logger.error(f"Excel文件不存在: {file_path}")
            raise ExcelFileNotFoundError(f"Excel文件不存在: {file_path}")
        
        # 检查缓存
        if file_path in self._file_cache and self.cache_enabled:
            logger.debug(f"从缓存加载Excel文件: {file_path}")
            return self._file_cache[file_path]
        
        logger.info(f"加载Excel文件: {file_path}")
        try:
            # 读取所有工作表，所有列作为字符串类型处理
            data = pd.read_excel(file_path, sheet_name=None, dtype=str)
            
            # 清理数据：将NaN转换为空字符串
            for sheet_name, df in data.items():
                data[sheet_name] = df.fillna("")
            
            if self.cache_enabled:
                self._file_cache[file_path] = data
            
            logger.debug(f"文件加载成功: {file_path}, 工作表数: {len(data)}")
            return data
            
        except pd.errors.EmptyDataError as e:
            logger.error(f"Excel文件为空: {file_path}")
            raise ExcelFormatError(f"Excel文件为空: {file_path}", e)
        except Exception as e:
            logger.error(f"读取Excel文件失败: {file_path}", exc_info=True)
            raise ExcelManagerError(f"读取Excel文件失败: {file_path}", e)
    
    def get_sheet(self, file_path: Path, sheet_name: str) -> pd.DataFrame:
        """
        获取指定工作表的DataFrame
        
        Args:
            file_path: Excel文件路径
            sheet_name: 工作表名称
            
        Returns:
            pd.DataFrame: 指定工作表的DataFrame，如果不存在则返回空DataFrame
            
        Raises:
            ExcelManagerError: 文件读取错误
        """
        try:
            data = self.load_excel(file_path)
            df = data.get(sheet_name, pd.DataFrame())
            
            if df.empty:
                logger.warning(f"工作表不存在或为空: {file_path} -> {sheet_name}")
            else:
                logger.debug(f"获取工作表: {file_path} -> {sheet_name}, 形状: {df.shape}")

            return df
        except ExcelManagerError:
            # 重新抛出已有的ExcelManagerError
            raise
        except Exception as e:
            logger.error(f"获取工作表失败: {file_path} -> {sheet_name}", exc_info=True)
            raise ExcelManagerError(f"获取工作表失败: {file_path} -> {sheet_name}", e)

    def get_sheet_names(self, file_path: Path) -> List[str]:
        """
        获取Excel文件的所有工作表名称
        
        Args:
            file_path: Excel文件路径
            
        Returns:
            List[str]: 工作表名称列表
            
        Raises:
            ExcelManagerError: 文件读取错误
        """
        try:
            data = self.load_excel(file_path)
            return list(data.keys())
        except ExcelManagerError:
            raise
        except Exception as e:
            logger.error(f"获取工作表名称失败: {file_path}", exc_info=True)
            raise ExcelManagerError(f"获取工作表名称失败: {file_path}", e)

    @handle_excel_operation
    def save_excel(self, 
                   file_path: Path, 
                   data: Dict[str, pd.DataFrame],
                   engine: Literal['openpyxl', 'xlsxwriter', 'odf', None] ,
                   **kwargs) -> bool:
        """
        保存数据到Excel文件
        
        Args:
            file_path: 保存路径
            data: {工作表名: DataFrame} 的字典
            engine: 写入引擎 ('openpyxl' 或 'xlsxwriter')
            **kwargs: 传递给 pd.ExcelWriter 的额外参数
            
        Returns:
            bool: 是否保存成功
            
        Raises:
            ExcelWriteError: 写入失败
        """
        try:
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"保存Excel文件: {file_path}")
            
            # 使用ExcelWriter保存多个工作表
            with pd.ExcelWriter(file_path, engine=engine, **kwargs) as writer:
                for sheet_name, df in data.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    logger.debug(f"写入工作表: {sheet_name}, 形状: {df.shape}")
            
            logger.info(f"文件保存成功: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存Excel文件失败: {file_path}", exc_info=True)
            raise ExcelWriteError(f"保存Excel文件失败: {file_path}", e)
    
    @handle_excel_operation
    def save_single_sheet(self,
                         file_path: Path,
                         df: pd.DataFrame,
                         sheet_name: str = 'Sheet1',
                         **kwargs) -> bool:
        """
        保存单个工作表到Excel文件
        
        Args:
            file_path: 保存路径
            df: 要保存的DataFrame
            sheet_name: 工作表名称
            **kwargs: 传递给 DataFrame.to_excel 的参数
            
        Returns:
            bool: 是否保存成功
        """
        try:
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"保存Excel文件（单工作表）: {file_path}")
            df.to_excel(file_path, sheet_name=sheet_name, index=False, **kwargs)
            
            logger.info(f"文件保存成功: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存Excel文件失败: {file_path}", exc_info=True)
            raise ExcelWriteError(f"保存Excel文件失败: {file_path}", e)

    def reload_file(self, file_path: Path):
        """
        重新加载文件（清除缓存并重新读取）

        Args:
            file_path: Excel文件路径
        """
        if file_path in self._file_cache:
            del self._file_cache[file_path]
            logger.info(f"清除文件缓存: {file_path}")

        # 重新加载文件
        self.load_excel(file_path)

    def clear_cache(self):
        """清除所有文件缓存"""
        self._file_cache.clear()
        logger.info("清除所有Excel文件缓存")