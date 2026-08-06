"""
语音测试脚本生成主程序
从 Excel 文件生成用于语音测试的视觉小说引擎脚本
支持两种输入格式：
1. 原始剧本 Excel（多工作表）
2. 配音台本 Excel/CSV（单工作表，包含 Name、Text、Voice、Index 列）
"""
import sys
import pandas as pd
import os
from pathlib import Path
from typing import Optional
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config_manager import AppConfig
from core.param_process.param_translator import ParamTranslator
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
    processor = engine_meta.processor_factory(
        config.engine,
        translator,
        generator_categories=['Voice', 'Text'],
        )

    return processor


def load_excel_data(file_path: Path) -> dict:
    """
    加载 Excel 文件数据（原始剧本格式）

    Args:
        file_path: Excel 文件路径

    Returns:
        dict: 工作表名称到 DataFrame 的映射

    Raises:
        ExcelFileNotFoundError: 文件不存在
        ExcelFormatError: 文件格式错误
        ExcelDataError: 数据提取错误
    """
    excel_manager = ExcelFileManager(cache_enabled=True)
    excel_data = excel_manager.load_excel(file_path)
    return excel_data


def load_dialogue_script(file_path: Path) -> pd.DataFrame:
    """
    加载配音台本格式的文件（Excel 或 CSV）
    自动将常见列名映射为标准格式（Name, Text, Voice, Index）
    
    Args:
        file_path: 文件路径
        
    Returns:
        pd.DataFrame: 配音台本数据，包含 Name、Text、Voice、Index 列
        
    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 文件格式不正确
    """
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在：{file_path}")
    
    # 根据扩展名读取文件
    if file_path.suffix in ['.xlsx', '.xls']:
        df = pd.read_excel(file_path)
    elif file_path.suffix == '.csv':
        df = pd.read_csv(file_path, encoding='utf-8-sig')
    else:
        raise ValueError(f"不支持的文件格式：{file_path.suffix}")
    
    logger.info(f"原始列名：{list(df.columns)}")
    
    # 定义常见的列名映射关系
    column_mapping = {
        # Name 列的可能名称
        '角色': ColumnName.NAME.value,
        '说话人': ColumnName.NAME.value,
        '说话者': ColumnName.NAME.value,
        '姓名': ColumnName.NAME.value,
        'name': ColumnName.NAME.value,
        'speaker': ColumnName.NAME.value,
        
        # Text 列的可能名称
        '文本': ColumnName.TEXT.value,
        '对话': ColumnName.TEXT.value,
        '台词': ColumnName.TEXT.value,
        '内容': ColumnName.TEXT.value,
        'text': ColumnName.TEXT.value,
        'dialog': ColumnName.TEXT.value,
        'content': ColumnName.TEXT.value,
        
        # Voice 列的可能名称
        '语音文件名': ColumnName.VOICE.value,
        '语音': ColumnName.VOICE.value,
        '音频': ColumnName.VOICE.value,
        'voice': ColumnName.VOICE.value,
        'audio': ColumnName.VOICE.value,
        'voice_file': ColumnName.VOICE.value,
        
        # Index 列的可能名称
        '文本行号': ColumnName.INDEX.value,
        '行号': ColumnName.INDEX.value,
        '索引': ColumnName.INDEX.value,
        '编号': ColumnName.INDEX.value,
        'index': ColumnName.INDEX.value,
        'line_number': ColumnName.INDEX.value,
    }
    
    # 重命名列
    renamed_columns = {}
    for col in df.columns:
        col_lower = col.strip().lower()
        if col_lower in column_mapping:
            new_name = column_mapping[col_lower]
            renamed_columns[col] = new_name
            logger.debug(f"列名映射：'{col}' -> '{new_name}'")
    
    df = df.rename(columns=renamed_columns)
    
    logger.info(f"转换后列名：{list(df.columns)}")
    
    # 检查必需的列
    required_columns = [ColumnName.NAME.value, ColumnName.TEXT.value]
    missing_cols = [col for col in required_columns if col not in df.columns]
    
    if missing_cols:
        logger.error(f"缺少必需的列：{missing_cols}")
        logger.error(f"当前列：{list(df.columns)}")
        logger.error(f"原始列：{list(df.columns)}")
        raise ValueError(
            f"配音台本格式不正确，缺少必需的列：{missing_cols}\n"
            f"请确保文件包含以下列（或其别名）：\n"
            f"  - Name (角色/说话人/姓名/speaker)\n"
            f"  - Text (文本/对话/台词/text)"
        )
    
    # 如果缺少 Voice 列，添加空列
    if ColumnName.VOICE.value not in df.columns:
        logger.warning(f"缺少 {ColumnName.VOICE.value} 列，将使用空值")
        df[ColumnName.VOICE.value] = ""
    
    # 如果缺少 Index 列，添加行号
    if ColumnName.INDEX.value not in df.columns:
        logger.warning(f"缺少 {ColumnName.INDEX.value} 列，将自动生成行号")
        df[ColumnName.INDEX.value] = [f"{i+1:04d}" for i in range(len(df))]
    
    logger.info(f"成功加载配音台本：{file_path.name}，共 {len(df)} 条记录")
    return df


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

            # 对于使用macro引擎，如果检测到Macro指令，使用Macro专用处理流程
            # 其他引擎或没有Macro的情况，使用普通处理流程
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

    # 处理行数据
    output_list = process_sheet_rows(
        processor, sheet_df, df_processor,
        file_basename, sheet, translator, config
    )

    # 计算字数统计
    calculate_word_statistics(sheet_df, df_processor, sheet)

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
    处理单个 Excel 文件（原始剧本格式）

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
        logger.info(f"开始处理原始剧本：{file_path.name}")
        processor = create_processor(config, translator)

        # 加载 Excel 数据
        excel_data = load_excel_data(file_path)
        sheet_names = list(excel_data.keys())

        # 判断是否为 Excel 输出格式
        is_excel = is_excel_output(config.engine)
        excel_outputs = {} if is_excel else None

        # 使用 DataFrameProcessor 处理数据
        df_processor = DataFrameProcessor(config)

        # 获取文件基本名（不含扩展名）
        file_basename = file_path.stem

        # 处理每个工作表
        for sheet in sheet_names:
            process_sheet(
                sheet, excel_data[sheet], processor, df_processor,
                file_basename, translator, config, excel_outputs
            )

        # Excel 格式统一输出
        if is_excel and excel_outputs:
            scenario_name = f"{file_basename}_输出脚本.xlsx"
            output_file_path = config.paths.output_dir / scenario_name
            output_excel_file(excel_outputs, output_file_path, config)
        elif is_excel and not excel_outputs:
            logger.warning(f"{file_path.name} 没有任何有效 sheet，未生成 Excel 输出文件。")



    except (ExcelFileNotFoundError, ExcelFormatError, ExcelDataError) as e:
        # 重新抛出给 main 函数处理
        raise
    except Exception as e:
        logger.error(f"处理文件 {file_path} 时出错：{e}", exc_info=True)
        raise ExcelParseError(f"处理文件失败：{file_path}") from e


