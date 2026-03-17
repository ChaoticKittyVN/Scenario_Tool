"""
规则引擎模块
解析 YAML 配置并生成填充方案
"""
from typing import Dict, List, Any, Optional
from pathlib import Path
import yaml
from dataclasses import dataclass
from core.logger import get_logger
from .filling_strategy import StrategyRegistry, FillingStrategy

logger = get_logger()


@dataclass
class FillingRule:
    """填充规则数据类"""
    name: str
    target_sheets: List[str]  # 空列表表示所有工作表
    target_columns: List[str]
    strategy_name: str
    params: Dict[str, Any]
    condition: Optional[str] = None
    
    def matches(self, sheet_name: str, column_name: str) -> bool:
        """
        判断规则是否匹配指定的工作表和列
        
        Args:
            sheet_name: 工作表名称
            column_name: 列名
            
        Returns:
            bool: 是否匹配
        """
        # 检查工作表是否匹配
        if self.target_sheets and sheet_name not in self.target_sheets:
            return False
        
        # 检查列是否匹配
        if column_name not in self.target_columns:
            return False
        
        return True


class RuleEngine:
    """规则引擎"""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        初始化规则引擎
        
        Args:
            config_path: YAML 配置文件路径
        """
        self.rules: List[FillingRule] = []
        self.config_path = config_path
        
        if config_path and config_path.exists():
            self.load_config(config_path)
    
    def load_config(self, config_path: Path):
        """
        加载 YAML 配置文件
        
        Args:
            config_path: 配置文件路径
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            filling_rules = config.get('filling_rules', [])
            
            for rule_data in filling_rules:
                rule = FillingRule(
                    name=rule_data.get('name', ''),
                    target_sheets=rule_data.get('target_sheets', []),
                    target_columns=rule_data.get('target_columns', []),
                    strategy_name=rule_data.get('strategy', ''),
                    params=rule_data.get('params', {}),
                    condition=rule_data.get('condition')
                )
                self.rules.append(rule)
            
            logger.info(f"从 {config_path} 加载了 {len(self.rules)} 条填充规则")
            
        except Exception as e:
            logger.error(f"加载配置文件失败：{e}", exc_info=True)
            raise
    
    def get_applicable_rules(self, sheet_name: str, column_name: str) -> List[FillingRule]:
        """
        获取适用于指定工作表和列的规则
        
        Args:
            sheet_name: 工作表名称
            column_name: 列名
            
        Returns:
            List[FillingRule]: 适用的规则列表
        """
        applicable = []
        for rule in self.rules:
            if rule.matches(sheet_name, column_name):
                applicable.append(rule)
        
        logger.debug(f"为 {sheet_name}.{column_name} 找到 {len(applicable)} 条规则")
        return applicable
    
    def validate_strategy(self, strategy_name: str) -> bool:
        """
        验证策略是否已注册
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            bool: 策略是否可用
        """
        strategy = StrategyRegistry.get(strategy_name)
        if strategy is None:
            logger.warning(f"策略未注册：{strategy_name}")
            return False
        return True
    
    def validate_rules(self) -> bool:
        """
        验证所有规则的有效性
        
        Returns:
            bool: 是否所有规则都有效
        """
        valid = True
        for rule in self.rules:
            if not self.validate_strategy(rule.strategy_name):
                valid = False
        
        return valid
