"""
场景脚本生成主程序
从 Excel 文件生成视觉小说引擎脚本
"""
import pandas as pd
import os
from pathlib import Path
from typing import Optional
from tqdm import tqdm
from core.config_manager import AppConfig
from core.param_translator import ParamTranslator
from core.engine_registry import EngineRegistry
from core.logger import get_logger
from core.exceptions import ExcelParseError, GeneratorError
from core.constants import SheetName, ColumnName, Marker, TEMP_FILE_PREFIX
from core.word_counter import BasicWordCounter

from core.excel_management import (
    ExcelManagerError,
    ExcelFileNotFoundError,
    ExcelFormatError,
    ExcelDataError,
    ExcelFileManager,
    DataFrameProcessor
)

# 导入输出管理器
from core.scenario_output import OutputManager, OutputFormat

# 导入引擎模块以触发注册
import engines.renpy
import engines.naninovel
import engines.utage

logger = get_logger()


def is_excel_output(engine_config) -> bool:
    """
    判断引擎是否输出Excel格式

    Args:
        engine_config: 引擎配置对象

    Returns:
        bool: 如果输出格式为Excel则返回True，否则返回False
    """
    # 检查是否有output_format属性
    if hasattr(engine_config, 'output_format'):
        return engine_config.output_format == "excel"
    # 如果没有output_format属性，检查文件扩展名
    return engine_config.file_extension in ['.xlsx', '.xls']


def import_engine_module(engine_type: str):
    """
    根据引擎类型动态导入引擎模块以触发注册

    Args:
        engine_type: 引擎类型（renpy, naninovel, utage）

    Raises:
        ImportError: 无法导入引擎模块
        ValueError: 不支持的引擎类型
    """
    engine_module_map = {
        "renpy": "engines.renpy",
        "naninovel": "engines.naninovel",
        "utage": "engines.utage"
    }

    if engine_type not in engine_module_map:
        raise ValueError(f"不支持的引擎类型: {engine_type}")

    module_name = engine_module_map[engine_type]
    try:
        __import__(module_name)
        logger.debug(f"已导入引擎模块: {module_name}")
    except ImportError as e:
        logger.error(f"无法导入引擎模块 {module_name}: {e}")
        raise


def create_processor(config: AppConfig, translator: ParamTranslator):
    """
    创建处理器实例

    Args:
        config: 应用配置
        translator: 参数翻译器

    Returns:
        处理器实例
    """
    # 确保引擎模块已导入并注册
    if not EngineRegistry.is_registered(config.engine.engine_type):
        import_engine_module(config.engine.engine_type)

    # 从注册表获取引擎元数据
    engine_meta = EngineRegistry.get(config.engine.engine_type)

    # 使用工厂函数创建处理器
    processor = engine_meta.processor_factory(config.engine, translator)

    return processor


def load_excel_data(file_path: Path) -> dict:
    """
    加载Excel文件数据

    Args:
        file_path: Excel 文件路径

    Returns:
        dict: 工作表名称到DataFrame的映射

    Raises:
        ExcelFileNotFoundError: 文件不存在
        ExcelFormatError: 文件格式错误
        ExcelDataError: 数据提取错误
    """
    excel_manager = ExcelFileManager(cache_enabled=True)
    excel_data = excel_manager.load_excel(file_path)
    return excel_data


def process_sheet_rows(
    processor,
    valid_rows_df: pd.DataFrame,
    df_processor: DataFrameProcessor,
    file_basename: str,
    sheet: str,
    translator: ParamTranslator,
    config: AppConfig
) -> list:
    """
    处理工作表的行数据，生成输出命令列表

    Args:
        processor: 处理器实例
        valid_rows_df: 有效行DataFrame
        df_processor: DataFrame处理器
        file_basename: 文件基本名
        sheet: 工作表名称
        translator: 参数翻译器
        config: 应用配置

    Returns:
        list: 输出命令列表
    """
    output_list = []

    # 使用进度条处理
    desc = f"处理 {file_basename} - {sheet}"
    if config.processing.enable_progress_bar:
        iterator = tqdm(range(len(valid_rows_df)), desc=desc)
    else:
        iterator = range(len(valid_rows_df))

    for idx in iterator:
        row_data = valid_rows_df.iloc[idx]
        try:
            # 设置翻译器上下文信息
            translator.set_context(file_basename, sheet, idx, row_data.get("Index", ""))

            commands = processor.process_row(row_data)
            if commands:
                output_list.extend(commands)
        except Exception as e:
            logger.error(f"处理第 {idx} 行时出错: {e}", exc_info=True)

    return output_list