def process_dialogue_file(
    file_path: Path, 
    config: AppConfig, 
    translator: ParamTranslator,
    text_format: str = "{index}\n{voice}\n{text}"
):
    """
    处理配音台本文件（Excel 或 CSV 格式）
    
    Args:
        file_path: 文件路径
        config: 应用配置
        translator: 参数翻译器
        text_format: Text 列内容格式化模板，支持 {index}、{voice}、{text} 占位符
        
    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 文件格式不正确
    """
    try:
        logger.info(f"开始处理配音台本：{file_path.name}")
        processor = create_processor(config, translator)
        
        # 加载配音台本数据
        dialogue_df = load_dialogue_script(file_path)
        
        # 获取文件基本名
        file_basename = file_path.stem
        
        # 处理配音台本
        output_list = process_dialogue_script(
            dialogue_df, processor, translator, config, file_basename,
            text_format=text_format
        )
        
        # 计算字数统计（使用配音台本的列名）
        word_counter = BasicWordCounter()
        
        # 检查是否有 Name 和 Text 列
        if ColumnName.NAME.value in dialogue_df.columns and ColumnName.TEXT.value in dialogue_df.columns:
            total_words = word_counter.count(dialogue_df[ColumnName.TEXT.value].tolist())
            logger.info(f"配音台本总字数：{total_words}")
            
            # 按说话者统计字数
            name_text_pairs = list(zip(
                dialogue_df[ColumnName.NAME.value],
                dialogue_df[ColumnName.TEXT.value]
            ))
            total_words_by_chara_name = word_counter.count_by(name_text_pairs)
            for chara_name, count in total_words_by_chara_name.items():
                logger.info(f"  说话者 '{chara_name}' 字数：{count}")
        else:
            logger.warning("配音台本缺少 Name 或 Text 列，跳过字数统计")
        
        # 确保输出目录存在
        config.paths.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 判断输出格式并保存
        is_excel = is_excel_output(config.engine)
        
        if is_excel:
            # Excel 格式：单个工作表
            excel_outputs = {"Dialogue": output_list}
            scenario_name = f"{file_basename}_voice_test.xlsx"
            output_file_path = config.paths.output_dir / scenario_name
            output_excel_file(excel_outputs, output_file_path, config)
        else:
            # 其他格式：直接输出
            scenario_name = f"{file_basename}_voice_test{config.engine.file_extension}"
            output_file_path = config.paths.output_dir / scenario_name
            output_sheet_file(output_list, output_file_path, config)
            
    except (FileNotFoundError, ValueError) as e:
        raise
    except Exception as e:
        logger.error(f"处理配音台本 {file_path} 时出错：{e}", exc_info=True)
        raise ValueError(f"处理配音台本失败：{file_path}") from e


