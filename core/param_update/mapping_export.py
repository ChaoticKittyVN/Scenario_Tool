"""Generate Python mapping modules from parameter workbook data."""

import pprint
from pathlib import Path
from typing import Dict, Optional

from core.logger import get_logger


logger = get_logger()


class MappingExportMixin:
    """Generate base and variant Python mapping modules."""

    def generate_mappings_file(
        self,
        mappings: Dict[str, Dict[str, str]],
        output_file: Path,
    ) -> None:
        """Write mappings as a generated Python module."""
        try:
            variable_name = (
                "VARIANT_MAPPINGS"
                if "variant" in output_file.name
                else "PARAM_MAPPINGS"
            )
            with open(output_file, "w", encoding="utf-8") as file:
                file.write("# 自动生成的参数映射文件\n")
                file.write("# 请不要手动编辑此文件\n")
                file.write(f"# 引擎类型: {self.engine_type}\n\n")
                file.write(f"{variable_name} = ")
                file.write(pprint.pformat(mappings, width=100, sort_dicts=False))
                file.write("\n")
            logger.debug(f"参数映射已保存到: {output_file}")
        except Exception as exc:
            logger.error(f"保存参数映射文件失败: {exc}", exc_info=True)

    def generate_param_mappings(self, dry_run: bool = False) -> bool:
        """Generate param_mappings.py."""
        param_file = self._default_param_file()
        if not param_file.exists():
            logger.error(f"参数文件不存在: {param_file}")
            logger.info("请确保参数文件存在")
            return False

        try:
            logger.debug(f"读取参数文件: {param_file}")
            mappings_list = [self.read_param_file(param_file)]
            for project_file, project_key in self._find_project_param_files():
                project_mappings = self.read_param_file(project_file)
                if project_mappings:
                    mappings_list.append(project_mappings)
                    logger.info(f"已加载项目 '{project_key}' 的参数映射")
            mappings = self._merge_mappings(mappings_list)
            if not mappings:
                logger.error("未能读取到任何参数映射")
                return False

            output_file = Path(self.config.paths.param_config_dir) / "param_mappings.py"
            action = "将生成" if dry_run else "生成"
            logger.debug(f"{action}参数映射文件: {output_file}")
            if not dry_run:
                self.generate_mappings_file(mappings, output_file)

            total_mappings = sum(len(mapping) for mapping in mappings.values())
            mode_label = (
                "多项目合并参数映射" if self.multi_project_mode else "基础参数映射"
            )
            logger.info(
                f"{mode_label}: {len(mappings)} 个工作表, {total_mappings} 个映射"
            )
            return True
        except Exception as exc:
            logger.error(f"处理基础参数映射时失败: {exc}")
            return False

    def generate_variant_mappings(
        self,
        dry_run: bool = False,
    ) -> tuple[bool, Optional[Path]]:
        """Generate variant_mappings.py and return its source workbook path."""
        variant_file = self._variant_data_file()
        if not variant_file.exists():
            logger.debug("差分参数文件不存在，跳过")
            return True, None

        logger.debug(f"读取差分参数文件: {variant_file}")
        try:
            variant_mappings = self.read_param_file(variant_file, skip_template=False)
            variant_output = (
                Path(self.config.paths.param_config_dir) / "variant_mappings.py"
            )
            action = "将生成" if dry_run else "生成"
            logger.debug(f"{action}差分参数映射文件: {variant_output}")
            if not dry_run:
                self.generate_mappings_file(variant_mappings, variant_output)

            valid_mappings = {
                key: value
                for key, value in variant_mappings.items()
                if value and "模板" not in key
            }
            if valid_mappings:
                total_variant = sum(
                    len(mapping) for mapping in valid_mappings.values()
                )
                logger.info(
                    f"差分参数映射: {len(valid_mappings)} 个角色, "
                    f"{total_variant} 个映射"
                )
            else:
                logger.info("差分参数文件中没有有效的角色映射")
            return True, variant_file
        except Exception as exc:
            logger.error(f"处理差分参数映射时失败: {exc}")
            return False, None
