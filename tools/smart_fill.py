"""
智能参数填充工具
根据 YAML 配置自动填充 Excel 表格中的参数

使用方法:
    py run_tool.py fill [--config CONFIG] [--input-dir DIR] [--sheets SHEETS]

示例:
    py run_tool.py fill                                    # 使用默认配置
    py run_tool.py fill --config my_rules.yaml            # 指定配置文件
    py run_tool.py fill --sheets 对话，剧本               # 只处理指定工作表
"""
import argparse
import sys
from pathlib import Path
from core.logger import get_logger
from core.config_manager import AppConfig
from core.param_filler import SmartParameterFiller

logger = get_logger()


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='智能参数填充工具 - 根据配置自动填充 Excel 表格参数',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                              使用默认配置处理所有文件
  %(prog)s --config my_rules.yaml       使用自定义配置文件
  %(prog)s --sheets 对话，剧本          只处理指定的工作表
  %(prog)s --input-dir ./custom_input   指定输入目录
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        type=Path,
        default=Path('config/filling_rules.yaml'),
        help='YAML 配置文件路径 (默认：config/filling_rules.yaml)'
    )
    
    parser.add_argument(
        '--input-dir', '-i',
        type=Path,
        default=None,
        help='输入目录 (默认：config.yaml 中定义的 input_dir)'
    )
    
    parser.add_argument(
        '--sheets', '-s',
        type=str,
        default=None,
        help='要处理的工作表名称，多个用逗号分隔 (默认：所有工作表)'
    )
    
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='只预览不执行（仅显示将要进行的修改）'
    )
    
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()
    
    try:
        logger.info("=" * 60)
        logger.info("智能参数填充工具")
        logger.info("=" * 60)
        
        # 加载应用配置
        config_path = Path("config.yaml")
        if config_path.exists():
            config = AppConfig.from_file(config_path)
            logger.info(f"从 {config_path} 加载配置")
        else:
            logger.warning("config.yaml 不存在，使用默认配置")
            config = AppConfig.create_default("naninovel")
        
        # 确定输入目录
        input_dir = args.input_dir or config.paths.input_dir
        if not input_dir.exists():
            logger.error(f"输入目录不存在：{input_dir}")
            return False
        
        logger.info(f"输入目录：{input_dir}")
        
        # 解析工作表列表
        sheet_names = None
        if args.sheets:
            sheet_names = [s.strip() for s in args.sheets.split(',')]
            logger.info(f"指定工作表：{sheet_names}")
        
        # 检查配置文件
        if not args.config.exists():
            logger.warning(f"配置文件不存在：{args.config}")
            logger.info("将使用内置的默认规则")
            filler_config_path = None
        else:
            filler_config_path = args.config
            logger.info(f"配置文件：{filler_config_path}")
        
        # 创建智能填写器
        filler = SmartParameterFiller(filler_config_path)
        
        # 验证规则
        if filler.rule_engine.rules:
            valid = filler.rule_engine.validate_rules()
            if not valid:
                logger.warning("部分规则无效，请检查配置文件")
            
            logger.info(f"加载了 {len(filler.rule_engine.rules)} 条填充规则")
            for i, rule in enumerate(filler.rule_engine.rules, 1):
                logger.info(f"  {i}. {rule.name} -> {rule.strategy_name}")
        
        # 发现文件
        files = filler.discover_files(input_dir)
        if not files:
            logger.warning(f"在 {input_dir} 中没有找到 Excel 文件")
            return False
        
        logger.info(f"找到 {len(files)} 个 Excel 文件")
        
        # 干运行模式
        if args.dry_run:
            logger.info("\n=== 干运行模式（不会实际修改文件）===")
            for file_path in files:
                sheets = filler.discover_sheets(file_path)
                logger.info(f"\n文件：{file_path.name}")
                for sheet in sheets:
                    if sheet_names and sheet not in sheet_names:
                        continue
                    
                    df = filler.excel_manager.get_sheet(file_path, sheet)
                    params = filler.extract_parameters(df, sheet)
                    
                    if params:
                        logger.info(f"  工作表：{sheet}")
                        for column, cells in params.items():
                            logger.info(f"    列 {column}: {len(cells)} 个单元格需要填充")
            return True
        
        # 执行填充
        logger.info("\n开始处理文件...")
        results = filler.process_directory(input_dir, sheet_names)
        
        # 统计结果
        success_count = sum(1 for v in results.values() if v)
        total_count = len(results)
        
        logger.info("\n" + "=" * 60)
        logger.info("处理结果统计")
        logger.info("=" * 60)
        logger.info(f"总文件数：{total_count}")
        logger.info(f"成功：{success_count}")
        logger.info(f"失败：{total_count - success_count}")
        
        if success_count < total_count:
            logger.warning("\n以下文件处理失败:")
            for file_path, success in results.items():
                if not success:
                    logger.warning(f"  - {file_path.name}")
        
        logger.info("\n处理完成!")
        return success_count > 0
        
    except KeyboardInterrupt:
        logger.warning("\n用户中断操作")
        return False
    except Exception as e:
        logger.critical(f"程序执行失败：{e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