def process_dialogue_script(
    dialogue_df: pd.DataFrame,
    processor,
    translator: ParamTranslator,
    config: AppConfig,
    file_basename: str = "dialogue",
    text_format: str = "{text}"
) -> list:
    """
    处理配音台本 DataFrame，生成输出命令列表
    
    Args:
        dialogue_df: 配音台本 DataFrame（包含 Name、Text、Voice、Index 列）
        processor: 处理器实例
        translator: 参数翻译器
        config: 应用配置
        file_basename: 文件基本名（用于日志）
        text_format: Text 列内容格式化模板，支持 {index}、{voice}、{text} 占位符
                    默认："{text}"
                    示例："[{index}][{voice}] {text}"
        
    Returns:
        list: 输出命令列表
    """
    output_list = []
    df_processor = DataFrameProcessor(config)
    
    # 使用进度条处理
    desc = f"处理配音台本 {file_basename}"
    if config.processing.enable_progress_bar:
        iterator = tqdm(range(len(dialogue_df)), desc=desc)
    else:
        iterator = range(len(dialogue_df))
    
    for idx in iterator:
        row_data = dialogue_df.iloc[idx]
        try:
            # 设置翻译器上下文信息
            translator.set_context(
                file_basename,
                sheet_name="Dialogue",  # 配音台本只有一个工作表
                row_index=idx,
                scenario_index=row_data.get(ColumnName.INDEX.value, "")
            )
            
            # 处理 Text 列的格式化
            original_text = row_data.get(ColumnName.TEXT.value, "")
            index_value = row_data.get(ColumnName.INDEX.value, "")
            voice_value = row_data.get(ColumnName.VOICE.value, "")
            
            # 根据格式模板构建新文本
            if text_format != "{text}":
                # 使用模板格式化
                formatted_text = text_format.format(
                    index=str(int(index_value)) if not pd.isna(index_value) else "",
                    voice=voice_value,
                    text=original_text
                )
                # 更新行数据中的 Text 列
                row_data = row_data.copy()  # 避免修改原始数据
                row_data[ColumnName.TEXT.value] = formatted_text
            
            # 直接使用行数据进行处理
            commands = processor.process_row(row_data)
            
            if commands:
                output_list.extend(commands)
        except Exception as e:
            logger.error(f"处理第 {idx} 行时出错：{e}", exc_info=True)
    
    return output_list


