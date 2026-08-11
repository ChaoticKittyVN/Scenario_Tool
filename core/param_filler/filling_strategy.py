"""
填充策略模块
定义各种参数填充策略的实现
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Type, Tuple
from pathlib import Path
from dataclasses import dataclass
import pandas as pd
import re
from core.logger import get_logger

logger = get_logger()


@dataclass(frozen=True)
class SyncLocatorResult:
    """Result of locating one synchronization record in a scenario sheet."""

    position: Optional[int]
    status: str


class FillingStrategy(ABC):
    """填充策略抽象基类"""
    
    def __init__(self, name: str = ""):
        """
        初始化填充策略
        
        Args:
            name: 策略名称
        """
        self.name = name or self.__class__.__name__
    
    @abstractmethod
    def can_fill(self, cell_value: Any, context: Dict[str, Any]) -> bool:
        """
        判断是否可以填充该单元格
        
        Args:
            cell_value: 当前单元格值
            context: 上下文信息（包含行数据、列名、工作表等）
            
        Returns:
            bool: 是否可以填充
        """
        pass
    
    @abstractmethod
    def fill(self, cell_value: Any, context: Dict[str, Any], params: Dict[str, Any]) -> Any:
        """
        执行填充
        
        Args:
            cell_value: 当前单元格值
            context: 上下文信息
            params: 策略参数字典
            
        Returns:
            Any: 填充后的值
        """
        pass


class DefaultValueStrategy(FillingStrategy):
    """默认值填充策略"""
    
    def __init__(self):
        super().__init__("default_value")
    
    def can_fill(self, cell_value: Any, context: Dict[str, Any]) -> bool:
        """单元格为空时可以填充"""
        return pd.isna(cell_value) or cell_value == ""
    
    def fill(self, cell_value: Any, context: Dict[str, Any], params: Dict[str, Any]) -> Any:
        """使用默认值填充"""
        default_value = params.get('default_value', '')
        logger.debug(f"使用默认值填充：{default_value}")
        return default_value


class ContextInheritStrategy(FillingStrategy):
    """上下文继承策略（从相邻行继承值）"""
    
    def __init__(self):
        super().__init__("context_inherit")
    
    def can_fill(self, cell_value: Any, context: Dict[str, Any]) -> bool:
        """单元格为空时可以填充"""
        return pd.isna(cell_value) or cell_value == ""
    
    def fill(self, cell_value: Any, context: Dict[str, Any], params: Dict[str, Any]) -> Any:
        """从上下文中继承值"""
        direction = params.get('direction', 'upward')  # upward 或 downward
        df = context.get('dataframe')
        current_row = context.get('row_index')
        column = context.get('column_name')
        
        if df is None or current_row is None or column not in df.columns:
            return cell_value
        
        # 向上查找
        if direction == 'upward':
            for idx in range(current_row - 1, -1, -1):
                value = df.at[idx, column]
                if pd.notna(value) and value != "":
                    logger.debug(f"从上方第{idx}行继承值：{value}")
                    return value
        
        # 向下查找
        elif direction == 'downward':
            for idx in range(current_row + 1, len(df)):
                value = df.at[idx, column]
                if pd.notna(value) and value != "":
                    logger.debug(f"从下方第{idx}行继承值：{value}")
                    return value
        
        logger.debug("未找到可继承的值")
        return cell_value


class PatternGenerateStrategy(FillingStrategy):
    """模式生成策略（根据模板生成值）"""
    
    def __init__(self):
        super().__init__("pattern_generate")
        self._counters: Dict[str, int] = {}
    
    def can_fill(self, cell_value: Any, context: Dict[str, Any]) -> bool:
        """单元格为空且满足条件时可以填充"""
        if pd.isna(cell_value) or cell_value == "":
            # 检查是否有额外的条件
            condition = context.get('additional_condition')
            if condition:
                return condition(context)
            return True
        return False
    
    def fill(self, cell_value: Any, context: Dict[str, Any], params: Dict[str, Any]) -> Any:
        """根据模式生成值"""
        pattern = params.get('pattern', '{value}')
        counter_scope = params.get('counter_scope', 'global')  # global, per_sheet, per_character
        
        # 构建计数器键
        counter_key = f"{counter_scope}:{context.get('sheet_name', '')}:{context.get('character', '')}"
        
        # 递增计数器
        if counter_key not in self._counters:
            self._counters[counter_key] = 0
        self._counters[counter_key] += 1
        
        # 获取用于填充的变量
        variables = {
            'index': self._counters[counter_key],
            'sheet_name': context.get('sheet_name', ''),
            'character': context.get('character', ''),
            'row_index': context.get('row_index', 0)
        }
        
        # 从行数据中获取额外变量
        row_data = context.get('row_data', {})
        for key, value in row_data.items():
            if key not in variables:
                variables[key] = value
        
        # 格式化字符串
        try:
            result = pattern.format(**variables)
            logger.debug(f"按模式生成值：{result}")
            return result
        except KeyError as e:
            logger.warning(f"模式格式化失败：{e}")
            return cell_value


class CharacterNameMappingStrategy(FillingStrategy):
    """角色名映射策略（中文转英文）"""
    
    def __init__(self, mapping: Optional[Dict[str, str]] = None):
        super().__init__("character_name_mapping")
        self.mapping = mapping or {}
        self._cache = {}
    
    def can_fill(self, cell_value: Any, context: Dict[str, Any]) -> bool:
        """单元格有中文角色名时可以填充"""
        if pd.isna(cell_value) or cell_value == "":
            return False
        
        # 检查是否是中文
        value_str = str(cell_value).strip()
        return bool(re.search(r'[\u4e00-\u9fff]', value_str))
    
    def fill(self, cell_value: Any, context: Dict[str, Any], params: Dict[str, Any]) -> Any:
        """将中文角色名映射为英文"""
        chinese_name = str(cell_value).strip()
        
        # 查缓存
        if chinese_name in self._cache:
            return self._cache[chinese_name]
        
        # 尝试映射
        english_name = self.mapping.get(chinese_name)
        
        if english_name:
            self._cache[chinese_name] = english_name
            logger.debug(f"映射角色名：{chinese_name} -> {english_name}")
            return english_name
        
        # 如果没有映射，返回原值
        logger.debug(f"未找到角色名映射：{chinese_name}")
        return cell_value


class VoiceIdGeneratorStrategy(FillingStrategy):
    """语音 ID 生成策略（完整逻辑）"""
    
    def __init__(self):
        super().__init__("voice_id_generator")
        self._counters: Dict[str, int] = {}
        self._cache: Dict[tuple, str] = {}
    
    def can_fill(self, cell_value: Any, context: Dict[str, Any]) -> bool:
        """
        判断是否需要生成语音 ID
        条件：
        1. 语音列为空
        2. 角色列不为空
        3. 台词列有内容
        """
        if pd.isna(cell_value) or cell_value == "":
            row_data = context.get('row_data', {})
            speaker = row_data.get('角色', row_data.get('speaker', ''))
            text = row_data.get('台词', row_data.get('text', ''))
            
            # 角色和台词都不为空时才生成
            has_speaker = pd.notna(speaker) and str(speaker).strip()
            has_text = pd.notna(text) and str(text).strip()
            
            return bool(has_speaker and has_text)
        
        return False
    
    def fill(self, cell_value: Any, context: Dict[str, Any], params: Dict[str, Any]) -> Any:
        """生成语音文件名"""
        row_data = context.get('row_data', {})
        
        # 获取角色名（支持中英文字段）
        speaker = row_data.get('角色', row_data.get('speaker', ''))
        speaker = str(speaker).strip()
        
        # 检查缓存
        cache_key = (speaker, context.get('sheet_name', ''))
        if cache_key in self._cache:
            voice_id = self._cache[cache_key]
            # 增加序号
            parts = voice_id.rsplit('_', 1)
            if len(parts) == 2 and parts[1].isdigit():
                new_num = int(parts[1]) + 1
                voice_id = f"{parts[0]}_{new_num:03d}"
            else:
                voice_id = f"{voice_id}_001"
        else:
            # 新角色，初始化计数器
            counter_key = f"voice:{speaker}"
            if counter_key not in self._counters:
                self._counters[counter_key] = 0
            self._counters[counter_key] += 1
            
            # 生成语音 ID
            format_pattern = params.get('format', '{speaker}_{index:03d}')
            index = self._counters[counter_key]
            
            # 如果是英文名直接使用，否则用中文名作为 ID
            if re.match(r'^[A-Z]+$', speaker):
                speaker_id = speaker
            else:
                # 简单处理：使用中文名作为 ID（实际项目中可能需要拼音转换）
                speaker_id = speaker
            
            voice_id = format_pattern.format(speaker=speaker_id, index=index)
        
        self._cache[cache_key] = voice_id
        logger.debug(f"生成语音 ID: {voice_id}")
        return voice_id


# ============================================================================
# 策略管理器
# ============================================================================

class StrategyManager:
    """
    策略管理器
    
    统一管理内置策略和外部自定义策略的注册与获取
    支持延迟实例化优化性能
    
    注意：每个 SmartParameterFiller 实例应持有独立的 StrategyManager 实例，
    避免不同项目/工具间策略注册表共享导致的行为耦合。
    """
    
    def __init__(self):
        """初始化策略管理器"""
        self._strategies: Dict[str, FillingStrategy] = {}
        self._strategy_classes: Dict[str, Type[FillingStrategy]] = {}
        
        logger.debug("策略管理器初始化完成")
    
    def register(self, strategy: FillingStrategy | Type[FillingStrategy], name: Optional[str] = None):
        """
        注册策略（支持实例或类）
        
        Args:
            strategy: 策略实例或策略类
            name: 策略名称（可选，如果不提供则使用策略的 name 属性或类名）
        """
        if isinstance(strategy, type):
            # 注册的是策略类，延迟实例化
            strategy_name = name or strategy.__name__
            self._strategy_classes[strategy_name] = strategy
            logger.info(f"注册策略类：{strategy_name}")
        else:
            # 注册的是策略实例
            strategy_name = name or strategy.name
            self._strategies[strategy_name] = strategy
            logger.info(f"注册策略实例：{strategy_name}")
    
    def register_custom_strategy(self, strategy_class: Type[FillingStrategy], name: Optional[str] = None):
        """
        注册自定义策略类（对外接口）
        
        Args:
            strategy_class: 自定义策略类
            name: 策略名称（可选）
        """
        self.register(strategy_class, name)
    
    def get(self, name: str) -> Optional[FillingStrategy]:
        """
        获取策略实例
        
        Args:
            name: 策略名称
            
        Returns:
            Optional[FillingStrategy]: 策略实例，不存在返回 None
        """
        # 先检查已实例化的策略
        if name in self._strategies:
            return self._strategies[name]
        
        # 检查是否有注册的类（延迟实例化）
        if name in self._strategy_classes:
            try:
                strategy_instance = self._strategy_classes[name]()
                self._strategies[name] = strategy_instance
                del self._strategy_classes[name]
                logger.debug(f"延迟实例化策略：{name}")
                return strategy_instance
            except Exception as e:
                logger.error(f"实例化策略失败：{name} - {e}")
                return None
        
        return None
    
    def has(self, name: str) -> bool:
        """
        检查策略是否已注册
        
        Args:
            name: 策略名称
            
        Returns:
            bool: 是否已注册
        """
        return name in self._strategies or name in self._strategy_classes
    
    def list_all(self) -> List[str]:
        """
        列出所有已注册的策略名称
        
        Returns:
            List[str]: 策略名称列表
        """
        return list(self._strategies.keys()) + list(self._strategy_classes.keys())
    
    def clear(self):
        """清空所有注册的策略"""
        self._strategies.clear()
        self._strategy_classes.clear()
        logger.info("已清空所有策略")


# ============================================================================
# 向后兼容的注册表（基于 StrategyManager）
# ============================================================================

class StrategyRegistry:
    """
    策略注册表（向后兼容，推荐使用 StrategyManager）
    
    注意：这是全局单例，仅用于向后兼容。新代码应使用 SmartParameterFiller 内部的 strategy_manager。
    """
    
    _instance: Optional[StrategyManager] = None
    
    @classmethod
    def _get_manager(cls) -> StrategyManager:
        """获取内部管理器实例"""
        if cls._instance is None:
            cls._instance = StrategyManager()
        return cls._instance
    
    @classmethod
    def register(cls, strategy: FillingStrategy):
        """注册策略"""
        cls._get_manager().register(strategy)
    
    @classmethod
    def get(cls, name: str) -> Optional[FillingStrategy]:
        """获取策略"""
        return cls._get_manager().get(name)
    
    @classmethod
    def list_all(cls) -> List[str]:
        """列出所有策略"""
        return cls._get_manager().list_all()


# ============================================================================
# 改动同步策略
# ============================================================================

class ChangeSyncStrategy(FillingStrategy):
    """
    改动同步策略
    
    从改动表格中读取修改信息并同步到演出表格
    
    改动表格格式:
    - 主定位列：ExcelFilename, SheetName, Index
    - 辅助校验列：Idx，以及具体同步工具定义的 Text、Name 等字段
    - 数据列：其他所有列，与演出表格表头一致 (需要修改的数据)
    """
    
    DEFAULT_LOCATOR_COLUMNS = [
        'ExcelFilename', 'SheetName', 'Index', 'Idx', 'OldText',
        'Text', 'Name', 'OriginalText', 'ProposedText', 'Decision',
    ]
    REQUIRED_LOCATOR_COLUMNS = ['ExcelFilename', 'SheetName', 'Index']
    LOCATOR_ALIASES = {
        'Filename': 'ExcelFilename',
        'Sheet': 'SheetName',
    }
    
    def __init__(self):
        super().__init__("change_sync")
        self.changes_df: Optional[pd.DataFrame] = None
        self.locator_columns: List[str] = self.DEFAULT_LOCATOR_COLUMNS.copy()
        self.data_columns: List[str] = []
        self._changes_cache: Dict[Tuple[str, str], pd.DataFrame] = {}  # {(filename, sheetname): changes}
    
    def set_changes_df(self, changes_df: pd.DataFrame, 
                      locator_columns: Optional[List[str]] = None,
                      data_columns: Optional[List[str]] = None):
        """
        设置改动表格数据
        
        Args:
            changes_df: 改动表格 DataFrame
            locator_columns: 定位列列表 (可选)
            data_columns: 数据列列表 (可选，默认自动识别)
        """
        self.changes_df = self.normalize_changes_dataframe(changes_df)
        
        if locator_columns:
            self.locator_columns = locator_columns
        
        # 自动识别数据列：除定位列外的所有列
        if data_columns:
            self.data_columns = data_columns
        else:
            all_columns = self.changes_df.columns.tolist()
            self.data_columns = [col for col in all_columns if col not in self.locator_columns]
        
        logger.debug(f"设置改动表格：{len(changes_df)} 条记录，数据列：{self.data_columns}")
        
        # 清空缓存
        self._changes_cache.clear()

    @staticmethod
    def is_blank(value: Any) -> bool:
        if value is None:
            return True
        try:
            if pd.isna(value):
                return True
        except (TypeError, ValueError):
            pass
        return isinstance(value, str) and not value.strip()

    @classmethod
    def normalize_scalar(cls, value: Any) -> Optional[str]:
        if cls.is_blank(value):
            return None
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value).strip()

    @classmethod
    def values_equal(cls, left: Any, right: Any) -> bool:
        return cls.normalize_scalar(left) == cls.normalize_scalar(right)

    @classmethod
    def normalize_changes_dataframe(
        cls,
        changes_df: pd.DataFrame,
        required_columns: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Normalize exporter locator aliases and workbook names for syncing."""
        normalized = changes_df.copy()
        for alias, canonical in cls.LOCATOR_ALIASES.items():
            if canonical not in normalized.columns and alias in normalized.columns:
                normalized = normalized.rename(columns={alias: canonical})
            elif canonical in normalized.columns and alias in normalized.columns:
                canonical_values = normalized[canonical]
                fill_mask = (
                    canonical_values.isna()
                    | canonical_values.astype(str).str.strip().eq('')
                )
                normalized.loc[fill_mask, canonical] = normalized.loc[fill_mask, alias]

        if 'ExcelFilename' in normalized.columns:
            normalized['ExcelFilename'] = normalized['ExcelFilename'].map(
                lambda value: Path(str(value).strip()).stem
                if not cls.is_blank(value)
                else value
            )

        required = required_columns or []
        missing = [column for column in required if column not in normalized.columns]
        if missing:
            raise ValueError(f"改动表格缺少必需列：{missing}")
        return normalized

    @classmethod
    def find_index_positions(cls, df: pd.DataFrame, index_value: Any) -> List[int]:
        if 'Index' not in df.columns or cls.is_blank(index_value):
            return []
        expected = cls.normalize_scalar(index_value)
        return [
            position
            for position, value in enumerate(df['Index'].tolist())
            if cls.normalize_scalar(value) == expected
        ]

    @classmethod
    def locate_record(
        cls,
        df: pd.DataFrame,
        change_record: Dict[str, Any],
    ) -> SyncLocatorResult:
        """Locate by scenario Index and use Idx only to validate the result."""
        index_value = change_record.get('Index')
        if cls.is_blank(index_value):
            return SyncLocatorResult(None, 'missing_index')

        positions = cls.find_index_positions(df, index_value)
        if not positions:
            return SyncLocatorResult(None, 'index_not_found')
        if len(positions) > 1:
            return SyncLocatorResult(None, 'index_ambiguous')

        position = positions[0]
        idx_value = change_record.get('Idx')
        if not cls.is_blank(idx_value):
            try:
                idx_matches = int(float(str(idx_value).strip())) == position + 2
            except (TypeError, ValueError):
                idx_matches = False
            if not idx_matches:
                return SyncLocatorResult(None, 'idx_mismatch')

        return SyncLocatorResult(position, 'matched')
    
    def get_changes_for_sheet(self, filename: str, sheet_name: str) -> pd.DataFrame:
        """
        获取指定工作表的改动记录
        
        Args:
            filename: Excel 文件名
            sheet_name: 工作表名称
            
        Returns:
            pd.DataFrame: 该工作表的改动记录
        """
        filename = Path(str(filename).strip()).stem
        cache_key = (filename, sheet_name)
        
        if cache_key not in self._changes_cache and self.changes_df is not None:
            # 筛选该工作表的改动
            mask = (
                (self.changes_df['ExcelFilename'] == filename) &
                (self.changes_df['SheetName'] == sheet_name)
            )
            self._changes_cache[cache_key] = self.changes_df[mask].copy()
        
        return self._changes_cache.get(cache_key, pd.DataFrame())

    def _get_changes_for_sheet(self, filename: str, sheet_name: str) -> pd.DataFrame:
        """Backward-compatible wrapper for older strategy callers."""
        return self.get_changes_for_sheet(filename, sheet_name)
    
    def _find_row_by_locator(self, df: pd.DataFrame, change_record: Dict[str, Any]) -> Optional[int]:
        """
        根据同步契约查找对应的行位置
        
        Args:
            df: 演出表格 DataFrame
            change_record: 改动记录（一行数据）
            
        Returns:
            Optional[int]: 匹配的行索引，找不到返回 None
        """
        result = self.locate_record(df, change_record)
        if result.position is None:
            logger.warning(
                f"无法定位改动行：status={result.status}, record={change_record}"
            )
        return result.position
    
    def can_fill(self, cell_value: Any, context: Dict[str, Any]) -> bool:
        """
        判断是否可以填充该单元格
        
        条件:
        1. 已加载改动表格
        2. 当前工作表有改动记录
        3. 当前行在改动记录中
        4. 当前列是数据列
        """
        if self.changes_df is None:
            return False
        
        filename = context.get('filename', '')
        sheet_name = context.get('sheet_name', '')
        row_idx = context.get('row_index')
        column_name = context.get('column_name')
        
        # 检查是否是数据列
        if column_name not in self.data_columns:
            return False
        
        # 获取该工作表的改动记录
        changes = self._get_changes_for_sheet(filename, sheet_name)
        if changes.empty:
            return False
        
        # 检查当前行是否有改动
        if row_idx is not None:
            for _, record in changes.iterrows():
                result = self.locate_record(
                    context.get('dataframe', pd.DataFrame()),
                    record.to_dict(),
                )
                if result.position == row_idx:
                    # 检查该列是否有新值
                    new_value = record.get(column_name)
                    return not self.is_blank(new_value)
        
        return False
    
    def fill(self, cell_value: Any, context: Dict[str, Any], params: Dict[str, Any]) -> Any:
        """
        执行填充
        
        从改动表格中获取新值并填充
        
        Args:
            cell_value: 当前单元格值
            context: 上下文信息
            params: 策略参数（本策略不使用）
            
        Returns:
            Any: 填充后的值（从改动表格获取）
        """
        filename = context.get('filename', '')
        sheet_name = context.get('sheet_name', '')
        row_idx = context.get('row_index')
        column_name = context.get('column_name')
        
        # 获取该工作表的改动记录
        changes = self._get_changes_for_sheet(filename, sheet_name)
        if changes.empty:
            logger.debug("无改动记录")
            return cell_value
        
        # 查找匹配的改动记录
        for _, record in changes.iterrows():
            # 定位行
            located_row = self._find_row_by_locator(context.get('dataframe', pd.DataFrame()), record.to_dict())  # type: ignore
            
            if located_row == row_idx:
                # 找到匹配的改动，返回新值
                new_value = record.get(column_name)
                if pd.notna(new_value):
                    row_display = row_idx + 2 if row_idx is not None else '?'
                    logger.info(f"同步改动：{sheet_name} 行{row_display} "
                              f"{column_name}: '{cell_value}' -> '{new_value}'")
                    return new_value
        
        logger.debug("未找到匹配的改动记录")
        return cell_value
