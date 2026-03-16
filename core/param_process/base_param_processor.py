# core/param_base.py
import importlib.util
import os
from typing import Dict, Optional, List, Any
from pathlib import Path
from core.logger import get_logger

logger = get_logger(__name__)

class ParamBaseProccessor:
    """参数处理基类，提供映射加载、缓存、变体处理等公共功能"""

    def __init__(self, module_file: str, variant_module_file: str):
        self.module_file = module_file
        self.variant_module_file = variant_module_file
        self.mappings = self._load_mappings(module_file, "PARAM_MAPPINGS")
        self.variant_mappings = self._load_mappings(variant_module_file, "VARIANT_MAPPINGS")
        self.cache = {}
        self.variant_cache = {}

    def _load_mappings(self, file_path: str, var_name: str) -> Dict[str, Dict[str, str]]:
        """从Python文件加载映射字典"""
        if not os.path.exists(file_path):
            logger.warning(f"映射文件不存在: {file_path}")
            return {}
        try:
            spec = importlib.util.spec_from_file_location("temp", file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            mappings = getattr(module, var_name, {})
            logger.debug(f"成功加载 {var_name}: {len(mappings)} 个类型")
            return mappings
        except Exception as e:
            logger.error(f"加载映射模块失败: {e}", exc_info=True)
            return {}

    def has_mapping(self, param_type: str, param: str) -> bool:
        """检查是否存在映射"""
        return param_type in self.mappings and param in self.mappings[param_type]

    def has_variant_mapping(self, role: str, param: str) -> bool:
        """检查是否存在角色特定映射"""
        return role in self.variant_mappings and param in self.variant_mappings[role]

    def get_mapping(self, param_type: str, param: str) -> Optional[str]:
        """获取映射值（若存在）"""
        if self.has_mapping(param_type, param):
            return self.mappings[param_type][param]
        return None

    def get_variant_mapping(self, role: str, param: str) -> Optional[str]:
        """获取角色特定映射值"""
        if self.has_variant_mapping(role, param):
            return self.variant_mappings[role][param]
        return None


    def get_available_types(self) -> list:
        """
        获取可用的参数类型列表

        Returns:
            list: 参数类型列表
        """
        return list(self.mappings.keys())

    def get_params_for_type(self, param_type: str) -> list:
        """
        获取指定参数类型的所有原始参数

        Args:
            param_type: 参数类型

        Returns:
            list: 原始参数列表，如果类型不存在则返回空列表
        """
        if param_type in self.mappings:
            return list(self.mappings[param_type].keys())
        return []

    def clear_cache(self):
        """清空所有缓存"""
        self.cache.clear()
        self.variant_cache.clear()