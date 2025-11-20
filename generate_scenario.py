"""
场景脚本生成主程序
从 Excel 文件生成视觉小说引擎脚本
"""
import pandas as pd
import os
from pathlib import Path
from tqdm import tqdm
from core.config_manager import AppConfig
from core.param_translator import ParamTranslator
from core.engine_registry import EngineRegistry
from core.logger import get_logger
from core.exceptions import ExcelParseError, GeneratorError
from core.constants import SheetName, ColumnName, Marker, TEMP_FILE_PREFIX

# 导入引擎模块以触发注册
import engines.renpy
import engines.naninovel

logger = get_logger()


def create_processor(config: AppConfig):
    """
    创建处理器实例

    Args:
        config: 应用配置

    Returns:
        处理器实例
    """
    # 创建翻译器
    translator = ParamTranslator(
        module_file=str(config.paths.param_config_dir / "param_mappings.py"),
        varient_module_file=str(config.paths.param_config_dir / "varient_mappings.py")
    )

    # 从注册表获取引擎元数据
    engine_meta = EngineRegistry.get(config.engine.engine_type)

    # 使用工厂函数创建处理器
    processor = engine_meta.processor_factory(config.engine, translator)

    return processor


def process_excel_file(file_path: Path, config: AppConfig):
    """
    处理单个Excel文件

    Args:
        file_path: Excel 文件路径
        config: 应用配置
    """
    try:
        logger.info(f"开始处理文件: {file_path.name}")
        processor = create_processor(config)

        # 读取Excel文件
        excel_data = pd.read_excel(file_path, sheet_name=None, dtype=str)
        sheet_names = list(excel_data.keys())

        # 获取文件基本名（不含扩展名）
        file_basename = file_path.stem

        # 处理每个工作表
        for sheet in sheet_names:
            # 跳过参数表
            if sheet == SheetName.PARAM_SHEET.value:
                logger.debug(f"跳过参数表: {sheet}")
                continue

            # 生成输出文件名
            scenario_name = config.engine.get_output_filename(sheet)

            # 检查结束标记
            if (ColumnName.NOTE.value not in excel_data[sheet].columns or
                    Marker.END.value not in excel_data[sheet][ColumnName.NOTE.value].tolist()):
                logger.warning(f"工作表 {sheet} 不包含Note列或END标记，跳过")
                continue

            # 找到 END 标记的位置
            end_index = excel_data[sheet][ColumnName.NOTE.value].tolist().index(Marker.END.value)

            # 提取需要处理的行
            valid_indices = []
            for j in range(end_index):
                # 检查是否需要忽略
                if config.processing.ignore_mode:
                    ignore_value = excel_data[sheet].iloc[j].get(ColumnName.IGNORE.value)
                    if ignore_value in config.processing.ignore_words:
                        logger.debug(f"忽略行 {j}: {ignore_value}")
                        continue
                valid_indices.append(j)

            # 获取有效行数据
            if not valid_indices:
                logger.warning(f"工作表 {sheet} 没有有效数据")
                continue

            valid_rows_df = excel_data[sheet].loc[valid_indices]
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
                    commands = processor.process_row(row_data)
                    if commands:
                        output_list.extend(commands)
                except Exception as e:
                    logger.error(f"处理第 {idx} 行时出错: {e}", exc_info=True)

            # 确保输出目录存在
            config.paths.output_dir.mkdir(parents=True, exist_ok=True)

            # 写入输出文件
            output_file_path = config.paths.output_dir / scenario_name
            write_output_file(output_file_path, output_list, config)

            logger.info(f"已生成: {output_file_path}")

    except Exception as e:
        logger.error(f"处理文件 {file_path} 时出错: {e}", exc_info=True)
        raise ExcelParseError(f"处理文件失败: {file_path}") from e


def write_output_file(output_path: Path, lines: list, config: AppConfig):
    """
    写入输出文件

    Args:
        output_path: 输出文件路径
        lines: 输出行列表
        config: 应用配置
    """
    with open(output_path, "w", encoding="utf-8") as f:
        for line in lines:
            # Ren'Py 特定的缩进处理
            if config.engine.engine_type == "renpy":
                if line.strip().startswith("label "):
                    f.write(line.strip() + "\n")
                else:
                    indent = " " * config.engine.indent_size
                    f.write(indent + line + "\n")
            else:
                # 其他引擎的默认处理
                f.write(line + "\n")


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

        # 处理每个Excel文件
        for excel_file in excel_files:
            process_excel_file(excel_file, config)

        logger.info("所有文件处理完成")

    except Exception as e:
        logger.critical(f"程序执行失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
