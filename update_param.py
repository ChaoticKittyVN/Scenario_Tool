"""
参数映射更新工具
从 Excel 参数文件生成 Python 参数映射模块
"""
import argparse
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
from openpyxl import load_workbook
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from core.sentence_generator_manager import SentenceGeneratorManager
from core.config_manager import AppConfig, _create_engine_config
from core.logger import get_logger
from core.excel_management import (
    ExcelManagerError,
    ExcelFileNotFoundError,
    ExcelFormatError,
    ExcelDataError,
    ExcelWriteError,
    ExcelFileManager,
    DataFrameProcessor,
    ExcelEditor
)

logger = get_logger()


class ParamUpdater:
    """参数映射更新器"""

    def __init__(self, config: AppConfig):
        """
        初始化参数更新器

        Args:
            config: 应用配置
        """
        self.config = config
        self.engine_type = config.engine.engine_type
        self.excel_manager = ExcelFileManager(cache_enabled=True)
        self.df_processor = DataFrameProcessor(config)

    @property
    def multi_project_mode(self) -> bool:
        """是否启用按项目扩展参数数据。"""
        processing = getattr(self.config, "processing", None)
        return getattr(processing, "multi_project_mode", False) is True

    @property
    def projects(self) -> Dict[str, str]:
        """返回有效的项目键与文件名识别文本。"""
        projects = getattr(self.config, "projects", {})
        if not isinstance(projects, dict):
            return {}
        return {
            str(project_key): str(match_text)
            for project_key, match_text in projects.items()
            if str(project_key).strip() and str(match_text).strip()
        }

    def _find_project_param_files(self) -> List[tuple[Path, str]]:
        """查找配置中启用的项目参数文件。"""
        if not self.multi_project_mode:
            return []

        param_dir = Path(self.config.paths.param_config_dir)
        results = []
        for project_key in self.projects:
            project_file = param_dir / f"param_data_{project_key}.xlsx"
            if project_file.exists():
                results.append((project_file, project_key))
                logger.info(f"发现项目参数文件: {project_file.name} (项目: {project_key})")
            else:
                logger.warning(f"项目参数文件不存在，跳过: {project_file}")
        return results

    @staticmethod
    def _merge_mappings(
        mappings_list: List[Dict[str, Dict[str, str]]],
    ) -> Dict[str, Dict[str, str]]:
        """依次合并映射，后面的项目配置覆盖同名映射。"""
        merged: Dict[str, Dict[str, str]] = {}
        for mappings in mappings_list:
            for sheet_name, sheet_mapping in mappings.items():
                merged.setdefault(sheet_name, {}).update(sheet_mapping)
        return merged

    @staticmethod
    def _merge_validation_data(
        data_list: List[Dict[str, List[str]]],
    ) -> Dict[str, List[str]]:
        """按参数类型合并、去重验证值，并保留原有顺序。"""
        merged: Dict[str, List[str]] = {}
        for data in data_list:
            for param_type, values in data.items():
                target = merged.setdefault(param_type, [])
                existing = set(target)
                for value in values:
                    if value not in existing:
                        target.append(value)
                        existing.add(value)
        return merged

    def _match_project_for_excel(self, excel_file: Path) -> Optional[str]:
        """根据工作簿文件名匹配项目。"""
        if not self.multi_project_mode:
            return None

        filename = excel_file.name
        matches = [
            (project_key, match_text)
            for project_key, match_text in self.projects.items()
            if match_text in filename
        ]
        if not matches:
            logger.debug(f"文件 {filename} 未匹配到项目参数")
            return None
        if len(matches) > 1:
            matched_keys = ", ".join(project_key for project_key, _ in matches)
            logger.warning(f"文件 {filename} 匹配到多个项目 ({matched_keys})，使用第一个")
        project_key, match_text = matches[0]
        logger.info(f"文件 {filename} 匹配到项目: {project_key} ({match_text})")
        return project_key

    def _validation_data_for_workbook(
        self,
        excel_file: Path,
        base_validation_data: Dict[str, List[str]],
        project_cache: Dict[str, Dict[str, List[str]]],
    ) -> Dict[str, List[str]]:
        """为单个工作簿合并基础参数和匹配项目的扩展参数。"""
        project_key = self._match_project_for_excel(excel_file)
        if project_key is None:
            return base_validation_data

        if project_key not in project_cache:
            project_file = (
                Path(self.config.paths.param_config_dir)
                / f"param_data_{project_key}.xlsx"
            )
            if not project_file.exists():
                logger.warning(f"项目 '{project_key}' 的参数文件不存在: {project_file}")
                project_cache[project_key] = {}
            else:
                project_cache[project_key] = self.collect_validation_data(project_file)

        project_data = project_cache[project_key]
        if not project_data:
            return base_validation_data
        logger.info(f"为 {excel_file.name} 合并项目 '{project_key}' 的定制参数")
        return self._merge_validation_data([base_validation_data, project_data])

    def read_param_file(self, param_file: Path, skip_template: bool = True) -> Dict[str, Dict[str, str]]:
        """
        读取参数文件并生成映射

        Args:
            param_file: 参数文件路径
            skip_template: 是否跳过模板工作表

        Returns:
            Dict[str, Dict[str, str]]: 参数映射字典
        """
        if not param_file.exists():
            logger.error(f"参数文件不存在: {param_file}")
            return {}

        try:
            # 使用新的ExcelFileManager读取所有工作表
            sheets = self.excel_manager.load_excel(param_file)
            logger.debug(f"读取到 {len(sheets)} 个工作表")

            mappings = {}

            for sheet_name, df in sheets.items():
                # 根据参数决定是否跳过模板工作表
                if skip_template and "模板" in sheet_name:
                    logger.debug(f"跳过模板工作表: {sheet_name}")
                    continue

                # 检查必需的列
                if "ExcelParam" not in df.columns or "ScenarioParam" not in df.columns:
                    logger.warning(f"工作表 {sheet_name} 缺少必需的列，跳过")
                    continue

                # 构建映射
                sheet_mapping = {}
                for _, row in df.iterrows():
                    excel_param = row["ExcelParam"]
                    scenario_param = row["ScenarioParam"]

                    if pd.notna(excel_param) and pd.notna(scenario_param):
                        sheet_mapping[str(excel_param)] = str(scenario_param)

                # 对于差分参数文件，保留空映射（包括模板）
                if not skip_template or sheet_mapping:
                    mappings[sheet_name] = sheet_mapping
                    if sheet_mapping:
                        logger.debug(f"工作表 {sheet_name}: {len(sheet_mapping)} 个映射")

            return mappings

        except ExcelFileNotFoundError as e:
            logger.error(f"参数文件不存在: {param_file} - {e}")
            return {}
        except ExcelFormatError as e:
            logger.error(f"参数文件格式错误: {param_file} - {e}")
            return {}
        except Exception as e:
            logger.error(f"读取参数文件失败: {e}", exc_info=True)
            return {}

    def generate_mappings_file(self, mappings: Dict[str, Dict[str, str]], output_file: Path):
        """
        生成参数映射 Python 文件

        Args:
            mappings: 参数映射字典
            output_file: 输出文件路径
        """
        try:
            # 根据文件名确定变量名
            variable_name = "VARIANT_MAPPINGS" if "variant" in output_file.name else "PARAM_MAPPINGS"

            with open(output_file, "w", encoding="utf-8") as f:
                f.write("# 自动生成的参数映射文件\n")
                f.write("# 请不要手动编辑此文件\n")
                f.write(f"# 引擎类型: {self.engine_type}\n\n")
                f.write(f"{variable_name} = ")

                # 使用 repr 生成格式化的字典
                import pprint
                f.write(pprint.pformat(mappings, width=100, sort_dicts=False))
                f.write("\n")

            logger.debug(f"参数映射已保存到: {output_file}")

        except Exception as e:
            logger.error(f"保存参数映射文件失败: {e}", exc_info=True)

    def collect_validation_data(
        self, 
        param_file: Path, 
        variant_file: Optional[Path] = None  # 修改类型注解
    ) -> Dict[str, List[str]]:
        """
        收集所有验证数据（基础参数 + 差分参数）

        Args:
            param_file: 基础参数文件路径
            variant_file: 差分参数文件路径（可选）

        Returns:
            Dict[str, List[str]]: 参数名 -> 参数值列表
        """
        validation_data = {}

        # 1. 收集基础参数
        try:
            base_sheets = self.excel_manager.load_excel(param_file)

            for sheet_name, df in base_sheets.items():
                # 检查是否有 ExcelParam 列
                if "ExcelParam" not in df.columns:
                    continue

                # 提取参数值
                params = []
                for _, row in df.iterrows():
                    excel_param = row["ExcelParam"]
                    # 使用空值检查方法
                    if pd.notna(excel_param):
                        param_str = str(excel_param)
                        if param_str:
                            params.append(param_str)

                # 只保存非空的参数列表
                if params:
                    validation_data[sheet_name] = params
                    logger.debug(f"收集参数 {sheet_name}: {len(params)} 个值")

        except (ExcelFileNotFoundError, ExcelFormatError) as e:
            logger.error(f"读取基础参数文件失败: {param_file} - {e}")
            return {}
        except Exception as e:
            logger.error(f"读取基础参数文件时发生未知错误: {e}", exc_info=True)
            return {}

        # 2. 收集差分参数
        if variant_file is not None and variant_file.exists():
            try:
                variant_sheets = self.excel_manager.load_excel(variant_file)

                # 收集所有差分参数名
                all_variant_params = set()
                for sheet_name, df in variant_sheets.items():
                    if "ExcelParam" not in df.columns:
                        continue

                    for _, row in df.iterrows():
                        excel_param = row["ExcelParam"]
                        if pd.notna(excel_param):
                            param_str = str(excel_param).strip()
                            if param_str:
                                all_variant_params.add(param_str)

                # 将差分参数合并到 Variant 列
                if all_variant_params:
                    if "Variant" in validation_data:
                        # 合并去重
                        existing_variants = set(validation_data["Variant"])
                        combined_variants = existing_variants.union(all_variant_params)
                        validation_data["Variant"] = sorted(list(combined_variants))
                    else:
                        validation_data["Variant"] = sorted(list(all_variant_params))

                    logger.debug(f"收集差分参数: {len(all_variant_params)} 个值")

            except (ExcelFileNotFoundError, ExcelFormatError) as e:
                logger.warning(f"读取差分参数文件失败: {variant_file} - {e}")
            except Exception as e:
                logger.warning(f"读取差分参数文件时发生未知错误: {e}")

        return validation_data

    def get_all_validate_params(self) -> Dict[str, List[str]]:
        """
        获取所有句子生成器的参数翻译类型
        
        Returns:
            Dict[str, List[str]]: 包含translate_types和validate_types的字典
        """
        try:
            # 创建管理器实例
            manager = SentenceGeneratorManager(self.engine_type)
            # 调用我们之前写的方法
            return manager.get_validate_params()
        except Exception as e:
            logger.error(f"获取数据验证参数类型时发生错误: {e}")
            return {}

    def update_scenario_param_sheets(
        self,
        validation_data: Dict[str, List[str]],
        scenario_workbooks: Optional[List[Path]] = None,
    ) -> bool:
        """
        更新演出表格中的参数表工作表

        Args:
            validation_data: 参数验证数据

        Returns:
            bool: 是否成功
        """
        if not validation_data:
            logger.error("没有收集到验证数据")
            return False
        
        # 获取参数翻译类型列表
        param_types = self.get_all_validate_params()
        if not param_types:
            logger.error("无法获取参数翻译类型词典")
            return False

        translate_params = param_types.get("translate_types", [])
        validate_params = param_types.get("validate_types", [])

        all_params = sorted(validate_params + translate_params)

        if scenario_workbooks is None:
            input_dir = Path(self.config.paths.input_dir)
            if not input_dir.exists():
                logger.error(f"输入目录不存在: {input_dir}")
                return False
            excel_files = list(input_dir.glob("*.xlsx"))
        else:
            excel_files = [Path(path) for path in scenario_workbooks]

        excel_files = [f for f in excel_files if not f.name.startswith("~")]
        missing_files = [f for f in excel_files if not f.exists()]
        for missing_file in missing_files:
            logger.error(f"指定的演出表格不存在: {missing_file}")
        excel_files = [f for f in excel_files if f.exists() and f.suffix.lower() == ".xlsx"]

        if not excel_files:
            location = str(input_dir) if scenario_workbooks is None else "显式工作簿列表"
            logger.warning(f"在 {location} 中没有找到 Excel 文件")
            return True

        logger.debug(f"找到 {len(excel_files)} 个演出表格文件")
        # 创建 ExcelEditor 实例
        excel_writer = ExcelEditor()
        success_count = 0
        updated_count = 0
        unchanged_count = 0
        project_cache: Dict[str, Dict[str, List[str]]] = {}

        for excel_file in excel_files:
            try:
                logger.debug(f"处理文件: {excel_file.name}")
                workbook_validation_data = self._validation_data_for_workbook(
                    excel_file,
                    validation_data,
                    project_cache,
                )

                # 准备参数数据（按照 all_params 的顺序）
                parameter_data = {}
                for param_type in all_params:
                    params = workbook_validation_data.get(param_type, [])
                    parameter_data[param_type] = params

                # 使用增强的 ExcelEditor 方法更新参数表
                try:
                    success = excel_writer.update_parameter_sheet(
                        excel_file,
                        "参数表",
                        parameter_data,
                        create_named_ranges=True
                    )

                    if success:
                        success_count += 1
                        if excel_writer.last_update_status == "unchanged":
                            unchanged_count += 1
                            logger.info(f"参数表无变化: {excel_file.name}")
                        else:
                            updated_count += 1
                            logger.info(f"参数表已更新: {excel_file.name}")
                    else:
                        logger.error(f"  更新参数表失败: {excel_file.name}")
                        
                except ExcelWriteError as e:
                    logger.error(f"  写入Excel失败: {excel_file} - {e}")
                except PermissionError as e:
                    logger.error(f"  文件被占用或无写入权限: {excel_file} - {e}")
                except Exception as e:
                    logger.error(f"  处理文件时发生错误: {excel_file} - {e}")

            except Exception as e:
                logger.error(f"  处理文件 {excel_file.name} 时发生错误: {e}", exc_info=True)

        failed_count = len(excel_files) - success_count
        logger.info(
            "参数表处理完成: "
            f"已更新 {updated_count}, 无变化 {unchanged_count}, 失败 {failed_count}"
        )
        return success_count > 0

    def preview_scenario_param_sheets(
        self,
        validation_data: Dict[str, List[str]],
        scenario_workbooks: Optional[List[Path]] = None,
    ) -> bool:
        """预览参数表同步范围，不写入任何文件。"""
        param_types = self.get_all_validate_params()
        if not param_types:
            logger.error("无法获取参数翻译类型词典")
            return False

        all_params = sorted(
            param_types.get("validate_types", [])
            + param_types.get("translate_types", [])
        )
        if scenario_workbooks is None:
            input_dir = Path(self.config.paths.input_dir)
            if not input_dir.exists():
                logger.error(f"输入目录不存在: {input_dir}")
                return False
            excel_files = list(input_dir.glob("*.xlsx"))
        else:
            excel_files = [Path(path) for path in scenario_workbooks]

        excel_files = [
            path
            for path in excel_files
            if path.exists()
            and path.suffix.lower() == ".xlsx"
            and not path.name.startswith("~")
        ]
        logger.info("DRY RUN：不会修改演出表格")
        logger.info(f"将同步 {len(excel_files)} 个工作簿、{len(all_params)} 个参数类型")
        project_cache: Dict[str, Dict[str, List[str]]] = {}
        for excel_file in excel_files:
            workbook_validation_data = self._validation_data_for_workbook(
                excel_file,
                validation_data,
                project_cache,
            )
            project_key = self._match_project_for_excel(excel_file)
            project_label = f", 项目={project_key}" if project_key else ""
            logger.info(f"  参数表目标: {excel_file}{project_label}")
            for param_type in all_params:
                logger.debug(
                    f"    参数类型 {param_type}: "
                    f"{len(workbook_validation_data.get(param_type, []))} 个值"
                )
        return True

    def _default_param_file(self) -> Path:
        """返回当前引擎的基础参数文件。"""
        return (
            Path(self.config.paths.param_config_dir)
            / f"param_data_{self.engine_type}.xlsx"
        )

    def _variant_data_file(self) -> Path:
        """返回差分参数文件。"""
        return Path(self.config.paths.param_config_dir) / "variant_data.xlsx"

    def generate_param_mappings(self, dry_run: bool = False) -> bool:
        """生成 param_mappings.py。"""
        param_file = self._default_param_file()
        if not param_file.exists():
            logger.error(f"参数文件不存在: {param_file}")
            logger.info("请确保参数文件存在")
            return False

        try:
            logger.debug(f"读取参数文件: {param_file}")
            mappings_list = [self.read_param_file(param_file)]
            project_param_files = self._find_project_param_files()
            for project_file, project_key in project_param_files:
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
            mode_label = "多项目合并参数映射" if self.multi_project_mode else "基础参数映射"
            logger.info(
                f"{mode_label}: {len(mappings)} 个工作表, {total_mappings} 个映射"
            )
            return True
        except Exception as e:
            logger.error(f"处理基础参数映射时失败: {e}")
            return False

    def generate_variant_mappings(
        self,
        dry_run: bool = False,
    ) -> tuple[bool, Optional[Path]]:
        """生成 variant_mappings.py，并返回可用于参数表同步的 variant_data 路径。"""
        variant_file = self._variant_data_file()
        if not variant_file.exists():
            logger.debug("差分参数文件不存在，跳过")
            return True, None

        logger.debug(f"读取差分参数文件: {variant_file}")
        try:
            # 差分参数文件不跳过模板工作表，保持与原项目一致
            variant_mappings = self.read_param_file(variant_file, skip_template=False)

            # 生成差分映射文件（保持与原项目一致，包含空映射）
            variant_output = (
                Path(self.config.paths.param_config_dir) / "variant_mappings.py"
            )
            action = "将生成" if dry_run else "生成"
            logger.debug(f"{action}差分参数映射文件: {variant_output}")
            if not dry_run:
                self.generate_mappings_file(variant_mappings, variant_output)

            # 统计有效映射（排除模板）
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
        except Exception as e:
            logger.error(f"处理差分参数映射时失败: {e}")
            return False, None

    def sync_parameter_sheets(
        self,
        scenario_workbooks: Optional[List[Path]] = None,
        dry_run: bool = False,
    ) -> bool:
        """收集基础、篇章和差分验证数据，并同步演出表参数表。"""
        param_file = self._default_param_file()
        if not param_file.exists():
            logger.error(f"参数文件不存在: {param_file}")
            logger.info("请确保参数文件存在")
            return False

        logger.debug("=" * 60)
        logger.debug("更新演出表格参数表")
        logger.debug("=" * 60)

        if hasattr(self, "_variant_file_for_parameter_sync"):
            variant_file = self._variant_file_for_parameter_sync
        else:
            configured_variant_file = self._variant_data_file()
            variant_file = (
                configured_variant_file if configured_variant_file.exists() else None
            )
        try:
            validation_data = self.collect_validation_data(param_file, variant_file)
            if not validation_data:
                logger.warning("未能收集到验证数据，跳过演出表格更新")
                return True

            logger.debug(f"收集到 {len(validation_data)} 个参数类型的验证数据")
            if dry_run:
                success = self.preview_scenario_param_sheets(
                    validation_data,
                    scenario_workbooks,
                )
            else:
                success = self.update_scenario_param_sheets(
                    validation_data,
                    scenario_workbooks,
                )
            if not success:
                logger.warning("更新演出表格参数表时出现错误，但主流程继续")
            return success
        except Exception as e:
            logger.error(f"更新演出表格参数表时失败: {e}")
            return False

    def update_mappings(
        self,
        scenario_workbooks: Optional[List[Path]] = None,
        generate_mapping_files: bool = True,
        update_parameter_sheets: bool = True,
        dry_run: bool = False,
    ) -> bool:
        """生成映射并/或同步参数表；默认行为保持原完整流程。"""
        logger.debug("=" * 60)
        logger.info(f"开始更新参数映射: 引擎={self.engine_type}")
        if dry_run:
            logger.info("执行模式: DRY RUN")
        elif generate_mapping_files and not update_parameter_sheets:
            logger.info("执行模式: 仅生成映射")
        elif update_parameter_sheets and not generate_mapping_files:
            logger.info("执行模式: 仅同步参数表")
        else:
            logger.info("执行模式: 完整更新")
        logger.debug("=" * 60)

        param_file = self._default_param_file()
        if not param_file.exists():
            logger.error(f"参数文件不存在: {param_file}")
            logger.info("请确保参数文件存在")
            return False

        variant_file_path: Optional[Path] = None
        if generate_mapping_files:
            if not self.generate_param_mappings(dry_run):
                return False
            _, variant_file_path = self.generate_variant_mappings(dry_run)

        if update_parameter_sheets:
            if generate_mapping_files:
                self._variant_file_for_parameter_sync = variant_file_path
            try:
                self.sync_parameter_sheets(
                    scenario_workbooks=scenario_workbooks,
                    dry_run=dry_run,
                )
            finally:
                if generate_mapping_files and hasattr(
                    self, "_variant_file_for_parameter_sync"
                ):
                    del self._variant_file_for_parameter_sync

        logger.debug("=" * 60)
        logger.info("参数映射更新完成")
        logger.debug("=" * 60)

        return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="更新参数映射并同步演出表格的参数表。")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径。")
    parser.add_argument(
        "--engine",
        choices=["renpy", "naninovel", "utage"],
        help="覆盖 config.yaml 中的 engine_type。",
    )
    parser.add_argument(
        "--workbook",
        action="append",
        help="只同步指定演出工作簿的参数表，可重复指定。省略时处理配置中的 input_dir。",
    )
    execution_mode = parser.add_mutually_exclusive_group()
    execution_mode.add_argument(
        "--dry-run",
        action="store_true",
        help="只读取并报告将执行的操作，不写入映射文件或 Excel。",
    )
    execution_mode.add_argument(
        "--apply",
        action="store_true",
        help="显式执行写入；不带 --dry-run 时本来就会执行，用于提高命令可读性。",
    )
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument(
        "--mappings-only",
        action="store_true",
        help="只生成 param_mappings.py 和 variant_mappings.py，不更新演出表格。",
    )
    scope.add_argument(
        "--parameter-sheet-only",
        action="store_true",
        help="只从 param_data/variant_data 同步参数表，不重新生成映射模块。",
    )
    return parser.parse_args()


def main() -> int:
    """主函数"""
    try:
        args = parse_args()
        # 加载配置
        config_path = Path(args.config)
        if not config_path.exists():
            logger.error(f"配置文件不存在: {config_path}")
            return 2

        config = AppConfig.from_file(config_path)
        if args.engine:
            config.engine = _create_engine_config(args.engine)

        # 创建更新器
        updater = ParamUpdater(config)

        # 执行更新
        workbooks = [Path(path).resolve() for path in args.workbook] if args.workbook else None
        generate_mapping_files = not args.parameter_sheet_only
        update_parameter_sheets = not args.mappings_only
        if args.mappings_only and workbooks:
            logger.warning("--mappings-only 模式不会使用 --workbook 参数")
        success = updater.update_mappings(
            workbooks,
            generate_mapping_files=generate_mapping_files,
            update_parameter_sheets=update_parameter_sheets,
            dry_run=args.dry_run,
        )

        if success:
            return 0
        else:
            logger.error("参数映射更新失败")
            return 1

    except KeyboardInterrupt:
        logger.info("用户中断操作")
        return 130
    except Exception as e:
        logger.critical(f"参数更新过程失败: {e}", exc_info=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
