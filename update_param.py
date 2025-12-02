"""
参数映射更新工具
从 Excel 参数文件生成 Python 参数映射模块
"""
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
from openpyxl import load_workbook
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from core.sentence_generator_manager import SentenceGeneratorManager
from core.config_manager import AppConfig
from core.logger import get_logger
from core.excel_management import (
    ExcelManagerError,
    ExcelFileNotFoundError,
    ExcelFormatError,
    ExcelDataError,
    ExcelWriteError,
    ExcelFileManager,
    DataFrameProcessor,
    ExcelWriter
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

    def collect_validation_data(
        self, 
        param_file: Path, 
        varient_file: Optional[Path] = None  # 修改类型注解
    ) -> Dict[str, List[str]]:
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

        except (ExcelFileNotFoundError, ExcelFormatError) as e:
            logger.error(f"读取基础参数文件失败: {param_file} - {e}")
            return {}
        except Exception as e:
            logger.error(f"读取基础参数文件时发生未知错误: {e}", exc_info=True)
            return {}

        # 2. 收集差分参数
        if varient_file is not None and varient_file.exists():
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

            except (ExcelFileNotFoundError, ExcelFormatError) as e:
                logger.warning(f"读取差分参数文件失败: {varient_file} - {e}")
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
        # 创建 ExcelWriter 实例
        excel_writer = ExcelWriter()
        success_count = 0

        for excel_file in excel_files:
            try:
                logger.info(f"处理文件: {excel_file.name}")

                # 准备参数数据（按照 all_params 的顺序）
                parameter_data = {}
                for param_type in all_params:
                    params = validation_data.get(param_type, [])
                    parameter_data[param_type] = params

                # 使用增强的 ExcelWriter 方法更新参数表
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

    def update_mappings(self) -> bool:
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

        try:
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
            
        except Exception as e:
            logger.error(f"处理基础参数映射时失败: {e}")
            return False

        # 阶段2: 生成差分参数映射
        varient_file = Path(self.config.paths.param_config_dir) / "varient_data.xlsx"
        varient_file_path = None  # 明确设置为 None

        if varient_file.exists():
            logger.info(f"读取差分参数文件: {varient_file}")
            try:
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
                    
                # 将文件路径赋值给变量
                varient_file_path = varient_file
                    
            except Exception as e:
                logger.error(f"处理差分参数映射时失败: {e}")
                # 继续执行，不因为差分参数失败而停止整个流程
        else:
            logger.info("差分参数文件不存在，跳过")

        # 阶段3: 更新演出表格的参数表
        logger.info("=" * 60)
        logger.info("更新演出表格参数表")
        logger.info("=" * 60)

        try:
            validation_data = self.collect_validation_data(param_file, varient_file_path)
            if validation_data:
                logger.info(f"收集到 {len(validation_data)} 个参数类型的验证数据")
                success = self.update_scenario_param_sheets(validation_data)
                if not success:
                    logger.warning("更新演出表格参数表时出现错误，但主流程继续")
            else:
                logger.warning("未能收集到验证数据，跳过演出表格更新")
        except Exception as e:
            logger.error(f"更新演出表格参数表时失败: {e}")
            # 不返回False，因为参数映射文件已经生成成功

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

    except KeyboardInterrupt:
        logger.info("用户中断操作")
    except Exception as e:
        logger.critical(f"参数更新过程失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()