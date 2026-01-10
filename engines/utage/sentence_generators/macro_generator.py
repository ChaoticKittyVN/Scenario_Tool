"""
Utage Macro Generator
生成宏命令语句
"""
from typing import Any, Dict, Optional
from core.dict_based_sentence_generator import DictBasedSentenceGenerator
from core.logger import get_logger

logger = get_logger()

# 从配置文件加载宏映射
try:
    from param_config.macro_mappings import MACRO_MAPPINGS
except ImportError:
    logger.warning("无法导入 macro_mappings，使用空映射")
    MACRO_MAPPINGS = {}


class MacroGenerator(DictBasedSentenceGenerator):
    """
    宏命令生成器
    
    特殊处理模式：
    - RECEIVE_ALL_PARAMS = True: 接收所有非空参数
    - EXCLUSIVE_MODE = True: 独占模式，激活时其他生成器（除ALLOWED_WITH_MACRO）被跳过
    
    与其他生成器的关系：
    - 当Macro存在时，只有标记为ALLOWED_WITH_MACRO的生成器（如CharacterTextGenerator）会被处理
    - 其他生成器（如BackgroundGenerator、AudioGenerator等）会被跳过
    - 这确保了Macro指令的优先级和独立性
    """
    
    # 标记：接收所有参数
    RECEIVE_ALL_PARAMS = True
    
    # 标记：独占模式 - 当此生成器成功处理时，其他生成器（除Text相关）应被跳过
    EXCLUSIVE_MODE = True
    
    @property
    def category(self):
        return "Macro"
    
    @property
    def priority(self) -> int:
        return 0  # 最高优先级，确保最先处理
    
    def can_process(self, data: Dict[str, Any]) -> bool:
        """检查是否有Macro参数"""
        return self.exists_param("Macro", data)
    
    def process(self, data: Dict[str, Any]) -> Optional[list]:
        """
        处理宏命令
        
        Args:
            data: 完整的参数字典（包含所有参数）
        
        Returns:
            List[Dict[str, Any]]: 生成的宏命令
        """
        if not self.can_process(data):
            return None
        
        macro_name = str(data.get("Macro", "")).strip()
        if not macro_name:
            return None
        
        # 查找映射配置
        mapping = MACRO_MAPPINGS.get(macro_name)
        if not mapping:
            logger.warning(f"未找到宏 '{macro_name}' 的映射配置")
            return None
        
        line = self.create_command_dict()
        self.set_command(line, self.get_value("Macro", data))

        # 根据映射填充字段
        for target_field, source in mapping.items():
            # source 可能是参数名（从data中获取）或固定值（直接使用）
            if source in data:
                # source 是参数名，从data中获取值
                value = data[source]
                if value not in (None, ""):
                    line[target_field] = str(value)
            else:
                # source 是固定值，直接使用
                line[target_field] = str(source)
        
        return [line] if line else None