def calculate_word_statistics(
    valid_rows_df: pd.DataFrame,
    df_processor: DataFrameProcessor,
    sheet: str
):
    """
    计算字数统计信息

    Args:
        valid_rows_df: 有效行DataFrame
        df_processor: DataFrame处理器
        sheet: 工作表名称
    """
    word_counter = BasicWordCounter()

    # 使用专用方法提取统计列
    stat_columns = df_processor.extract_columns_for_statistics(
        valid_rows_df, [ColumnName.NAME.value, ColumnName.TEXT.value]
    )

    name_series = stat_columns.get(ColumnName.NAME.value, pd.Series(dtype=object))
    text_series = stat_columns.get(ColumnName.TEXT.value, pd.Series(dtype=object))

    # 统计总字数
    total_words = word_counter.count(text_series.tolist())
    logger.info(f"工作表 {sheet} 总字数: {total_words}")

    # 按说话者统计字数
    total_words_by_chara_name = word_counter.count_by(list(zip(
        name_series,
        text_series
    )))
    for chara_name, count in total_words_by_chara_name.items():
        logger.info(f"  说话者 '{chara_name}' 字数: {count}")


def output_sheet_file(
    output_list: list,
    output_file_path: Path,
    config: AppConfig
) -> bool:
    """
    输出单个工作表文件（非Excel格式引擎）

    Args:
        output_list: 输出命令列表
        output_file_path: 输出文件路径
        config: 应用配置

    Returns:
        bool: 是否成功
    """
    output_manager = OutputManager.create_default()
    success = output_manager.output(
        data=output_list,
        output_path=output_file_path,
        format=OutputFormat.TEXT,
        engine_config=config.engine,
        apply_formatting=True
    )

    if success:
        logger.info(f"已生成: {output_file_path}")
    else:
        logger.error(f"生成文件失败: {output_file_path}")

    return success


def output_excel_file(
    excel_outputs: dict,
    output_file_path: Path,
    config: AppConfig
) -> bool:
    """
    输出Excel统一文件

    Args:
        excel_outputs: 工作表名称到输出列表的映射
        output_file_path: 输出文件路径
        config: 应用配置

    Returns:
        bool: 是否成功
    """
    output_manager = OutputManager.create_default()
    success = output_manager.output(
        data=excel_outputs,
        output_path=output_file_path,
        format=OutputFormat.EXCEL,
        engine_config=config.engine,
        apply_formatting=True
    )

    if success:
        logger.info(f"已生成: {output_file_path}")
    else:
        logger.error(f"生成文件失败: {output_file_path}")

    return success


def process_sheet(
    sheet: str,
    sheet_df: pd.DataFrame,
    processor,
    df_processor: DataFrameProcessor,
    file_basename: str,
    translator: ParamTranslator,
    config: AppConfig,
    excel_outputs: Optional[dict]
):
    """
    处理单个工作表

    Args:
        sheet: 工作表名称
        sheet_df: 工作表DataFrame
        processor: 处理器实例
        df_processor: DataFrame处理器
        file_basename: 文件基本名
        translator: 参数翻译器
        config: 应用配置
        excel_outputs: Excel输出字典（用于收集Excel格式输出）
    """
    # 跳过参数表
    if sheet == SheetName.PARAM_SHEET.value:
        logger.debug(f"跳过参数表: {sheet}")
        return

    # 判断是否为Excel输出格式
    is_excel = is_excel_output(config.engine)

    # 生成输出文件名
    if is_excel:
        # 对于Excel格式：原文件名_工作表名.xlsx
        scenario_name = f"{file_basename}_{sheet}.xlsx"
    else:
        # 对于其他格式：文件名.rpy/.nani
        scenario_name = config.engine.get_output_filename(sheet)

    # 使用DataFrameProcessor提取有效行
    valid_rows_df = df_processor.extract_valid_rows(sheet_df, sheet)

    if valid_rows_df.empty:
        logger.warning(f"工作表 {sheet} 没有有效数据")
        return

    # 处理行数据
    output_list = process_sheet_rows(
        processor, valid_rows_df, df_processor,
        file_basename, sheet, translator, config
    )

    # 计算字数统计
    calculate_word_statistics(valid_rows_df, df_processor, sheet)

    # 确保输出目录存在
    config.paths.output_dir.mkdir(parents=True, exist_ok=True)

    # 收集Excel输出或直接输出文件
    if is_excel:
        if output_list and excel_outputs is not None:  # 只收集非空sheet
            excel_outputs[sheet] = output_list
    else:
        output_file_path = config.paths.output_dir / scenario_name
        output_sheet_file(output_list, output_file_path, config)


