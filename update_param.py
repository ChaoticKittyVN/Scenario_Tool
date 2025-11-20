"""
参数映射更新工具
从 Excel 参数文件生成 Python 参数映射模块
"""
import pandas as pd
from pathlib import Path
from typing import Dict
from core.config_manager import AppConfig
from core.logger import get_logger

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
            # 读取所有工作表
            sheets = pd.read_excel(param_file, sheet_name=None)
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
            logger.info(f"\n读取差分参数文件: {varient_file}")
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
            logger.info("差分参数文件不存在，跳过")

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