def main():
    """主函数"""
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="语音测试脚本生成工具 - 从原始剧本或配音台本生成演出脚本"
    )
    parser.add_argument(
        "--input", type=Path,
        help="输入文件路径（单个文件或目录）。如果是目录，处理其中的所有 Excel 文件"
    )
    parser.add_argument(
        "--dialogue", action="store_true", default=True,
        help="输入为配音台本格式（Excel/CSV），包含 Name、Text、Voice、Index 列"
    )
    parser.add_argument(
        "--output", type=Path,
        help="输出目录（覆盖配置中的 output_dir）"
    )
    parser.add_argument(
        "--text-format", type=str, default="{index}\\n{voice}\\n{text}",
        dest="text_format",
        help="Text 列内容格式化模板，支持 {index}、{voice}、{text} 占位符\n"
             "默认：\"{text}\"\n"
             "示例：\"[{index}][{voice}] {text}\" 或 \"[{voice}] {text}\""
    )

    args = parser.parse_args()
    
    try:
        # 加载配置
        config_path = Path("config.yaml")
        if config_path.exists():
            logger.info(f"从配置文件加载：{config_path}")
            config = AppConfig.from_file(config_path)
        else:
            logger.info("使用默认配置")
            config = AppConfig.create_default("naninovel")
        
        # 覆盖输出目录（如果指定）
        if args.output:
            config.paths.output_dir = args.output
        
        # 确保目录存在
        config.paths.ensure_dirs_exist()
        
        # 确定输入源
        if args.input:
            # 使用命令行指定的输入
            input_path = args.input
            if input_path.is_file():
                input_files = [input_path]
                input_dir = input_path.parent
            elif input_path.is_dir():
                input_dir = input_path
                input_files = [
                    f for f in input_dir.iterdir()
                    if f.suffix in ['.xlsx', '.xls', '.csv'] and not f.name.startswith(TEMP_FILE_PREFIX)
                ]
            else:
                logger.error(f"输入路径不存在：{input_path}")
                return
        else:
            # 使用配置中的输入目录
            input_voice_path = getattr(config.paths, 'input_voice_dir', config.paths.input_dir / 'voice')
            if not input_voice_path.exists():
                logger.error(f"输入路径不存在：{input_voice_path}")
                return
            
            input_dir = input_voice_path
            input_files = [
                f for f in input_voice_path.iterdir()
                if f.suffix in ['.xlsx', '.xls'] and not f.name.startswith(TEMP_FILE_PREFIX)
            ]
        
        if not input_files:
            logger.warning(f"在 {input_dir} 中没有找到文件")
            return
        
        # 根据配置动态导入引擎模块
        import_engine_module(config.engine.engine_type)
        
        # 创建翻译器（用于追踪无法翻译的参数）
        translator = ParamTranslator(
            module_file=str(config.paths.param_config_dir / "param_mappings.py")
        )
        
        logger.info(f"找到 {len(input_files)} 个文件，开始处理...")
        logger.info(f"使用引擎：{config.engine.engine_type}")
        logger.info(f"输入模式：{'配音台本' if args.dialogue else '原始剧本'}")

        # 处理每个文件
        success_count = 0
        error_count = 0
        
        for input_file in input_files:
            try:
                if args.dialogue:
                    # 处理配音台本格式
                    process_dialogue_file(
                        input_file, config, translator,
                        text_format=args.text_format
                    )
                else:
                    # 处理原始剧本格式
                    process_excel_file(input_file, config, translator)
                success_count += 1
            except Exception as e:
                logger.error(f"处理文件失败：{input_file} - {e}")
                error_count += 1
                continue
        
        logger.info(f"处理完成：成功 {success_count} 个，失败 {error_count} 个")
        
        # 导出无法翻译的参数日志
        untranslatable_count = translator.get_untranslatable_count()
        if untranslatable_count > 0:
            logger.info(f"发现 {untranslatable_count} 个无法翻译的参数")
            log_path = translator.export_untranslatable_log(config.paths.output_dir)
            if log_path:
                logger.info(f"无法翻译的参数详细信息已保存至：{log_path}")
        else:
            logger.info("所有参数均成功翻译")
        
    except Exception as e:
        logger.critical(f"程序执行失败：{e}", exc_info=True)
        raise

main()
