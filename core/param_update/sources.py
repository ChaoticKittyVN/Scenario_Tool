"""Read mapping and validation data from parameter workbooks."""

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from core.excel_management import ExcelFileNotFoundError, ExcelFormatError
from core.logger import get_logger


logger = get_logger()


class ParamSourceMixin:
    """Read param_data and variant_data workbook contents."""

    def _default_param_file(self) -> Path:
        """Return the base parameter workbook for the current engine."""
        return (
            Path(self.config.paths.param_config_dir)
            / f"param_data_{self.engine_type}.xlsx"
        )

    def _variant_data_file(self) -> Path:
        """Return the configured variant parameter workbook."""
        return Path(self.config.paths.param_config_dir) / "variant_data.xlsx"

    def read_param_file(
        self,
        param_file: Path,
        skip_template: bool = True,
    ) -> Dict[str, Dict[str, str]]:
        """Read ExcelParam-to-ScenarioParam mappings from every valid sheet."""
        if not param_file.exists():
            logger.error(f"参数文件不存在: {param_file}")
            return {}

        try:
            sheets = self.excel_manager.load_excel(param_file)
            logger.debug(f"读取到 {len(sheets)} 个工作表")
            mappings = {}

            for sheet_name, df in sheets.items():
                if skip_template and "模板" in sheet_name:
                    logger.debug(f"跳过模板工作表: {sheet_name}")
                    continue
                if "ExcelParam" not in df.columns or "ScenarioParam" not in df.columns:
                    logger.warning(f"工作表 {sheet_name} 缺少必需的列，跳过")
                    continue

                sheet_mapping = {}
                for _, row in df.iterrows():
                    excel_param = row["ExcelParam"]
                    scenario_param = row["ScenarioParam"]
                    if pd.notna(excel_param) and pd.notna(scenario_param):
                        sheet_mapping[str(excel_param)] = str(scenario_param)

                if not skip_template or sheet_mapping:
                    mappings[sheet_name] = sheet_mapping
                    if sheet_mapping:
                        logger.debug(
                            f"工作表 {sheet_name}: {len(sheet_mapping)} 个映射"
                        )
            return mappings
        except ExcelFileNotFoundError as exc:
            logger.error(f"参数文件不存在: {param_file} - {exc}")
            return {}
        except ExcelFormatError as exc:
            logger.error(f"参数文件格式错误: {param_file} - {exc}")
            return {}
        except Exception as exc:
            logger.error(f"读取参数文件失败: {exc}", exc_info=True)
            return {}

    def collect_validation_data(
        self,
        param_file: Path,
        variant_file: Optional[Path] = None,
    ) -> Dict[str, List[str]]:
        """Collect validation values from base and optional variant workbooks."""
        validation_data = {}
        try:
            base_sheets = self.excel_manager.load_excel(param_file)
            for sheet_name, df in base_sheets.items():
                if "ExcelParam" not in df.columns:
                    continue
                params = []
                for _, row in df.iterrows():
                    excel_param = row["ExcelParam"]
                    if pd.notna(excel_param):
                        param_str = str(excel_param)
                        if param_str:
                            params.append(param_str)
                if params:
                    validation_data[sheet_name] = params
                    logger.debug(f"收集参数 {sheet_name}: {len(params)} 个值")
        except (ExcelFileNotFoundError, ExcelFormatError) as exc:
            logger.error(f"读取基础参数文件失败: {param_file} - {exc}")
            return {}
        except Exception as exc:
            logger.error(f"读取基础参数文件时发生未知错误: {exc}", exc_info=True)
            return {}

        if variant_file is not None and variant_file.exists():
            try:
                variant_sheets = self.excel_manager.load_excel(variant_file)
                all_variant_params = set()
                for _, df in variant_sheets.items():
                    if "ExcelParam" not in df.columns:
                        continue
                    for _, row in df.iterrows():
                        excel_param = row["ExcelParam"]
                        if pd.notna(excel_param):
                            param_str = str(excel_param).strip()
                            if param_str:
                                all_variant_params.add(param_str)

                if all_variant_params:
                    existing_variants = set(validation_data.get("Variant", []))
                    validation_data["Variant"] = sorted(
                        existing_variants.union(all_variant_params)
                    )
                    logger.debug(f"收集差分参数: {len(all_variant_params)} 个值")
            except (ExcelFileNotFoundError, ExcelFormatError) as exc:
                logger.warning(f"读取差分参数文件失败: {variant_file} - {exc}")
            except Exception as exc:
                logger.warning(f"读取差分参数文件时发生未知错误: {exc}")

        return validation_data
