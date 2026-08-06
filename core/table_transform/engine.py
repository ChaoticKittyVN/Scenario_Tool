"""Workbook-level planning and application for declarative table operations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import pandas as pd
import yaml

from core.excel_management.excel_editor import CellUpdate, ExcelEditor
from core.excel_management.excel_file_manager import ExcelFileManager
from core.logger import get_logger

from .base import OperationContext, TableOperation
from .models import ChangePlan, FileTransformResult
from .operations import BUILTIN_OPERATIONS
from .registry import OperationRegistry


logger = get_logger()


@dataclass
class TransformDefinition:
    operations: List[TableOperation]
    conflict_policy: str = "error"


def load_definition(
    config_path: Path,
    registry: Optional[OperationRegistry] = None,
) -> TransformDefinition:
    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"表格变更配置不存在: {config_path}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"表格变更配置无法解析: {exc}") from exc

    if not isinstance(config, dict):
        raise ValueError("表格变更配置根节点必须是对象。")
    if config.get("version", 1) != 1:
        raise ValueError(f"不支持的配置版本: {config.get('version')}")

    operation_registry = registry or OperationRegistry()
    for operation_class in BUILTIN_OPERATIONS:
        operation_registry.register(operation_class)

    plugins = config.get("plugins", [])
    if not isinstance(plugins, list):
        raise ValueError("plugins 必须是 module:Class 字符串列表。")
    for plugin in plugins:
        operation_registry.load_plugin(str(plugin))

    operation_configs = config.get("operations")
    if not isinstance(operation_configs, list) or not operation_configs:
        raise ValueError("配置必须包含非空的 operations 列表。")

    operations: List[TableOperation] = []
    seen_ids = set()
    for index, operation_config in enumerate(operation_configs, 1):
        if not isinstance(operation_config, dict):
            raise ValueError(f"第 {index} 个操作必须是对象。")
        operation_id = operation_config.get("id")
        operation_type = operation_config.get("op")
        if not isinstance(operation_id, str) or not operation_id:
            raise ValueError(f"第 {index} 个操作缺少有效 id。")
        if operation_id in seen_ids:
            raise ValueError(f"操作 id 重复: {operation_id}")
        if not isinstance(operation_type, str) or not operation_type:
            raise ValueError(f"操作 {operation_id} 缺少 op。")
        if "target" not in operation_config:
            raise ValueError(f"操作 {operation_id} 缺少 target。")
        seen_ids.add(operation_id)
        operations.append(
            operation_registry.create(operation_type, operation_id, operation_config)
        )

    conflict_policy = config.get("conflict_policy", "error")
    if conflict_policy not in ("error", "first", "last"):
        raise ValueError("conflict_policy 必须是 error、first 或 last。")
    return TransformDefinition(operations=operations, conflict_policy=conflict_policy)


class TableTransformEngine:
    """Plan changes first, then optionally apply them through ExcelEditor."""

    def __init__(
        self,
        definition: TransformDefinition,
        excel_manager: Optional[ExcelFileManager] = None,
        excel_editor: Optional[ExcelEditor] = None,
    ):
        self.definition = definition
        self.excel_manager = excel_manager or ExcelFileManager(cache_enabled=True)
        self.excel_editor = excel_editor or ExcelEditor()

    @classmethod
    def from_config(cls, config_path: Path) -> "TableTransformEngine":
        return cls(load_definition(config_path))

    def reset(self) -> None:
        for operation in self.definition.operations:
            operation.reset()
        self.excel_manager.clear_cache()

    @staticmethod
    def discover_files(input_dir: Path) -> List[Path]:
        if not input_dir.exists():
            raise FileNotFoundError(f"输入目录不存在: {input_dir}")
        return sorted(
            (
                path
                for path in input_dir.iterdir()
                if path.suffix.lower() in (".xlsx", ".xlsm")
                and not path.name.startswith("~")
            ),
            key=lambda path: path.name.lower(),
        )

    @staticmethod
    def _operation_matches_sheet(operation: TableOperation, sheet_name: str) -> bool:
        sheets = operation.config.get("sheets", [])
        exclude_sheets = operation.config.get("exclude_sheets", [])
        if sheets and sheet_name not in sheets:
            return False
        if exclude_sheets and sheet_name in exclude_sheets:
            return False
        return operation.config.get("enabled", True) is not False

    def plan_file(
        self,
        file_path: Path,
        sheet_names: Optional[Sequence[str]] = None,
    ) -> ChangePlan:
        excel_data = self.excel_manager.load_excel(file_path)
        selected_sheets = (
            [sheet for sheet in sheet_names if sheet in excel_data]
            if sheet_names
            else list(excel_data)
        )
        plan = ChangePlan(file_path=file_path)

        for sheet_name in selected_sheets:
            dataframe = excel_data[sheet_name]
            if dataframe.empty:
                continue
            working = dataframe.copy()
            plan.sheets_processed += 1
            for operation in self.definition.operations:
                if not self._operation_matches_sheet(operation, sheet_name):
                    continue
                context = OperationContext(file_path, sheet_name, working)
                for change in operation.plan(context):
                    accepted = plan.add(change, self.definition.conflict_policy)
                    if accepted:
                        working.at[change.dataframe_index, change.column] = change.new_value
        return plan

    def apply_plan(self, plan: ChangePlan) -> bool:
        if not plan.changes:
            return True
        updates = [
            CellUpdate(
                sheet_name=change.sheet,
                row=change.row,
                column=change.column,
                value=change.new_value,
                preserve_style=True,
            )
            for change in plan.changes
        ]
        success = self.excel_editor.update_cells_batch(plan.file_path, updates)
        if success:
            self.excel_manager.clear_cache()
        return success

    def process_file(
        self,
        file_path: Path,
        dry_run: bool = True,
        sheet_names: Optional[Sequence[str]] = None,
    ) -> FileTransformResult:
        try:
            plan = self.plan_file(file_path, sheet_names)
            applied = False
            if not dry_run and plan.changes:
                applied = self.apply_plan(plan)
                if not applied:
                    return FileTransformResult(file_path, False, False, plan, "写入失败")
            return FileTransformResult(file_path, True, applied, plan)
        except Exception as exc:
            logger.error(f"表格变更失败: {file_path} - {exc}", exc_info=True)
            return FileTransformResult(
                file_path=file_path,
                success=False,
                applied=False,
                plan=ChangePlan(file_path=file_path),
                error=str(exc),
            )

    def process_directory(
        self,
        input_dir: Path,
        dry_run: bool = True,
        sheet_names: Optional[Sequence[str]] = None,
    ) -> List[FileTransformResult]:
        self.reset()
        return [
            self.process_file(file_path, dry_run=dry_run, sheet_names=sheet_names)
            for file_path in self.discover_files(input_dir)
        ]


def summarize_results(results: Iterable[FileTransformResult]) -> Dict[str, int]:
    result_list = list(results)
    return {
        "files": len(result_list),
        "success": sum(1 for result in result_list if result.success),
        "failed": sum(1 for result in result_list if not result.success),
        "changed_files": sum(1 for result in result_list if result.plan.changes),
        "applied_files": sum(1 for result in result_list if result.applied),
        "changes": sum(len(result.plan.changes) for result in result_list),
    }
