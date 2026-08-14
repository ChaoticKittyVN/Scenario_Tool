"""Generate isolated scenario test fragments from Excel row ranges."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

import pandas as pd

from core.config_manager import AppConfig
from core.constants import ColumnName, Marker, SheetName
from core.excel_management import DataFrameProcessor, ExcelFileManager
from core.param_process.param_translator import ParamTranslator
from core.scenario_generation.models import (
    RANGE_MODE_TARGET_ONLY,
    ScenarioRangeCase,
    ScenarioTestCaseResult,
)
from core.scenario_generation.service import ScenarioGenerationService, is_excel_output
from core.scenario_output import OutputFormat, OutputManager


_SOURCE_ROW_COLUMN = "__ScenarioToolExcelRow"
_INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')


class ScenarioTestCaseGenerator:
    """Generate range cases through the shared scenario generation service."""

    def __init__(
        self,
        config: AppConfig,
        excel_manager: Optional[ExcelFileManager] = None,
        output_manager: Optional[OutputManager] = None,
        translator: Optional[ParamTranslator] = None,
        processor_factory: Optional[Callable[[], Any]] = None,
        generation_service: Optional[ScenarioGenerationService] = None,
    ) -> None:
        self.config = config
        self.service = generation_service or ScenarioGenerationService(
            config,
            excel_manager=excel_manager or ExcelFileManager(cache_enabled=False),
            output_manager=output_manager,
            translator=translator,
            processor_factory=processor_factory,
        )

    def generate(
        self,
        input_path: Path,
        cases: Iterable[ScenarioRangeCase],
        output_dir: Path,
    ) -> dict[str, Any]:
        input_path = Path(input_path).resolve()
        output_dir = Path(output_dir).resolve()
        case_list = list(cases)
        if not case_list:
            raise ValueError("至少需要指定一个测试范围")

        duplicate_names = self._duplicate_case_names(case_list)
        if duplicate_names:
            raise ValueError(f"测试用例名称重复: {', '.join(duplicate_names)}")
        duplicate_outputs = self._duplicate_output_filenames(case_list)
        if duplicate_outputs:
            raise ValueError(f"测试用例输出文件名冲突: {', '.join(duplicate_outputs)}")

        excel_data = self.service.load_workbook(input_path)
        cases_by_sheet: dict[str, list[ScenarioRangeCase]] = {}
        for case in case_list:
            if case.sheet == SheetName.PARAM_SHEET.value:
                raise ValueError("参数表不能用于生成测试片段")
            if case.sheet not in excel_data:
                raise ValueError(f"工作表不存在: {case.sheet}")
            cases_by_sheet.setdefault(case.sheet, []).append(case)

        output_dir.mkdir(parents=True, exist_ok=True)
        results_by_name: dict[str, ScenarioTestCaseResult] = {}
        for sheet, sheet_cases in cases_by_sheet.items():
            sheet_results = self._generate_sheet_cases(
                input_path,
                sheet,
                excel_data[sheet],
                sheet_cases,
                output_dir,
            )
            results_by_name.update({result.name: result for result in sheet_results})

        ordered_results = [results_by_name[case.case_name] for case in case_list]
        manifest = {
            "input": str(input_path),
            "engine": self.config.engine.engine_type,
            "output_dir": str(output_dir),
            "cases": [asdict(result) for result in ordered_results],
            "success": all(result.success for result in ordered_results),
        }
        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        manifest["manifest"] = str(manifest_path)
        return manifest

    def _generate_sheet_cases(
        self,
        input_path: Path,
        sheet: str,
        dataframe: pd.DataFrame,
        cases: list[ScenarioRangeCase],
        output_dir: Path,
    ) -> list[ScenarioTestCaseResult]:
        if dataframe.empty:
            raise ValueError(f"工作表为空: {sheet}")

        tracked = dataframe.copy()
        tracked[_SOURCE_ROW_COLUMN] = range(2, len(tracked) + 2)
        end_position = DataFrameProcessor(self.config).find_marker_position(
            tracked,
            ColumnName.NOTE.value,
            Marker.END.value,
        )
        if end_position == -1:
            raise ValueError(f"工作表 {sheet} 没有 END 标记")
        end_excel_row = int(tracked.iloc[end_position][_SOURCE_ROW_COLUMN])

        for case in cases:
            if case.end_row >= end_excel_row:
                raise ValueError(
                    f"{case.case_name}: 目标结束行 {case.end_row} 必须早于 END 所在的第 {end_excel_row} 行"
                )

        valid_rows = self.service.prepare_sheet_rows(tracked, sheet)
        valid_excel_rows = {int(value) for value in valid_rows[_SOURCE_ROW_COLUMN]}

        results: list[ScenarioTestCaseResult] = []
        shared_groups: dict[int, list[ScenarioRangeCase]] = {}
        isolated_cases: list[ScenarioRangeCase] = []
        for case in cases:
            if case.effective_mode == RANGE_MODE_TARGET_ONLY:
                isolated_cases.append(case)
            else:
                shared_groups.setdefault(case.effective_replay_start, []).append(case)

        for replay_start, grouped_cases in shared_groups.items():
            results.extend(
                self._generate_case_group(
                    input_path,
                    sheet,
                    valid_rows,
                    valid_excel_rows,
                    grouped_cases,
                    replay_start,
                    output_dir,
                )
            )

        for case in isolated_cases:
            results.extend(
                self._generate_case_group(
                    input_path,
                    sheet,
                    valid_rows,
                    valid_excel_rows,
                    [case],
                    case.start_row,
                    output_dir,
                )
            )
        return results

    def _generate_case_group(
        self,
        input_path: Path,
        sheet: str,
        valid_rows: pd.DataFrame,
        valid_excel_rows: set[int],
        cases: list[ScenarioRangeCase],
        replay_start: int,
        output_dir: Path,
    ) -> list[ScenarioTestCaseResult]:
        max_target_row = max(case.end_row for case in cases)
        replay_rows = valid_rows[
            (valid_rows[_SOURCE_ROW_COLUMN] >= replay_start)
            & (valid_rows[_SOURCE_ROW_COLUMN] <= max_target_row)
        ]
        runtime = self.service.create_runtime()
        blocks = self.service.process_rows(
            runtime,
            replay_rows,
            input_path.stem,
            sheet,
            source_row_column=_SOURCE_ROW_COLUMN,
            enable_progress=False,
        )
        blocks_by_row = {block.excel_row: block for block in blocks}

        results: list[ScenarioTestCaseResult] = []
        for case in cases:
            processed_blocks = [
                block for block in blocks if block.excel_row <= case.end_row
            ]
            selected_blocks = [
                blocks_by_row[row]
                for row in range(case.output_start_row, case.end_row + 1)
                if row in blocks_by_row
            ]
            commands: list[Any] = []
            if case.label:
                commands.extend(
                    self._generate_label_commands(case.label, input_path, sheet)
                )
            for block in selected_blocks:
                commands.extend(block.commands)

            output_path = output_dir / self._output_filename(case)
            success = self._write_output(commands, output_path)
            skipped_rows = [
                row
                for row in range(case.output_start_row, case.end_row + 1)
                if row not in valid_excel_rows
            ]
            row_errors = {
                block.excel_row: block.error
                for block in processed_blocks
                if block.error is not None
            }
            results.append(
                ScenarioTestCaseResult(
                    name=case.case_name,
                    sheet=sheet,
                    mode=case.effective_mode,
                    target_start=case.start_row,
                    target_end=case.end_row,
                    replay_start=case.effective_replay_start,
                    output_start=case.output_start_row,
                    label=case.label,
                    output_file=str(output_path) if success else None,
                    processed_rows=len(processed_blocks),
                    warmup_rows=sum(
                        block.excel_row < case.output_start_row
                        for block in processed_blocks
                    ),
                    output_rows=len(selected_blocks),
                    generated_commands=len(commands),
                    skipped_rows=skipped_rows,
                    row_errors=row_errors,
                    success=success and not row_errors,
                )
            )
        return results

    def _generate_label_commands(
        self,
        label: str,
        input_path: Path,
        sheet: str,
    ) -> list[Any]:
        runtime = self.service.create_runtime()
        label_row = pd.Series(
            {
                ColumnName.NAME.value: "label",
                ColumnName.TEXT.value: label,
            }
        )
        commands = self.service.process_row(
            runtime,
            label_row,
            input_path.stem,
            sheet,
            0,
            "",
        )
        return [command for command in commands if command not in (None, "", {})]

    def _write_output(self, commands: list[Any], output_path: Path) -> bool:
        output_format = (
            OutputFormat.EXCEL
            if is_excel_output(self.config.engine)
            else OutputFormat.TEXT
        )
        return self.service.write_output(commands, output_path, output_format)

    def _output_filename(self, case: ScenarioRangeCase) -> str:
        safe_name = self._safe_case_name(case)
        extension = (
            ".xlsx"
            if is_excel_output(self.config.engine)
            else self.config.engine.file_extension
        )
        return f"{safe_name}{extension}"

    @staticmethod
    def _safe_case_name(case: ScenarioRangeCase) -> str:
        safe_name = _INVALID_FILENAME_CHARS.sub("_", case.case_name).strip(" .")
        return safe_name or f"R{case.start_row}-R{case.end_row}"

    @staticmethod
    def _duplicate_case_names(cases: list[ScenarioRangeCase]) -> list[str]:
        seen = set()
        duplicates = set()
        for case in cases:
            if case.case_name in seen:
                duplicates.add(case.case_name)
            seen.add(case.case_name)
        return sorted(duplicates)

    @classmethod
    def _duplicate_output_filenames(cls, cases: list[ScenarioRangeCase]) -> list[str]:
        seen = set()
        duplicates = set()
        for case in cases:
            safe_name = cls._safe_case_name(case).casefold()
            if safe_name in seen:
                duplicates.add(cls._safe_case_name(case))
            seen.add(safe_name)
        return sorted(duplicates)
