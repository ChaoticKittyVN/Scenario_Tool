"""Shared scenario generation service for production and range-test exports."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

import pandas as pd
from tqdm import tqdm

from core.config_manager import AppConfig
from core.constants import ColumnName, SheetName, TEMP_FILE_PREFIX
from core.engine_loader import load_engine
from core.engine_registry import EngineRegistry
from core.exceptions import ExcelParseError
from core.excel_management import (
    DataFrameProcessor,
    ExcelDataError,
    ExcelFileManager,
    ExcelFileNotFoundError,
    ExcelFormatError,
)
from core.logger import get_logger
from core.param_process.param_translator import ParamTranslator
from core.scenario_generation.models import (
    GeneratedRowBlock,
    GenerationRuntime,
    GenerationSummary,
)
from core.scenario_output import OutputFormat, OutputManager
from core.word_statistics import calculate_dataframe_word_statistics


logger = get_logger(__name__)


def is_excel_output(engine_config: Any) -> bool:
    if hasattr(engine_config, "output_format"):
        return engine_config.output_format == "excel"
    return engine_config.file_extension in (".xlsx", ".xls")


class ScenarioGenerationService:
    """Own the shared row-to-output generation pipeline."""

    def __init__(
        self,
        config: AppConfig,
        *,
        excel_manager: Optional[ExcelFileManager] = None,
        output_manager: Optional[OutputManager] = None,
        translator: Optional[ParamTranslator] = None,
        processor_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        self.config = config
        self.excel_manager = excel_manager or ExcelFileManager(cache_enabled=True)
        self.output_manager = output_manager or OutputManager.create_default()
        self.translator = translator or ParamTranslator(
            module_file=str(config.paths.param_config_dir / "param_mappings.py"),
            variant_module_file=str(config.paths.param_config_dir / "variant_mappings.py"),
        )
        self.processor_factory = processor_factory

    def create_processor(self) -> Any:
        if self.processor_factory is not None:
            return self.processor_factory()

        engine_type = self.config.engine.engine_type
        if not EngineRegistry.is_registered(engine_type):
            load_engine(engine_type)
        engine_metadata = EngineRegistry.get(engine_type)
        return engine_metadata.processor_factory(self.config.engine, self.translator)

    def create_runtime(self) -> GenerationRuntime:
        return GenerationRuntime(
            translator=self.translator,
            processor=self.create_processor(),
            dataframe_processor=DataFrameProcessor(self.config),
        )

    def discover_workbooks(self) -> list[Path]:
        input_dir = Path(self.config.paths.input_dir)
        if not input_dir.exists():
            return []
        return sorted(
            (
                path
                for path in input_dir.iterdir()
                if path.suffix.lower() in (".xlsx", ".xls")
                and not path.name.startswith(TEMP_FILE_PREFIX)
            ),
            key=lambda path: path.name.lower(),
        )

    def load_workbook(self, file_path: Path) -> dict[str, pd.DataFrame]:
        return self.excel_manager.load_excel(file_path)

    def prepare_sheet_rows(
        self,
        dataframe: pd.DataFrame,
        sheet: str,
        runtime: Optional[GenerationRuntime] = None,
    ) -> pd.DataFrame:
        dataframe_processor = (
            runtime.dataframe_processor
            if runtime is not None
            else DataFrameProcessor(self.config)
        )
        return dataframe_processor.extract_valid_rows(dataframe, sheet)

    def process_row(
        self,
        runtime: GenerationRuntime,
        row_data: pd.Series,
        file_basename: str,
        sheet: str,
        context_row: int,
        scenario_index: str,
    ) -> list[Any]:
        runtime.translator.set_context(
            file_basename,
            sheet,
            context_row,
            scenario_index,
        )
        if self.config.engine.use_macro and runtime.processor.has_macro(row_data):
            commands = runtime.processor.process_macro_row(row_data)
        else:
            commands = runtime.processor.process_row(row_data)
        return list(commands or [])

    def process_rows(
        self,
        runtime: GenerationRuntime,
        rows: pd.DataFrame,
        file_basename: str,
        sheet: str,
        *,
        source_row_column: Optional[str] = None,
        enable_progress: Optional[bool] = None,
    ) -> list[GeneratedRowBlock]:
        blocks: list[GeneratedRowBlock] = []
        use_progress = (
            self.config.processing.enable_progress_bar
            if enable_progress is None
            else enable_progress
        )
        iterator: Any = rows.iterrows()
        if use_progress:
            iterator = tqdm(
                iterator,
                total=len(rows),
                desc=f"处理 {file_basename} - {sheet}",
            )

        for position, (_, tracked_row) in enumerate(iterator):
            if source_row_column is not None:
                excel_row = int(tracked_row[source_row_column])
                row_data = tracked_row.drop(labels=[source_row_column])
                context_row = excel_row
            else:
                excel_row = position + 2
                row_data = tracked_row
                # Preserve the legacy zero-based valid-row context in production runs.
                context_row = position

            scenario_index = self._string_value(
                row_data.get(ColumnName.INDEX.value, "")
            )
            try:
                commands = self.process_row(
                    runtime,
                    row_data,
                    file_basename,
                    sheet,
                    context_row,
                    scenario_index,
                )
                blocks.append(
                    GeneratedRowBlock(
                        excel_row=excel_row,
                        scenario_index=scenario_index,
                        command_count=len(commands),
                        commands=commands,
                    )
                )
            except Exception as exc:
                logger.error(
                    f"处理 {file_basename}/{sheet}/Excel 第 {excel_row} 行时出错: {exc}",
                    exc_info=True,
                )
                blocks.append(
                    GeneratedRowBlock(
                        excel_row=excel_row,
                        scenario_index=scenario_index,
                        command_count=0,
                        commands=[],
                        error=str(exc),
                    )
                )
        return blocks

    def write_output(
        self,
        data: Any,
        output_path: Path,
        output_format: OutputFormat,
    ) -> bool:
        success = self.output_manager.output(
            data=data,
            output_path=output_path,
            format=output_format,
            engine_config=self.config.engine,
            apply_formatting=True,
        )
        if success:
            logger.info(f"已生成: {output_path}")
        else:
            logger.error(f"生成文件失败: {output_path}")
        return success

    def generate_sheet(
        self,
        runtime: GenerationRuntime,
        file_basename: str,
        sheet: str,
        dataframe: pd.DataFrame,
        excel_outputs: Optional[dict[str, list[Any]]],
    ) -> bool:
        if sheet == SheetName.PARAM_SHEET.value:
            logger.debug(f"跳过参数表: {sheet}")
            return True

        valid_rows = self.prepare_sheet_rows(dataframe, sheet, runtime)
        if valid_rows.empty:
            logger.warning(f"工作表 {sheet} 没有有效数据")
            return True

        blocks = self.process_rows(runtime, valid_rows, file_basename, sheet)
        commands = [command for block in blocks for command in block.commands]

        statistics = calculate_dataframe_word_statistics(valid_rows)
        logger.info(f"工作表 {sheet} 总字数: {statistics.total}")
        for character_name, count in statistics.by_speaker.items():
            logger.info(f"  说话者 '{character_name}' 字数: {count}")

        self.config.paths.output_dir.mkdir(parents=True, exist_ok=True)
        if is_excel_output(self.config.engine):
            if commands and excel_outputs is not None:
                excel_outputs[sheet] = commands
            return True

        output_path = self.config.paths.output_dir / self.config.engine.get_output_filename(sheet)
        return self.write_output(commands, output_path, OutputFormat.TEXT)

    def generate_workbook(
        self,
        file_path: Path,
        runtime: GenerationRuntime,
    ) -> bool:
        try:
            logger.info(f"开始处理文件: {file_path.name}")
            excel_data = self.load_workbook(file_path)
            excel_outputs: Optional[dict[str, list[Any]]] = (
                {} if is_excel_output(self.config.engine) else None
            )
            for sheet, dataframe in excel_data.items():
                self.generate_sheet(
                    runtime,
                    file_path.stem,
                    sheet,
                    dataframe,
                    excel_outputs,
                )

            if is_excel_output(self.config.engine):
                if excel_outputs:
                    output_path = (
                        self.config.paths.output_dir
                        / f"{file_path.stem}_输出脚本.xlsx"
                    )
                    return self.write_output(
                        excel_outputs,
                        output_path,
                        OutputFormat.EXCEL,
                    )
                logger.warning(f"{file_path.name} 没有任何有效sheet，未生成Excel输出文件。")
            return True
        except (ExcelFileNotFoundError, ExcelFormatError, ExcelDataError):
            raise
        except Exception as exc:
            logger.error(f"处理文件 {file_path} 时出错: {exc}", exc_info=True)
            raise ExcelParseError(f"处理文件失败: {file_path}") from exc

    def generate_all(
        self,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> GenerationSummary:
        def progress(message: str) -> None:
            if progress_callback:
                progress_callback(message)

        input_dir = Path(self.config.paths.input_dir)
        if not input_dir.exists():
            message = f"输入路径不存在: {input_dir}"
            logger.error(message)
            return GenerationSummary(error=message)

        self.config.paths.ensure_dirs_exist()
        excel_files = self.discover_workbooks()
        if not excel_files:
            message = f"在 {input_dir} 中没有找到Excel文件"
            logger.warning(message)
            return GenerationSummary(error=message)

        summary = GenerationSummary(total_files=len(excel_files))
        logger.info(f"找到 {len(excel_files)} 个Excel文件，开始处理...")
        logger.info(f"使用引擎: {self.config.engine.engine_type}")
        progress(f"准备生成 {len(excel_files)} 个文件")

        # Preserve the existing production behavior: one processor per batch.
        runtime = self.create_runtime()
        for index, excel_file in enumerate(excel_files, 1):
            progress(f"[{index}/{len(excel_files)}] 处理 {excel_file.name}")
            try:
                self.generate_workbook(excel_file, runtime)
                summary.succeeded_files += 1
            except (ExcelFileNotFoundError, ExcelFormatError) as exc:
                summary.failed_files += 1
                logger.error(f"处理文件失败，跳过: {excel_file} - {exc}")
            except Exception as exc:
                summary.failed_files += 1
                logger.error(f"处理文件失败: {excel_file} - {exc}", exc_info=True)

        self._finalize_translation_report(summary)
        logger.info(
            "脚本生成完成: "
            f"成功 {summary.succeeded_files}, 失败 {summary.failed_files}"
        )
        progress(
            f"生成完成：成功 {summary.succeeded_files}，失败 {summary.failed_files}"
        )
        return summary

    def _finalize_translation_report(self, summary: GenerationSummary) -> None:
        summary.untranslatable_count = self.translator.get_untranslatable_count()
        if summary.untranslatable_count <= 0:
            logger.info("所有参数均成功翻译")
            return

        logger.info(f"发现 {summary.untranslatable_count} 个无法翻译的参数")
        summary.untranslatable_log = self.translator.export_untranslatable_log(
            self.config.paths.output_dir
        )
        if summary.untranslatable_log:
            logger.info(
                f"无法翻译的参数详细信息已保存至: {summary.untranslatable_log}"
            )

    @staticmethod
    def _string_value(value: Any) -> str:
        if value is None or pd.isna(value):
            return ""
        return str(value)
