"""Generate complete engine scenarios from configured Excel workbooks."""

from pathlib import Path
from typing import Callable, Optional

from core.config_manager import AppConfig
from core.logger import get_logger
from core.scenario_output import OutputFormat, OutputManager
from core.scenario_generation import (
    GenerationRuntime,
    GenerationSummary,
    ScenarioGenerationService,
    is_excel_output,
)
from core.word_statistics import calculate_dataframe_word_statistics


logger = get_logger()


def import_engine_module(engine_type: str):
    """Backward-compatible engine loader wrapper."""
    from core.engine_loader import load_engine

    return load_engine(engine_type)


def create_processor(config: AppConfig, translator):
    """Backward-compatible processor factory wrapper."""
    service = ScenarioGenerationService(config, translator=translator)
    return service.create_processor()


def load_excel_data(file_path: Path) -> dict:
    """Backward-compatible workbook loader wrapper."""
    from core.excel_management import ExcelFileManager

    return ExcelFileManager(cache_enabled=True).load_excel(file_path)


def process_sheet_rows(
    processor,
    valid_rows_df,
    df_processor,
    file_basename: str,
    sheet: str,
    translator,
    config: AppConfig,
) -> list:
    """Backward-compatible row-processing wrapper."""
    service = ScenarioGenerationService(
        config,
        translator=translator,
        processor_factory=lambda: processor,
    )
    runtime = GenerationRuntime(translator, processor, df_processor)
    blocks = service.process_rows(runtime, valid_rows_df, file_basename, sheet)
    return [command for block in blocks for command in block.commands]


def calculate_word_statistics(valid_rows_df, df_processor, sheet: str):
    """Backward-compatible word-statistics wrapper."""
    statistics = calculate_dataframe_word_statistics(valid_rows_df)
    logger.info(f"工作表 {sheet} 总字数: {statistics.total}")
    for character_name, count in statistics.by_speaker.items():
        logger.info(f"  说话者 '{character_name}' 字数: {count}")
    return statistics


def output_sheet_file(output_list: list, output_file_path: Path, config: AppConfig) -> bool:
    """Backward-compatible text-output wrapper."""
    success = OutputManager.create_default().output(
        data=output_list,
        output_path=output_file_path,
        format=OutputFormat.TEXT,
        engine_config=config.engine,
        apply_formatting=True,
    )
    if success:
        logger.info(f"已生成: {output_file_path}")
    else:
        logger.error(f"生成文件失败: {output_file_path}")
    return success


def output_excel_file(excel_outputs: dict, output_file_path: Path, config: AppConfig) -> bool:
    """Backward-compatible Excel-output wrapper."""
    success = OutputManager.create_default().output(
        data=excel_outputs,
        output_path=output_file_path,
        format=OutputFormat.EXCEL,
        engine_config=config.engine,
        apply_formatting=True,
    )
    if success:
        logger.info(f"已生成: {output_file_path}")
    else:
        logger.error(f"生成文件失败: {output_file_path}")
    return success


def process_sheet(
    sheet,
    sheet_df,
    processor,
    df_processor,
    file_basename,
    translator,
    config,
    excel_outputs,
):
    """Backward-compatible single-sheet wrapper."""
    service = ScenarioGenerationService(
        config,
        translator=translator,
        processor_factory=lambda: processor,
    )
    runtime = GenerationRuntime(translator, processor, df_processor)
    return service.generate_sheet(
        runtime,
        file_basename,
        sheet,
        sheet_df,
        excel_outputs,
    )


def process_excel_file(file_path: Path, config: AppConfig, processor, translator):
    """Backward-compatible single-workbook wrapper."""
    service = ScenarioGenerationService(
        config,
        translator=translator,
        processor_factory=lambda: processor,
    )
    runtime = service.create_runtime()
    return service.generate_workbook(file_path, runtime)


def generate_scenarios(
    config: AppConfig,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> GenerationSummary:
    """Run the complete generation workflow shared by CLI and GUI."""
    return ScenarioGenerationService(config).generate_all(progress_callback)


def main() -> int:
    try:
        config_path = Path("config.yaml")
        if config_path.exists():
            logger.info(f"从配置文件加载: {config_path}")
            config = AppConfig.from_file(config_path)
        else:
            logger.info("使用默认配置")
            config = AppConfig.create_default("naninovel")
        summary = generate_scenarios(config)
        return 0 if summary.success else 1
    except Exception as exc:
        logger.critical(f"程序执行失败: {exc}", exc_info=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
