"""
宏映射更新工具
从 Excel 宏映射文件生成 Python 宏映射模块
"""
import pandas as pd
from pathlib import Path
from typing import Dict, Any
from core.config_manager import AppConfig
from core.logger import get_logger
from core.excel_management import (
    ExcelFileNotFoundError,
    ExcelFormatError,
    ExcelFileManager
)

logger = get_logger()


class MacroUpdater:
    """宏映射更新器"""

    def __init__(self, config: AppConfig):
        """
        初始化宏更新器

        Args:
            config: 应用配置
        """
        self.config = config
        self.engine_type = config.engine.engine_type
        self.excel_manager = ExcelFileManager(cache_enabled=True)
        
        # Utage标准列（不包括Macro列）
        self.target_columns = [
            "Command", "Arg1", "Arg2", "Arg3", "Arg4", "Arg5", "Arg6",
            "WaitType", "Text", "PageCtrl", "Voice", "WindowType"
        ]

    def read_macro_file(self, macro_file: Path) -> Dict[str, Dict[str, Any]]:
        """
        读取宏映射文件并生成映射

        Args:
            macro_file: 宏映射文件路径

        Returns:
            Dict[str, Dict[str, Any]]: 宏映射字典
            格式: {宏名称: {目标字段: 源参数名或固定值}}
        """
        if not macro_file.exists():
            logger.error(f"宏映射文件不存在: {macro_file}")
            return {}

        try:
            # 读取所有工作表
            sheets = self.excel_manager.load_excel(macro_file)
            logger.info(f"读取到 {len(sheets)} 个工作表")

            mappings = {}

            for sheet_name, df in sheets.items():
                # 跳过模板工作表
                if "模板" in sheet_name:
                    logger.debug(f"跳过模板工作表: {sheet_name}")
                    continue

                # 检查必需的列
                if "Macro" not in df.columns:
                    logger.warning(f"工作表 {sheet_name} 缺少必需的 'Macro' 列，跳过")
                    continue

                # 处理每一行
                for _, row in df.iterrows():
                    macro_name = row.get("Macro")
                    
                    # 跳过空行
                    if pd.isna(macro_name) or not str(macro_name).strip():
                        continue
                    
                    macro_name = str(macro_name).strip()
                    
                    # 构建该宏的映射
                    macro_mapping = {}
                    
                    # 遍历所有目标列
                    for target_col in self.target_columns:
                        if target_col not in df.columns:
                            continue
                        
                        source_value = row.get(target_col)
                        
                        # 如果单元格有值，添加到映射中
                        if pd.notna(source_value):
                            source_str = str(source_value).strip()
                            if source_str:  # 非空字符串
                                macro_mapping[target_col] = source_str
                    
                    # 如果该宏有映射，保存
                    if macro_mapping:
                        if macro_name in mappings:
                            logger.warning(f"宏 '{macro_name}' 重复定义，将覆盖之前的映射")
                        mappings[macro_name] = macro_mapping
                        logger.debug(f"宏 '{macro_name}': {len(macro_mapping)} 个字段映射")

                if mappings:
                    logger.info(f"工作表 {sheet_name}: {len(mappings)} 个宏映射")

            return mappings

        except ExcelFileNotFoundError as e:
            logger.error(f"宏映射文件不存在: {macro_file} - {e}")
            return {}
        except ExcelFormatError as e:
            logger.error(f"宏映射文件格式错误: {macro_file} - {e}")
            return {}
        except Exception as e:
            logger.error(f"读取宏映射文件失败: {e}", exc_info=True)
            return {}

    def generate_mappings_file(
        self, 
        mappings: Dict[str, Dict[str, Any]], 
        output_file: Path
    ):
        """
        生成宏映射 Python 文件

        Args:
            mappings: 宏映射字典
            output_file: 输出文件路径
        """
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("# 自动生成的宏映射文件\n")
                f.write("# 请不要手动编辑此文件\n")
                f.write(f"# 引擎类型: {self.engine_type}\n\n")
                f.write("MACRO_MAPPINGS = ")

                # 使用 pprint 生成格式化的字典
                import pprint
                f.write(pprint.pformat(mappings, width=100, sort_dicts=False))
                f.write("\n")

            logger.info(f"宏映射已保存到: {output_file}")

        except Exception as e:
            logger.error(f"保存宏映射文件失败: {e}", exc_info=True)

    def update_mappings(self) -> bool:
        """更新宏映射"""
        logger.info("=" * 60)
        logger.info(f"开始更新宏映射 (引擎: {self.engine_type})")
        logger.info("=" * 60)

        # 读取宏映射文件
        macro_file = Path(self.config.paths.param_config_dir) / f"macro_data_{self.engine_type}.xlsx"

        if not macro_file.exists():
            logger.error(f"宏映射文件不存在: {macro_file}")
            logger.info(f"请创建宏映射文件: {macro_file}")
            logger.info("表格格式：第一列为 'Macro'，其他列为目标字段（Command, Arg1-Arg6, WaitType等）")
            return False

        try:
            logger.info(f"读取宏映射文件: {macro_file}")
            mappings = self.read_macro_file(macro_file)

            if not mappings:
                logger.error("未能读取到任何宏映射")
                return False

            output_file = self.config.paths.param_config_dir / "macro_mappings.py"
            logger.info(f"生成宏映射文件: {output_file}")
            self.generate_mappings_file(mappings, output_file)

            total_fields = sum(len(m) for m in mappings.values())
            logger.info(f"宏映射: {len(mappings)} 个宏, 共 {total_fields} 个字段映射")
            
            logger.info("=" * 60)
            logger.info(f"宏映射更新完成")
            logger.info("=" * 60)

            return True

        except Exception as e:
            logger.error(f"处理宏映射时失败: {e}")
            return False


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
        updater = MacroUpdater(config)

        # 执行更新
        success = updater.update_mappings()

        if success:
            logger.info("宏映射更新成功")
        else:
            logger.error("宏映射更新失败")

    except KeyboardInterrupt:
        logger.info("用户中断操作")
    except Exception as e:
        logger.critical(f"宏映射更新过程失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

