"""Preview and synchronize parameter sheets in scenario workbooks."""

from pathlib import Path
from typing import Dict, List, Optional

from core.excel_management import ExcelEditor, ExcelWriteError
from core.logger import get_logger
from core.sentence_generator_manager import SentenceGeneratorManager


logger = get_logger()


class ParameterSheetSyncMixin:
    """Synchronize validation data into scenario workbook parameter sheets."""

    def get_all_validate_params(self) -> Dict[str, List[str]]:
        """Return translate and validation parameter types from generators."""
        try:
            manager = SentenceGeneratorManager(self.engine_type)
            return manager.get_validate_params()
        except Exception as exc:
            logger.error(f"获取数据验证参数类型时发生错误: {exc}")
            return {}

    def update_scenario_param_sheets(
        self,
        validation_data: Dict[str, List[str]],
        scenario_workbooks: Optional[List[Path]] = None,
    ) -> bool:
        """Write validation data into scenario workbook parameter sheets."""
        if not validation_data:
            logger.error("没有收集到验证数据")
            return False

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

        excel_files = [path for path in excel_files if not path.name.startswith("~")]
        missing_files = [path for path in excel_files if not path.exists()]
        for missing_file in missing_files:
            logger.error(f"指定的演出表格不存在: {missing_file}")
        excel_files = [
            path
            for path in excel_files
            if path.exists() and path.suffix.lower() == ".xlsx"
        ]

        if not excel_files:
            location = (
                str(input_dir)
                if scenario_workbooks is None
                else "显式工作簿列表"
            )
            logger.warning(f"在 {location} 中没有找到 Excel 文件")
            return True

        logger.debug(f"找到 {len(excel_files)} 个演出表格文件")
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
                parameter_data = {
                    param_type: workbook_validation_data.get(param_type, [])
                    for param_type in all_params
                }
                try:
                    success = excel_writer.update_parameter_sheet(
                        excel_file,
                        "参数表",
                        parameter_data,
                        create_named_ranges=True,
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
                except ExcelWriteError as exc:
                    logger.error(f"  写入Excel失败: {excel_file} - {exc}")
                except PermissionError as exc:
                    logger.error(f"  文件被占用或无写入权限: {excel_file} - {exc}")
                except Exception as exc:
                    logger.error(f"  处理文件时发生错误: {excel_file} - {exc}")
            except Exception as exc:
                logger.error(
                    f"  处理文件 {excel_file.name} 时发生错误: {exc}",
                    exc_info=True,
                )

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
        """Preview parameter-sheet targets without writing files."""
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

    def sync_parameter_sheets(
        self,
        scenario_workbooks: Optional[List[Path]] = None,
        dry_run: bool = False,
    ) -> bool:
        """Collect validation data and synchronize scenario parameter sheets."""
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
        except Exception as exc:
            logger.error(f"更新演出表格参数表时失败: {exc}")
            return False
