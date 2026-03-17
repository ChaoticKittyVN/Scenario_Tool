"""
填充策略模块
定义各种参数填充策略的实现
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Type
from pathlib import Path
import pandas as pd
import re
from core.logger import get_logger

logger = get_logger()


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
    """
    
    _instance: Optional['StrategyManager'] = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化策略管理器"""
        if self._initialized:
            return
        
        self._strategies: Dict[str, FillingStrategy] = {}
        self._strategy_classes: Dict[str, Type[FillingStrategy]] = {}
        self._initialized = True
        
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
    """
    
    @classmethod
    def register(cls, strategy: FillingStrategy):
        """注册策略"""
        manager = StrategyManager()
        manager.register(strategy)
    
    @classmethod
    def get(cls, name: str) -> Optional[FillingStrategy]:
        """获取策略"""
        manager = StrategyManager()
        return manager.get(name)
    
    @classmethod
    def list_all(cls) -> List[str]:
        """列出所有策略"""
        manager = StrategyManager()
        return manager.list_all()