def process_excel_file(file_path: Path, config: AppConfig, translator: ParamTranslator):
    """
    处理单个Excel文件

    Args:
        file_path: Excel 文件路径
        config: 应用配置
        translator: 参数翻译器（用于追踪上下文）

    Raises:
        ExcelFileNotFoundError: 文件不存在
        ExcelFormatError: 文件格式错误
        ExcelDataError: 数据提取错误
    """
    try:
        logger.info(f"开始处理文件: {file_path.name}")
        processor = create_processor(config, translator)

        # 加载Excel数据
        excel_data = load_excel_data(file_path)
        sheet_names = list(excel_data.keys())

        # 判断是否为Excel输出格式
        is_excel = is_excel_output(config.engine)
        excel_outputs = {} if is_excel else None

        # 使用DataFrameProcessor处理数据
        df_processor = DataFrameProcessor(config)

        # 获取文件基本名（不含扩展名）
        file_basename = file_path.stem

        # 处理每个工作表
        for sheet in sheet_names:
            process_sheet(
                sheet, excel_data[sheet], processor, df_processor,
                file_basename, translator, config, excel_outputs
            )

        # Excel格式统一输出
        if is_excel and excel_outputs:
            scenario_name = f"{file_basename}_输出脚本.xlsx"
            output_file_path = config.paths.output_dir / scenario_name
            output_excel_file(excel_outputs, output_file_path, config)
        elif is_excel and not excel_outputs:
            logger.warning(f"{file_path.name} 没有任何有效sheet，未生成Excel输出文件。")



    except (ExcelFileNotFoundError, ExcelFormatError, ExcelDataError) as e:
        # 重新抛出给main函数处理
        raise
    except Exception as e:
        logger.error(f"处理文件 {file_path} 时出错: {e}", exc_info=True)
        raise ExcelParseError(f"处理文件失败: {file_path}") from e


def main():
    """主函数"""
    try:
        # 加载配置
        config_path = Path("config.yaml")
        if config_path.exists():
            logger.info(f"从配置文件加载: {config_path}")
            config = AppConfig.from_file(config_path)
        else:
            logger.info("使用默认配置")
            config = AppConfig.create_default("naninovel")

        # 确保目录存在
        config.paths.ensure_dirs_exist()

        # 确保输入路径存在
        if not config.paths.input_dir.exists():
            logger.error(f"输入路径不存在: {config.paths.input_dir}")
            return

        # 获取所有Excel文件
        excel_files = [
            f for f in config.paths.input_dir.iterdir()
            if f.suffix in ['.xlsx', '.xls'] and not f.name.startswith(TEMP_FILE_PREFIX)
        ]

        if not excel_files:
            logger.warning(f"在 {config.paths.input_dir} 中没有找到Excel文件")
            return

        logger.info(f"找到 {len(excel_files)} 个Excel文件，开始处理...")
        logger.info(f"使用引擎: {config.engine.engine_type}")

        # 根据配置动态导入引擎模块
        import_engine_module(config.engine.engine_type)

        # 创建翻译器（用于追踪无法翻译的参数）
        translator = ParamTranslator(
            module_file=str(config.paths.param_config_dir / "param_mappings.py"),
            varient_module_file=str(config.paths.param_config_dir / "varient_mappings.py")
        )

        # 处理每个Excel文件
        for excel_file in excel_files:
            try:
                process_excel_file(excel_file, config, translator)
            except ExcelFileNotFoundError as e:
                logger.error(f"文件不存在，跳过: {excel_file} - {e}")
                continue
            except ExcelFormatError as e:
                logger.error(f"Excel格式错误，跳过: {excel_file} - {e}")
                continue
            except Exception as e:
                logger.error(f"处理文件失败: {excel_file} - {e}")
                continue

        logger.info("所有文件处理完成")

        # 导出无法翻译的参数日志
        untranslatable_count = translator.get_untranslatable_count()
        if untranslatable_count > 0:
            logger.info(f"发现 {untranslatable_count} 个无法翻译的参数")
            log_path = translator.export_untranslatable_log(config.paths.output_dir)
            if log_path:
                logger.info(f"无法翻译的参数详细信息已保存至: {log_path}")
        else:
            logger.info("所有参数均成功翻译")

    except Exception as e:
        logger.critical(f"程序执行失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
