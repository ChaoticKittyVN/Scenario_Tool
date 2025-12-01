"""
参数映射更新工具
从 Excel 参数文件生成 Python 参数映射模块
"""
import pandas as pd
from pathlib import Path
from typing import Dict, List
from openpyxl import load_workbook
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from core.sentence_generator_manager import SentenceGeneratorManager
from core.config_manager import AppConfig
from core.logger import get_logger
from core.excel_reader import ExcelFileManager, DataFrameProcessor

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
            variable_name = "VARIENT_MAPPINGS" if "varient" in output_file.name else "PARAM_MAPPINGS"

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

    def collect_validation_data(self, param_file: Path, varient_file: Path = None) -> Dict[str, List[str]]:
        """
        收集所有验证数据（基础参数 + 差分参数）

        Args:
            param_file: 基础参数文件路径
            varient_file: 差分参数文件路径（可选）

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

        except Exception as e:
            logger.error(f"读取基础参数文件失败: {e}", exc_info=True)
            return {}

        # 2. 收集差分参数
        if varient_file and varient_file.exists():
            try:
                varient_sheets = self.excel_manager.load_excel(varient_file)

                # 收集所有差分参数名
                all_varient_params = set()
                for sheet_name, df in varient_sheets.items():
                    if "ExcelParam" not in df.columns:
                        continue

                    for _, row in df.iterrows():
                        excel_param = row["ExcelParam"]
                        if pd.notna(excel_param):
                            param_str = str(excel_param).strip()
                            if param_str:
                                all_varient_params.add(param_str)

                # 将差分参数合并到 Varient 列
                if all_varient_params:
                    if "Varient" in validation_data:
                        # 合并去重
                        existing_varients = set(validation_data["Varient"])
                        combined_varients = existing_varients.union(all_varient_params)
                        validation_data["Varient"] = sorted(list(combined_varients))
                    else:
                        validation_data["Varient"] = sorted(list(all_varient_params))

                    logger.debug(f"收集差分参数: {len(all_varient_params)} 个值")

            except Exception as e:
                logger.warning(f"读取差分参数文件失败: {e}")

        return validation_data

    def get_all_validate_params(self) -> Dict[str, List[str]]:
        """
        获取所有句子生成器的参数翻译类型
        
        Returns:
            Dict[str, Dict[str, list[str]]]: 去重后的数据验证参数类型列表
        """
        try:
            # 创建管理器实例
            manager = SentenceGeneratorManager(self.engine_type)
            # 调用我们之前写的方法
            return manager.get_validate_params()
        except Exception as e:
            logger.error(f"获取数据验证参数类型时发生错误: {e}")
            return {}

    def update_scenario_param_sheets(self, validation_data: Dict[str, List[str]]) -> bool:
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

        # 获取 input 目录
        input_dir = Path(self.config.paths.input_dir)
        if not input_dir.exists():
            logger.error(f"输入目录不存在: {input_dir}")
            return False

        # 查找所有 Excel 文件
        excel_files = list(input_dir.glob("*.xlsx"))
        excel_files = [f for f in excel_files if not f.name.startswith("~")]

        if not excel_files:
            logger.warning(f"在 {input_dir} 中没有找到 Excel 文件")
            return True

        logger.info(f"找到 {len(excel_files)} 个演出表格文件")

        success_count = 0
        for excel_file in excel_files:
            try:
                logger.info(f"处理文件: {excel_file.name}")

                # 加载工作簿
                wb = load_workbook(excel_file)

                # 检查是否存在"参数表"工作表
                if "参数表" not in wb.sheetnames:
                    logger.info(f"  创建新的'参数表'工作表")
                    validation_ws = wb.create_sheet("参数表")
                    # logger.warning(f"  {excel_file.name} 中没有'参数表'工作表，跳过")
                    # wb.close()
                    # continue
                else:
                    validation_ws = wb["参数表"]

                # 创建居中对齐样式
                center_alignment = Alignment(horizontal='center', vertical='center')

                # # 获取当前参数表的列顺序
                # current_headers = []
                # for col_idx in range(1, validation_ws.max_column + 1):
                #     header = validation_ws.cell(row=1, column=col_idx).value
                #     if header:
                #         current_headers.append(header)

                # logger.info(f"  当前参数表列: {current_headers}")

                # 跟踪是否有任何更新
                has_updates = False

                # 按照当前列顺序更新参数表
                for col_idx, param_type in enumerate(all_params, 1):
                    # 获取这个参数的数据
                    params = validation_data.get(param_type, [])

                    
                    # 检查表头是否匹配
                    current_header = validation_ws.cell(row=1, column=col_idx).value
                    needs_update = False

                    if current_header != param_type:
                        needs_update = True
                        logger.info(f" 表头不匹配: 当前'{current_header}'，期望'{param_type}'")
                    else: 
                        # 检查参数内容是否匹配
                        current_params = []
                        read_row = 2
                        while read_row <= validation_ws.max_row:
                            cell_value = validation_ws.cell(row=read_row, column=col_idx).value
                            if cell_value is None:
                                break
                            current_params.append(str(cell_value))
                            read_row += 1

                        # 如果参数数量或内容有变化，需要更新
                        if current_params != [str(p) for p in params]:
                            needs_update = True
                            logger.info(f" 更新 {param_type}: 当前 {len(current_params)} 个，新 {len(params)} 个")
                    # 如果需要更新，重新写入这一列
                    if needs_update: 
                            
                        has_updates = True

                        # 清除这一列的内容（从第1行开始）
                        for clear_row in range(1, validation_ws.max_row + 1):
                            validation_ws.cell(row=clear_row, column=col_idx).value = None

                        # 写入表头
                        header_cell = validation_ws.cell(row=1, column=col_idx, value=param_type)
                        header_cell.alignment = center_alignment

                        # 写入参数数据
                        for write_row, param_value in enumerate(params, 2):
                            cell = validation_ws.cell(row=write_row, column=col_idx, value=param_value)
                            cell.alignment = center_alignment

                        logger.info(f" 更新 {param_type} 参数 写入 {len(params)} 个参数")
                    else:
                        logger.debug(f" {param_type} 列无需更新")

                    # 创建或更新命名区域
                    range_name = f"{param_type}List"
                    col_letter = get_column_letter(col_idx)
                    expected_dynamic_range = f"OFFSET(参数表!${col_letter}$2,0,0,COUNTA(参数表!${col_letter}:${col_letter})-1,1)"

                    # 检查命名区域是否需要更新
                    needs_update_range = True
                    if range_name in wb.defined_names:
                        existing_named_range = wb.defined_names[range_name]
                        existing_range = existing_named_range.attr_text

                        # 如果现有区域已经是正确的动态公式，则跳过
                        if existing_range == expected_dynamic_range:
                            needs_update_range = False

                    # 创建或更新命名区域
                    if needs_update_range:
                        try:
                            # 删除已存在的区域（如果存在）
                            if range_name in wb.defined_names:
                                del wb.defined_names[range_name]

                            # 创建新的命名区域
                            wb.defined_names[range_name] = DefinedName(
                                name=range_name,
                                attr_text=expected_dynamic_range
                            )
                            logger.debug(f"  创建命名区域: {range_name}")
                            has_updates = True

                        except Exception as e:
                            logger.warning(f"  处理命名区域 {range_name} 时发生错误: {e}")

                # 清理多余的列（如果参数翻译类型列表比当前列少）
                current_column_count = validation_ws.max_column
                if current_column_count > len(all_params):
                    logger.info(f"  清理多余的列: 当前{current_column_count}列，期望{len(all_params)}列")
                    has_updates = True
                    # 删除多余的列
                    for col_idx in range(len(all_params) + 1, current_column_count + 1):
                        for row_idx in range(1, validation_ws.max_row + 1):
                            validation_ws.cell(row=row_idx, column=col_idx).value = None


                # 保存工作簿（仅当有更新时）
                if has_updates:
                    try:
                        wb.save(excel_file)
                        logger.info(f"  成功保存文件: {excel_file.name}")
                        success_count += 1
                    except Exception as e:
                        logger.error(f"  保存失败: {e}")
                    finally:
                        wb.close()
                else:
                    logger.info(f"  {excel_file.name} 无需更新")
                    wb.close()

            except Exception as e:
                logger.error(f"  处理文件 {excel_file.name} 时发生错误: {e}", exc_info=True)

        logger.info(f"处理完成，成功更新 {success_count}/{len(excel_files)} 个文件")
        return success_count > 0

    def update_mappings(self):
        """更新参数映射"""
        logger.info("=" * 60)
        logger.info(f"开始更新参数映射 (引擎: {self.engine_type})")
        logger.info("=" * 60)

        # 阶段1: 生成基础参数映射
        param_file = Path(self.config.paths.param_config_dir) / f"param_data_{self.engine_type}.xlsx"

        if not param_file.exists():
            logger.error(f"参数文件不存在: {param_file}")
            logger.info(f"请确保参数文件存在")
            return False

        logger.info(f"读取参数文件: {param_file}")
        mappings = self.read_param_file(param_file)

        if not mappings:
            logger.error("未能读取到任何参数映射")
            return False

        output_file = self.config.paths.param_config_dir / "param_mappings.py"
        logger.info(f"生成参数映射文件: {output_file}")
        self.generate_mappings_file(mappings, output_file)

        total_mappings = sum(len(m) for m in mappings.values())
        logger.info(f"基础参数映射: {len(mappings)} 个工作表, {total_mappings} 个映射")

        # 阶段2: 生成差分参数映射
        varient_file = Path(self.config.paths.param_config_dir) / "varient_data.xlsx"

        if varient_file.exists():
            logger.info(f"读取差分参数文件: {varient_file}")
            # 差分参数文件不跳过模板工作表，保持与原项目一致
            varient_mappings = self.read_param_file(varient_file, skip_template=False)

            # 生成差分映射文件（保持与原项目一致，包含空映射）
            varient_output = self.config.paths.param_config_dir / "varient_mappings.py"
            logger.info(f"生成差分参数映射文件: {varient_output}")
            self.generate_mappings_file(varient_mappings, varient_output)

            # 统计有效映射（排除模板）
            valid_mappings = {k: v for k, v in varient_mappings.items() if v and "模板" not in k}
            if valid_mappings:
                total_varient = sum(len(m) for m in valid_mappings.values())
                logger.info(f"差分参数映射: {len(valid_mappings)} 个角色, {total_varient} 个映射")
            else:
                logger.info("差分参数文件中没有有效的角色映射")
        else:
            varient_file = None
            logger.info("差分参数文件不存在，跳过")

        # 阶段3: 更新演出表格的参数表
        logger.info("=" * 60)
        logger.info("更新演出表格参数表")
        logger.info("=" * 60)

        validation_data = self.collect_validation_data(param_file, varient_file)
        if validation_data:
            logger.info(f"收集到 {len(validation_data)} 个参数类型的验证数据")
            self.update_scenario_param_sheets(validation_data)
        else:
            logger.warning("未能收集到验证数据，跳过演出表格更新")

        logger.info("=" * 60)
        logger.info(f"参数映射更新完成")
        logger.info("=" * 60)

        return True


def main():
    """主函数"""
    try:
        # 加载配置
        config_path = Path("config.yaml")
        if not config_path.exists():
            logger.error("配置文件不存在: config.yaml")
            return

        config = AppConfig.from_file(config_path)

        # 创建更新器
        updater = ParamUpdater(config)

        # 执行更新
        success = updater.update_mappings()

        if success:
            logger.info("参数映射更新成功")
        else:
            logger.error("参数映射更新失败")

    except Exception as e:
        logger.critical(f"参数更新过程失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
