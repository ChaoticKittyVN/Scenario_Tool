import re
from typing import Dict, Optional, List, Tuple, Any
from core.logger import get_logger
from core.param_process.base_param_processor import ParamBaseProccesor

logger = get_logger()


class ParamValidator(ParamBaseProccesor):
    """
    参数验证器类，用于加载参数映射并提供验证功能
    """

    def __init__(
        self,
        module_file: str = "param_config/param_mappings.py",
        varient_module_file: str = "param_config/varient_mappings.py"
    ):
        """
        初始化参数验证器

        Args:
            module_file: 基础参数映射模块文件路径
            varient_module_file: 差分参数映射模块文件路径
        """
        # 调用父类构造函数
        super().__init__(module_file, varient_module_file)
        
        # 重新指向缓存，保持原有命名约定
        self._validation_cache = self.cache
        self._varient_validation_cache = self.varient_cache

        # 自定义验证规则（特殊情况）
        self.custom_validators = {
            # 'Character': self._validate_character_format,
            # 'Position': self._validate_position_format,
        }

        logger.info(f"参数验证器初始化完成，加载了 {len(self.mappings)} 个参数类型")

    def validate(self, param_type: str, param: str) -> Tuple[bool, str]:
        """
        验证单个参数

        Args:
            param_type: 参数类型（如"Layer", "Transform", "Transition"）
            param: 要验证的参数值

        Returns:
            Tuple[bool, str]: (是否有效, 验证消息)
        """
        # 缓存键
        cache_key = f"{param_type}:{param}"
        
        # 检查缓存
        if cache_key in self._validation_cache:
            return self._validation_cache[cache_key]
        
        # 优先检查是否在映射中存在
        if param_type in self.mappings:
            if param in self.mappings[param_type]:
                result = (True, f"Valid mapped parameter: {param} -> {self.mappings[param_type][param]}")
            else:
                # 参数值不在映射中，尝试自定义验证规则
                if param_type in self.custom_validators:
                    result = self.custom_validators[param_type](param)
                else:
                    result = (False, f"Parameter value '{param}' not found in {param_type} mappings")
        else:
            # 参数类型不存在于映射中，尝试自定义验证规则
            if param_type in self.custom_validators:
                result = self.custom_validators[param_type](param)
            else:
                result = (False, f"Parameter type '{param_type}' not supported and no custom validator")
        
        # 存入缓存
        self._validation_cache[cache_key] = result
        return result

    def validate_variant(self, param: str, role: Optional[str] = None) -> Tuple[bool, str]:
        """
        验证差分参数

        Args:
            param: 要验证的差分参数值
            role: 角色名

        Returns:
            Tuple[bool, str]: (是否有效, 验证消息)
        """
        # 缓存键（包含角色信息）
        cache_key = f"Variant:{role}:{param}"

        # 检查缓存
        if cache_key in self._varient_validation_cache:
            return self._varient_validation_cache[cache_key]

        # 如果没有提供角色名，尝试从基础映射中查找
        if role is None:
            if "Variant" in self.mappings and param in self.mappings["Variant"]:
                result = (True, f"Valid variant parameter: {param} -> {self.mappings['Variant'][param]}")
            else:
                result = (False, f"Variant parameter '{param}' not found in base mappings")
        else:
            # 使用角色特定的映射
            if role in self.varient_mappings:
                if param in self.varient_mappings[role]:
                    result = (True, f"Valid variant parameter for {role}: {param} -> {self.varient_mappings[role][param]}")
                else:
                    result = (False, f"Variant parameter '{param}' not found for role {role}")
            else:
                result = (False, f"Role '{role}' not found in variant mappings")

        # 存入缓存
        self._varient_validation_cache[cache_key] = result
        return result

    def validate_batch(self, param_type: str, params: list) -> List[Tuple[bool, str]]:
        """
        批量验证参数

        Args:
            param_type: 参数类型
            params: 要验证的参数列表

        Returns:
            List[Tuple[bool, str]]: 验证结果列表
        """
        return [self.validate(param_type, param) for param in params]

    def clear_validation_cache(self):
        """清空验证缓存"""
        self._validation_cache.clear()
        self._varient_validation_cache.clear()
        logger.debug("已清空验证缓存")


# 特定参数类型的验证器类（可选，提供更友好的API）
class SpecificValidator(ParamValidator):
    """特定参数验证器"""

    def validate_specific(self, param: str) -> Tuple[bool, str]:
        """验证指定参数"""
        return self.validate("SpecificParam", param)

    def get_specific_params(self) -> list:
        """获取所有SpecificParam原始参数"""
        return self.get_params_for_type("SpecificParam")