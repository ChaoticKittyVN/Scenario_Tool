"""
资源提取器模块
从 Excel 数据中提取资源引用
"""
from typing import Dict, List, Set
from collections import defaultdict
from core.sentence_generator_manager import SentenceGeneratorManager
from core.param_translator import ParamTranslator
from core.config_manager import EngineConfig
from core.logger import get_logger

logger = get_logger()


class ResourceExtractor:
    """资源提取器 - 从 Excel 数据中提取资源引用"""

    def __init__(
        self,
        generator_manager: SentenceGeneratorManager,
        translator: ParamTranslator,
        engine_config: EngineConfig
    ):
        """
        初始化资源提取器

        Args:
            generator_manager: 生成器管理器
            translator: 参数翻译器
            engine_config: 引擎配置
        """
        self.generator_manager = generator_manager
        self.translator = translator
        self.engine_config = engine_config
        self.generators = []

    def setup(self):
        """设置提取器，创建生成器实例"""
        self.generators = self.generator_manager.create_generator_instances(
            self.translator,
            self.engine_config
        )
        logger.info(f"资源提取器设置完成，共 {len(self.generators)} 个生成器")

    def extract_from_row(self, row_data: Dict) -> Dict[str, Set[str]]:
        """
        从一行数据中提取所有资源

        Args:
            row_data: 行数据字典

        Returns:
            Dict[str, Set[str]]: {资源类型: {资源名集合}}
            例如: {"Character": {"alice happy smile"}, "Music": {"bgm01"}}
        """
        resources = defaultdict(set)

        for generator in self.generators:
            # 获取所有 resource_config
            configs = self._get_resource_configs(generator)

            for config in configs:
                resource_name = self._build_resource_name(row_data, config)
                if resource_name:
                    resource_type = config["resource_type"]
                    resources[resource_type].add(resource_name)

        return dict(resources)

    def _get_resource_configs(self, generator) -> List[Dict]:
        """
        获取 generator 的所有资源配置

        Returns:
            List[Dict]: 资源配置列表
        """
        configs = []

        # 检查单个 resource_config
        if hasattr(generator, "resource_config"):
            configs.append(generator.resource_config)

        # 检查多个 resource_config_xxx
        for attr_name in dir(generator):
            if attr_name.startswith("resource_config_"):
                config = getattr(generator, attr_name)
                if isinstance(config, dict):
                    configs.append(config)

        return configs

    def _build_resource_name(self, row_data: Dict, config: Dict) -> str:
        """
        根据配置构建完整的资源名（包含差分）

        Args:
            row_data: 行数据
            config: 资源配置

        Returns:
            str: 完整的资源名，如果主参数不存在则返回空字符串
        """
        main_param = config["main_param"]
        main_value = row_data.get(main_param)

        if not main_value or main_value == "":
            return ""

        # 确保是字符串类型
        main_value = str(main_value).strip()

        # 翻译主参数
        if self.translator.has_mapping(config["resource_type"], main_value):
            main_value = self.translator.translate(config["resource_type"], main_value)

        result = str(main_value)
        separator = config.get("separator", " ")

        # 拼接差分参数
        for part_param in config.get("part_params", []):
            if part_param in row_data and row_data[part_param]:
                part_value = str(row_data[part_param]).strip()

                # 尝试翻译差分参数
                if self.translator.has_mapping(part_param, part_value):
                    part_value = self.translator.translate(part_param, part_value)

                part_value = str(part_value)

                if separator:
                    result += f"{separator}{part_value}"
                else:
                    result += part_value

        return result

    def extract_from_excel(self, excel_data: Dict) -> Dict[str, Dict[str, Set[str]]]:
        """
        从整个 Excel 文件中提取资源

        Args:
            excel_data: Excel 数据 {sheet_name: DataFrame}

        Returns:
            Dict[str, Dict[str, Set[str]]]: {资源类别: {资源类型: {资源名集合}}}
            例如: {
                "图片": {
                    "Character": {"alice happy", "bob normal"},
                    "Background": {"room", "street"}
                },
                "音频": {
                    "Music": {"bgm01", "bgm02"}
                }
            }
        """
        from core.constants import SheetName, ColumnName, Marker
        import pandas as pd

        all_resources = defaultdict(lambda: defaultdict(set))

        for sheet_name, sheet_data in excel_data.items():
            # 跳过参数表
            if sheet_name == SheetName.PARAM_SHEET.value:
                continue

            # 检查是否有 END 标记
            if (ColumnName.NOTE.value not in sheet_data.columns or
                    Marker.END.value not in sheet_data[ColumnName.NOTE.value].tolist()):
                logger.warning(f"工作表 {sheet_name} 不包含Note列或END标记，跳过")
                continue

            # 找到 END 标记位置
            end_index = sheet_data[ColumnName.NOTE.value].tolist().index(Marker.END.value)

            # 遍历有效行
            for idx in range(end_index):
                row = sheet_data.iloc[idx]
                row_dict = row.to_dict()

                # 提取这一行的资源
                row_resources = self.extract_from_row(row_dict)

                # 按资源类别分类
                for resource_type, resource_names in row_resources.items():
                    # 查找资源类别
                    category = self._get_resource_category(resource_type)
                    if category:
                        all_resources[category][resource_type].update(resource_names)

        # 转换为普通字典
        result = {}
        for category, types in all_resources.items():
            result[category] = {k: v for k, v in types.items()}

        return result

    def _get_resource_category(self, resource_type: str) -> str:
        """
        获取资源类型对应的资源类别

        Args:
            resource_type: 资源类型（如 "Character", "Music"）

        Returns:
            str: 资源类别（如 "图片", "音频"）
        """
        for generator in self.generators:
            configs = self._get_resource_configs(generator)
            for config in configs:
                if config["resource_type"] == resource_type:
                    return config.get("resource_category", "")
        return ""
