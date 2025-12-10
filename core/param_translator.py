"""
参数翻译器模块
负责将用户友好的参数名称翻译为引擎特定的语法
"""
import importlib.util
import os
from typing import Dict, Optional, List, Any
from pathlib import Path
from core.logger import get_logger
from core.exceptions import TranslationError


logger = get_logger()


class ParamTranslator:
    """
    参数翻译器类，用于加载参数映射并提供翻译功能
    """

    def __init__(
        self,
        module_file: str = "param_config/param_mappings.py",
        varient_module_file: str = "param_config/varient_mappings.py"
    ):
        """
        初始化参数翻译器

        Args:
            module_file: 基础参数映射模块文件路径
            varient_module_file: 差分参数映射模块文件路径
        """
        self.module_file = module_file
        self.varient_module_file = varient_module_file
        self.mappings = self._load_mappings()
        self.varient_mappings = self._load_varient_mappings()
        self._translation_cache = {}
        self._varient_translation_cache = {}

        # 上下文追踪
        self.current_file_name: Optional[str] = None
        self.current_sheet_name: Optional[str] = None
        self.current_row_index: Optional[int] = None

        # 无法翻译的参数
        self.untranslatable_params: List[Dict[str, Any]] = []

        logger.info(f"参数翻译器初始化完成，加载了 {len(self.mappings)} 个参数类型")

    def _load_mappings(self) -> Dict[str, Dict[str, str]]:
        """
        从Python模块加载映射字典

        Returns:
            Dict[str, Dict[str, str]]: 映射字典，如果加载失败则返回空字典
        """
        if not os.path.exists(self.module_file):
            logger.warning(f"映射文件不存在: {self.module_file}")
            return {}

        try:
            spec = importlib.util.spec_from_file_location(
                "param_mappings",
                self.module_file
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            mappings = module.PARAM_MAPPINGS
            logger.debug(f"成功加载基础参数映射: {len(mappings)} 个类型")
            return mappings
        except Exception as e:
            logger.error(f"加载映射模块失败: {e}", exc_info=True)
            return {}

    def _load_varient_mappings(self) -> Dict[str, Dict[str, str]]:
        """
        从Python模块加载差分映射字典

        Returns:
            Dict[str, Dict[str, str]]: 差分映射字典，如果加载失败则返回空字典
        """
        if not os.path.exists(self.varient_module_file):
            logger.debug(f"差分映射文件不存在: {self.varient_module_file}")
            return {}

        try:
            spec = importlib.util.spec_from_file_location(
                "varient_mappings",
                self.varient_module_file
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            varient_mappings = getattr(module, "VARIENT_MAPPINGS", {})
            logger.debug(f"成功加载差分参数映射: {len(varient_mappings)} 个角色")
            return varient_mappings
        except Exception as e:
            logger.error(f"加载差分映射模块失败: {e}", exc_info=True)
            return {}

    def set_context(self, file_name: str, sheet_name: str, row_index: int):
        """
        设置当前处理的上下文信息

        Args:
            file_name: 当前处理的文件名
            sheet_name: 当前处理的工作表名
            row_index: 当前处理的行号
        """
        self.current_file_name = file_name
        self.current_sheet_name = sheet_name
        self.current_row_index = row_index

    def _collect_untranslatable(
        self,
        param_type: str,
        param_value: str,
        role: Optional[str] = None
    ):
        """
        收集无法翻译的参数信息

        Args:
            param_type: 参数类型
            param_value: 参数值
            role: 角色名（差分参数使用）
        """
        record = {
            'file': self.current_file_name,
            'sheet': self.current_sheet_name,
            'row': self.current_row_index,
            'param_type': param_type,
            'param_value': param_value
        }
        if role is not None:
            record['role'] = role

        self.untranslatable_params.append(record)

    def translate(self, param_type: str, param: str) -> str:
        """
        翻译单个参数

        Args:
            param_type: 参数类型（如"Layer", "Transform", "Transition"）
            param: 要翻译的参数值

        Returns:
            str: 翻译后的参数值，如果找不到映射则返回原值
        """
        # 缓存键
        cache_key = f"{param_type}:{param}"
        
        # 检查缓存
        if cache_key in self._translation_cache:
            return self._translation_cache[cache_key]
        
        if param_type in self.mappings:
            if param in self.mappings[param_type]:
                translated = self.mappings[param_type][param]
                # 存入缓存
                self._translation_cache[cache_key] = translated
                return translated
            else:
                # 收集无法翻译的参数
                self._collect_untranslatable(param_type, param)
                # 缓存原值
                self._translation_cache[cache_key] = param
                return param
        else:
            # 参数类型不存在，也收集
            self._collect_untranslatable(param_type, param)
            return param

    def translate_varient(self, param: str, role: Optional[str] = None) -> str:
        """
        翻译差分参数

        Args:
            param: 要翻译的差分参数值
            role: 角色名

        Returns:
            str: 翻译后的参数值
        """
        # 缓存键（包含角色信息）
        cache_key = f"Varient:{role}:{param}"

        # 检查缓存
        if cache_key in self._varient_translation_cache:
            return self._varient_translation_cache[cache_key]

        # 如果没有提供角色名，尝试从基础映射中查找
        if role is None:
            if "Varient" in self.mappings and param in self.mappings["Varient"]:
                translated = self.mappings["Varient"][param]
                self._varient_translation_cache[cache_key] = translated
                return translated
            else:
                # 收集无法翻译的差分参数
                self._collect_untranslatable("Varient", param)
                self._varient_translation_cache[cache_key] = param
                return param

        # 使用角色特定的映射
        if role in self.varient_mappings:
            if param in self.varient_mappings[role]:
                translated = self.varient_mappings[role][param]
                self._varient_translation_cache[cache_key] = translated
                return translated
            else:
                # 收集无法翻译的差分参数（带角色信息）
                self._collect_untranslatable("Varient", param, role)
                self._varient_translation_cache[cache_key] = param
                return param
        else:
            # 角色不存在，也收集
            self._collect_untranslatable("Varient", param, role)
            self._varient_translation_cache[cache_key] = param
            return param

    def translate_batch(self, param_type: str, params: list) -> list:
        """
        批量翻译参数

        Args:
            param_type: 参数类型
            params: 要翻译的参数列表

        Returns:
            list: 翻译后的参数列表
        """
        return [self.translate(param_type, param) for param in params]

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

    def get_translations_for_type(self, param_type: str) -> list:
        """
        获取指定参数类型的所有翻译后参数

        Args:
            param_type: 参数类型

        Returns:
            list: 翻译后参数列表，如果类型不存在则返回空列表
        """
        if param_type in self.mappings:
            return list(self.mappings[param_type].values())
        return []

    def has_mapping(self, param_type: str, param: str) -> bool:
        """
        检查是否存在指定参数的映射

        Args:
            param_type: 参数类型
            param: 参数值

        Returns:
            bool: 是否存在映射
        """
        return (
            param_type in self.mappings and
            param in self.mappings[param_type]
        )

    def get_untranslatable_count(self) -> int:
        """
        获取无法翻译的参数总数

        Returns:
            int: 无法翻译的参数数量
        """
        return len(self.untranslatable_params)

    def export_untranslatable_log(self, output_dir: Path) -> Optional[Path]:
        """
        导出无法翻译的参数日志文件

        Args:
            output_dir: 输出目录

        Returns:
            Optional[Path]: 日志文件路径，如果没有无法翻译的参数则返回 None
        """
        if not self.untranslatable_params:
            logger.info("没有无法翻译的参数，跳过日志文件生成")
            return None

        # 生成日志文件名（带时间戳）
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"untranslatable_params_{timestamp}.log"
        log_path = output_dir / log_filename

        # 确保输出目录存在
        output_dir.mkdir(parents=True, exist_ok=True)

        # 按参数类型分组统计
        from collections import Counter, defaultdict
        type_counts = Counter(item['param_type'] for item in self.untranslatable_params)

        # 按参数类型分组详细信息
        grouped_params = defaultdict(list)
        for item in self.untranslatable_params:
            grouped_params[item['param_type']].append(item)

        # 写入日志文件
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("无法翻译的参数报告\n")
            f.write("=" * 80 + "\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总计: {len(self.untranslatable_params)} 个无法翻译的参数\n")
            f.write("\n")

            # 按参数类型统计
            f.write("-" * 80 + "\n")
            f.write("按参数类型统计:\n")
            f.write("-" * 80 + "\n")
            for param_type, count in sorted(type_counts.items()):
                f.write(f"  {param_type}: {count} 个\n")
            f.write("\n")

            # 详细列表（按参数类型分组）
            f.write("-" * 80 + "\n")
            f.write("详细列表:\n")
            f.write("-" * 80 + "\n")

            for param_type in sorted(grouped_params.keys()):
                f.write(f"\n=== {param_type} 参数 ===\n")

                # 按文件和工作表分组
                file_sheet_groups = defaultdict(lambda: defaultdict(list))
                for item in grouped_params[param_type]:
                    file_name = item['file'] or 'Unknown'
                    sheet_name = item['sheet'] or 'Unknown'
                    file_sheet_groups[file_name][sheet_name].append(item)

                # 输出分组信息
                for file_name in sorted(file_sheet_groups.keys()):
                    f.write(f"\n文件: {file_name}\n")
                    for sheet_name in sorted(file_sheet_groups[file_name].keys()):
                        f.write(f"  工作表: {sheet_name}\n")
                        for item in file_sheet_groups[file_name][sheet_name]:
                            row_info = f"行 {item['row']}" if item['row'] is not None else "未知行"
                            param_value = item['param_value']

                            # 如果有角色信息（差分参数）
                            if 'role' in item:
                                f.write(f"    {row_info}: 参数值 '{param_value}' (角色: {item['role']})\n")
                            else:
                                f.write(f"    {row_info}: 参数值 '{param_value}'\n")

            f.write("\n")
            f.write("=" * 80 + "\n")
            f.write("报告结束\n")
            f.write("=" * 80 + "\n")

        logger.info(f"无法翻译的参数日志已导出: {log_path}")
        return log_path

    def clear_untranslatable_records(self):
        """清空无法翻译的参数记录"""
        self.untranslatable_params.clear()
        logger.debug("已清空无法翻译的参数记录")


# 特定参数类型的翻译器类（可选，提供更友好的API）
class LayerTranslator(ParamTranslator):
    """Layer参数翻译器"""

    def translate_layer(self, param: str) -> str:
        """翻译Layer参数"""
        return self.translate("Layer", param)

    def get_layer_params(self) -> list:
        """获取所有Layer原始参数"""
        return self.get_params_for_type("Layer")

    def get_layer_translations(self) -> list:
        """获取所有Layer翻译后参数"""
        return self.get_translations_for_type("Layer")


class TransformTranslator(ParamTranslator):
    """Transform参数翻译器"""

    def translate_transform(self, param: str) -> str:
        """翻译Transform参数"""
        return self.translate("Transform", param)

    def get_transform_params(self) -> list:
        """获取所有Transform原始参数"""
        return self.get_params_for_type("Transform")

    def get_transform_translations(self) -> list:
        """获取所有Transform翻译后参数"""
        return self.get_translations_for_type("Transform")


class TransitionTranslator(ParamTranslator):
    """Transition参数翻译器"""

    def translate_transition(self, param: str) -> str:
        """翻译Transition参数"""
        return self.translate("Transition", param)

    def get_transition_params(self) -> list:
        """获取所有Transition原始参数"""
        return self.get_params_for_type("Transition")

    def get_transition_translations(self) -> list:
        """获取所有Transition翻译后参数"""
        return self.get_translations_for_type("Transition")