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
            logger.info(f"读取到 {len(sheets)} 个工作表")

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
                        logger.info(f"工作表 {sheet_name}: {len(sheet_mapping)} 个映射")

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

            logger.info(f"参数映射已保存到: {output_file}")

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

        logger.info(f"找到 {len(excel_files)} 个演出表格文件")
        # 创建 ExcelEditor 实例
        excel_writer = ExcelEditor()
        success_count = 0

        for excel_file in excel_files:
            try:
                logger.info(f"处理文件: {excel_file.name}")

                # 准备参数数据（按照 all_params 的顺序）
                parameter_data = {}
                for param_type in all_params:
                    params = validation_data.get(param_type, [])
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
                        logger.info(f"  成功更新参数表: {excel_file.name}")
                        success_count += 1
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

        logger.info(f"处理完成，成功更新 {success_count}/{len(excel_files)} 个文件")
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
        for excel_file in excel_files:
            logger.info(f"  参数表目标: {excel_file}")
        for param_type in all_params:
            logger.debug(
                f"  参数类型 {param_type}: {len(validation_data.get(param_type, []))} 个值"
            )
        return True

    def update_mappings(
        self,
        scenario_workbooks: Optional[List[Path]] = None,
        generate_mapping_files: bool = True,
        update_parameter_sheets: bool = True,
        dry_run: bool = False,
    ) -> bool:
        """生成映射并/或同步参数表；默认行为保持原完整流程。"""
        logger.info("=" * 60)
        logger.info(f"开始更新参数映射 (引擎: {self.engine_type})")
        if dry_run:
            logger.info("模式: DRY RUN")
        elif generate_mapping_files and not update_parameter_sheets:
            logger.info("模式: 仅生成映射")
        elif update_parameter_sheets and not generate_mapping_files:
            logger.info("模式: 仅同步参数表")
        else:
            logger.info("模式: 完整更新")
        logger.info("=" * 60)

        # 阶段1: 生成基础参数映射
        param_file = Path(self.config.paths.param_config_dir) / f"param_data_{self.engine_type}.xlsx"

        if not param_file.exists():
            logger.error(f"参数文件不存在: {param_file}")
            logger.info(f"请确保参数文件存在")
            return False

        try:
            logger.info(f"读取参数文件: {param_file}")
            mappings = self.read_param_file(param_file)

            if generate_mapping_files and not mappings:
                logger.error("未能读取到任何参数映射")
                return False

            output_file = self.config.paths.param_config_dir / "param_mappings.py"
            if generate_mapping_files:
                action = "将生成" if dry_run else "生成"
                logger.info(f"{action}参数映射文件: {output_file}")
                if not dry_run:
                    self.generate_mappings_file(mappings, output_file)

            total_mappings = sum(len(m) for m in mappings.values())
            logger.info(f"基础参数映射: {len(mappings)} 个工作表, {total_mappings} 个映射")
            
        except Exception as e:
            logger.error(f"处理基础参数映射时失败: {e}")
            return False

        # 阶段2: 生成差分参数映射
        variant_file = Path(self.config.paths.param_config_dir) / "variant_data.xlsx"
        variant_file_path = None  # 明确设置为 None

        if variant_file.exists():
            logger.info(f"读取差分参数文件: {variant_file}")
            try:
                if generate_mapping_files:
                    # 差分参数文件不跳过模板工作表，保持与原项目一致
                    variant_mappings = self.read_param_file(variant_file, skip_template=False)

                    # 生成差分映射文件（保持与原项目一致，包含空映射）
                    variant_output = self.config.paths.param_config_dir / "variant_mappings.py"
                    action = "将生成" if dry_run else "生成"
                    logger.info(f"{action}差分参数映射文件: {variant_output}")
                    if not dry_run:
                        self.generate_mappings_file(variant_mappings, variant_output)

                    # 统计有效映射（排除模板）
                    valid_mappings = {
                        key: value
                        for key, value in variant_mappings.items()
                        if value and "模板" not in key
                    }
                    if valid_mappings:
                        total_variant = sum(len(mapping) for mapping in valid_mappings.values())
                        logger.info(
                            f"差分参数映射: {len(valid_mappings)} 个角色, {total_variant} 个映射"
                        )
                    else:
                        logger.info("差分参数文件中没有有效的角色映射")
                    
                # 将文件路径赋值给变量
                variant_file_path = variant_file
                    
            except Exception as e:
                logger.error(f"处理差分参数映射时失败: {e}")
                # 继续执行，不因为差分参数失败而停止整个流程
        else:
            logger.info("差分参数文件不存在，跳过")

        if update_parameter_sheets:
            # 阶段3: 更新演出表格的参数表
            logger.info("=" * 60)
            logger.info("更新演出表格参数表")
            logger.info("=" * 60)

            try:
                validation_data = self.collect_validation_data(param_file, variant_file_path)
                if validation_data:
                    logger.info(f"收集到 {len(validation_data)} 个参数类型的验证数据")
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
                else:
                    logger.warning("未能收集到验证数据，跳过演出表格更新")
            except Exception as e:
                logger.error(f"更新演出表格参数表时失败: {e}")
                # 不返回False，因为参数映射文件可能已经生成成功

        logger.info("=" * 60)
        logger.info(f"参数映射更新完成")
        logger.info("=" * 60)

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
            logger.info("参数映射更新成功")
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
