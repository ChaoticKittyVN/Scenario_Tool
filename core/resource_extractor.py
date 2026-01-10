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

from core.excel_management.dataframe_processor import DataFrameProcessor

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
            configs = self.get_resource_configs(generator)

            for config in configs:
                # 传递生成器实例以便访问 param_config
                resource_name = self._build_resource_name(row_data, config, generator)
                if resource_name:
                    resource_type = config["resource_type"]
                    resources[resource_type].add(resource_name)

        return dict(resources)

    def get_resource_configs(self, generator) -> List[Dict]:
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

    def _build_resource_name(self, row_data: Dict, config: Dict, generator=None) -> str:
        """
        根据配置构建完整的资源名（包含差分）

        Args:
            row_data: 行数据
            config: 资源配置
            generator: 生成器实例（用于访问 param_config 和自定义构建方法）

        Returns:
            str: 完整的资源名，如果主参数不存在则返回空字符串
        """
        # 如果生成器提供了自定义的资源名称构建方法，优先使用
        if generator and hasattr(generator, 'build_resource_name'):
            try:
                # 先翻译数据，因为生成器的 build_resource_name 期望接收已翻译的数据
                translated_data = generator.do_translate(row_data.copy())
                custom_name = generator.build_resource_name(translated_data, config)
                if custom_name is not None and custom_name != "":
                    return str(custom_name).strip()
            except Exception as e:
                logger.warning(
                    f"生成器 {generator.__class__.__name__} 的 build_resource_name 方法执行失败，"
                    f"回退到标准逻辑: {e}"
                )
        
        # 使用标准逻辑构建资源名称
        return self._build_resource_name_standard(row_data, config, generator)

    def _build_resource_name_standard(self, row_data: Dict, config: Dict, generator=None) -> str:
        """
        使用标准逻辑构建资源名称（原有逻辑）

        Args:
            row_data: 行数据
            config: 资源配置
            generator: 生成器实例（用于访问 param_config）

        Returns:
            str: 完整的资源名，如果主参数不存在则返回空字符串
        """
        main_param = config["main_param"]
        main_value = row_data.get(main_param)

        if not main_value or main_value == "":
            return ""

        # 确保是字符串类型
        main_value = str(main_value).strip()

        # 翻译主参数 - 使用 param_config 中的 translate_type
        translate_type = None
        if generator and hasattr(generator, 'param_config'):
            param_cfg = generator.param_config.get(main_param, {})
            translate_type = param_cfg.get("translate_type")
        
        # 如果找到了 translate_type，使用它进行翻译
        if translate_type:
            if self.translator.has_mapping(translate_type, main_value):
                main_value = self.translator.translate(translate_type, main_value)
        else:
            # 回退到使用 resource_type（向后兼容）
            if self.translator.has_mapping(config["resource_type"], main_value):
                main_value = self.translator.translate(config["resource_type"], main_value)

        result = str(main_value)
        separator = config.get("separator", " ")

        # 拼接差分参数
        for part_param in config.get("part_params", []):
            if part_param in row_data and row_data[part_param]:
                part_value = str(row_data[part_param]).strip()

                # 尝试翻译差分参数 - 也使用 param_config 中的 translate_type
                part_translate_type = None
                if generator and hasattr(generator, 'param_config'):
                    part_param_cfg = generator.param_config.get(part_param, {})
                    part_translate_type = part_param_cfg.get("translate_type")
                
                if part_translate_type:
                    if self.translator.has_mapping(part_translate_type, part_value):
                        part_value = self.translator.translate(part_translate_type, part_value)
                else:
                    # 回退到使用参数名作为翻译类型
                    if self.translator.has_mapping(part_param, part_value):
                        part_value = self.translator.translate(part_param, part_value)

                part_value = str(part_value)

                if separator:
                    result += f"{separator}{part_value}"
                else:
                    result += part_value

        return result

    def extract_from_excel(self, excel_data: Dict, config=None) -> Dict[str, Dict[str, Set[str]]]:
        """
        从整个 Excel 文件中提取资源

        Args:
            excel_data: Excel 数据 {sheet_name: DataFrame}
            config: 应用配置（可选，用于DataFrameProcessor）
            
        Returns:
            Dict[str, Dict[str, Set[str]]]: {资源类别: {资源类型: {资源名集合}}}
        """
        from core.constants import SheetName
        
        all_resources = defaultdict(lambda: defaultdict(set))

        # 创建DataFrame处理器
        df_processor = DataFrameProcessor(config)

        for sheet_name, sheet_data in excel_data.items():
            # 跳过参数表
            if sheet_name == SheetName.PARAM_SHEET.value:
                continue

            # 提取有效行
            valid_df = df_processor.extract_valid_rows(sheet_data, sheet_name)

            if valid_df.empty:
                continue

            # 遍历有效行
            for _, row in valid_df.iterrows():
                row_dict = row.to_dict()
                
                # 提取这一行的资源
                row_resources = self.extract_from_row(row_dict)
                
                # 按资源类别分类
                for resource_type, resource_names in row_resources.items():
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
            configs = self.get_resource_configs(generator)
            for config in configs:
                if config["resource_type"] == resource_type:
                    return config.get("resource_category", "")
        return ""
