"""Orchestrate parameter mapping generation and workbook synchronization."""

from pathlib import Path
from typing import List, Optional

from core.config_manager import AppConfig
from core.excel_management import ExcelFileManager
from core.logger import get_logger
from core.param_update.mapping_export import MappingExportMixin
from core.param_update.project_scope import ProjectScopeMixin
from core.param_update.sheet_sync import ParameterSheetSyncMixin
from core.param_update.sources import ParamSourceMixin
from core.param_update.variant_export import VariantAgentExportMixin


logger = get_logger()


class ParamUpdater(
    ProjectScopeMixin,
    ParamSourceMixin,
    MappingExportMixin,
    VariantAgentExportMixin,
    ParameterSheetSyncMixin,
):
    """Public facade for all parameter update operations."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.engine_type = config.engine.engine_type
        self.excel_manager = ExcelFileManager(cache_enabled=True)

    def update_mappings(
        self,
        scenario_workbooks: Optional[List[Path]] = None,
        generate_mapping_files: bool = True,
        update_parameter_sheets: bool = True,
        dry_run: bool = False,
    ) -> bool:
        """Generate mappings and/or synchronize parameter sheets."""
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
            agent_export_config = getattr(self.config, "variant_agent_export", None)
            if (
                agent_export_config is not None
                and agent_export_config.enabled is True
            ):
                if not self.export_agent_variant_document(dry_run):
                    return False

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
                    self,
                    "_variant_file_for_parameter_sync",
                ):
                    del self._variant_file_for_parameter_sync

        logger.debug("=" * 60)
        logger.info("参数映射更新完成")
        logger.debug("=" * 60)
        return True
