"""
改动同步工具
从改动表格中读取修改信息并同步到演出表格
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from core.logger import get_logger
from core.param_filler.scenario_param_filler import BaseParamTool, ChangeRecord
from core.param_filler.filling_strategy import ChangeSyncStrategy
from core.excel_management.excel_editor import CellUpdate

logger = get_logger()


class ChangeSyncTool(BaseParamTool):
    """
    改动同步工具
    
    从改动表格 (Excel/CSV) 中读取修改信息，自动同步到对应的演出表格中。
    
    改动表格格式:
    - 定位列：ExcelFilename, SheetName, Idx, Index, Text (5 列用于定位行)
    - 数据列：其他所有列，与演出表格表头一致 (需要修改的数据)
    """
    
    def __init__(self, changes_file: Optional[Path] = None,
                 locator_columns: Optional[List[str]] = None,
                 data_columns: Optional[List[str]] = None,
                 dry_run: bool = True):
        """
        初始化改动同步工具
        
        Args:
            changes_file: 改动表格文件路径 (Excel 或 CSV，默认在 input/sync/目录下)
            locator_columns: 定位列列表 (默认使用策略的 DEFAULT_LOCATOR_COLUMNS)
            data_columns: 数据列列表 (默认自动识别：除定位列外的所有列)
            dry_run: 是否干跑模式（默认 True）。干跑模式下不会实际修改文件。
        """
        # 调用父类初始化 (注册 ChangeSyncStrategy 策略)
        super().__init__(ChangeSyncStrategy, "change_sync", dry_run=dry_run)
        
        self.changes_file = changes_file
        self.changes_df: Optional[pd.DataFrame] = None
        self.locator_columns = locator_columns
        self.data_columns = data_columns
        
        logger.debug(f"ChangeSyncTool 初始化完成，dry_run={dry_run}")
    
    def load_changes_file(self, file_path: Path) -> pd.DataFrame:
        """
        加载改动表格文件
        
        Args:
            file_path: 文件路径 (Excel 或 CSV)
            
        Returns:
            pd.DataFrame: 改动数据
        """
        # 如果没有指定扩展名，自动补全为 .xlsx
        if not file_path.suffix.lower() in ['.xlsx', '.xls', '.csv']:
            file_path = file_path.with_suffix('.xlsx')
        
        # 如果是相对路径，默认在 input/sync/目录下
        if not file_path.is_absolute():
            default_dir = Path('input/sync')
            if not file_path.parent.name in ['sync', 'input']:
                file_path = default_dir / file_path
        
        if not file_path.exists():
            raise FileNotFoundError(f"改动表格文件不存在：{file_path}")
        
        logger.info(f"加载改动表格：{file_path.name}")
        
        # 根据文件后缀选择读取方式
        if file_path.suffix.lower() in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        elif file_path.suffix.lower() == '.csv':
            df = pd.read_csv(file_path, encoding='utf-8')
        else:
            raise ValueError(f"不支持的文件格式：{file_path.suffix}")
        
        # 验证必需的定位列
        required_locators = ['ExcelFilename', 'SheetName', 'Index']
        missing_columns = [col for col in required_locators 
                          if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"改动表格缺少必需列：{missing_columns}")
        
        logger.info(f"改动表格加载完成，共 {len(df)} 条记录")
        return df

    def load_changes_files(self, sync_dir: Path) -> pd.DataFrame:
        """
        加载同步目录下所有的改动表格文件
        
        Args:
            sync_dir: 改动表格目录
            
        Returns:
            pd.DataFrame: 合并后的改动数据
        """
        if not sync_dir.exists():
            raise FileNotFoundError(f"改动表格目录不存在：{sync_dir}")
        
        # 发现所有 Excel 文件
        excel_files = [
            f for f in sync_dir.iterdir()
            if f.suffix.lower() in ['.xlsx', '.xls'] and not f.name.startswith('~')
        ]
        
        if not excel_files:
            raise ValueError(f"改动表格目录中没有 Excel 文件：{sync_dir}")
        
        logger.info(f"发现 {len(excel_files)} 个改动表格文件")
        
        # 读取并合并所有文件
        all_dfs = []
        for file_path in sorted(excel_files):
            try:
                df = pd.read_excel(file_path)
                
                # 验证必需的定位列
                required_locators = ['ExcelFilename', 'SheetName', 'Index']
                missing_columns = [col for col in required_locators 
                                  if col not in df.columns]
                
                if missing_columns:
                    logger.warning(f"文件 {file_path.name} 缺少必需列：{missing_columns}，跳过")
                    continue
                
                # 添加来源文件标记
                df['_source_file'] = file_path.name
                all_dfs.append(df)
                
                logger.debug(f"加载文件：{file_path.name} ({len(df)} 条记录)")
                
            except Exception as e:
                logger.warning(f"加载文件 {file_path.name} 失败：{e}")
        
        if not all_dfs:
            raise ValueError("没有成功加载任何改动表格文件")
        
        # 合并所有 DataFrame
        merged_df = pd.concat(all_dfs, ignore_index=True)
        
        logger.info(f"成功加载 {len(merged_df)} 条改动记录（来自 {len(all_dfs)} 个文件）")
        return merged_df
    
    def process_directory(self, input_dir: Path, dry_run: bool = True, 
                         changes_file: Optional[Path] = None,
                         locator_columns: Optional[List[str]] = None,
                         data_columns: Optional[List[str]] = None) -> Dict[Path, bool]:
        """
        处理整个目录 (重写父类方法以支持改动同步)
        
        Args:
            input_dir: 演出表格目录
            dry_run: 是否干跑模式
            changes_file: 改动表格文件路径 (可选，如果为 None 则自动读取 input/sync/下所有文件)
            locator_columns: 定位列列表 (可选)
            data_columns: 数据列列表 (可选)
             
        Returns:
            Dict[Path, bool]: {文件路径：是否成功}
        """
        # 确定使用哪个改动文件/目录
        if changes_file:
            # 指定了单个文件
            changes_file_to_use = changes_file
            if not changes_file_to_use.is_absolute():
                default_dir = Path('input/sync')
                if not changes_file_to_use.parent.name in ['sync', 'input']:
                    changes_file_to_use = default_dir / changes_file_to_use
            
            try:
                self.changes_df = self.load_changes_file(changes_file_to_use)
            except Exception as e:
                logger.error(f"加载改动表格失败：{e}", exc_info=True)
                print(f"\n❌ 错误：加载改动表格失败 - {e}")
                return {}
        else:
            # 未指定时，自动读取 input/sync/目录下所有文件
            default_sync_dir = Path('input/sync')
            
            if not default_sync_dir.exists():
                logger.error(f"改动表格目录不存在：{default_sync_dir}")
                print(f"\n❌ 错误：改动表格目录不存在 - {default_sync_dir}")
                print("   请创建该目录并添加改动表格文件，或通过 --changes 参数指定文件")
                return {}
            
            try:
                self.changes_df = self.load_changes_files(default_sync_dir)
            except Exception as e:
                logger.error(f"加载改动表格失败：{e}", exc_info=True)
                print(f"\n❌ 错误：加载改动表格失败 - {e}")
                return {}
        
        # 更新策略的 DataFrame 和列配置
        strategy: Optional[ChangeSyncStrategy] = self.filler.strategy_manager.get("change_sync")  # type: ignore
        if strategy:
            locators_to_use = locator_columns or self.locator_columns
            data_cols_to_use = data_columns or self.data_columns
            
            logger.info(f"设置改动表格：locator_columns={locators_to_use}, data_columns={data_cols_to_use}")
            
            strategy.set_changes_df(
                self.changes_df,
                locator_columns=locators_to_use,
                data_columns=data_cols_to_use
            )
            
            logger.info(f"策略已配置：data_columns={strategy.data_columns}")
        
        # 调用父类方法处理目录
        return super().process_directory(input_dir, dry_run)
    
    def process_dataframe(self, df: pd.DataFrame, sheet_name: str, file_path: Path):
        """
        处理单个 DataFrame
        
        Args:
            df: DataFrame
            sheet_name: 工作表名称
            file_path: 文件路径
        """
        if self.changes_df is None:
            logger.warning("改动表格未加载，跳过")
            return
        
        # 检查该工作表是否有改动记录
        # 使用 file_path.stem 去掉扩展名，与改动表格中的 ExcelFilename 匹配
        filename = file_path.stem
        sheet_changes = self.changes_df[
            (self.changes_df['SheetName'] == sheet_name) &
            (self.changes_df['ExcelFilename'] == filename)
        ]
        
        if sheet_changes.empty:
            logger.debug(f"工作表 {sheet_name} 没有改动记录，跳过")
            return
        
        logger.debug(f"工作表 {sheet_name} 有 {len(sheet_changes)} 条改动记录")
        
        # 获取策略对象
        strategy: Optional[ChangeSyncStrategy] = self.filler.strategy_manager.get("change_sync")  # type: ignore
        if not strategy:
            logger.error("策略未找到")
            return
        
        # 构建改动索引缓存：{行索引：改动记录}
        row_changes_cache: Dict[int, Dict[str, Any]] = {}
        
        for _, record in sheet_changes.iterrows():
            # 优先使用 Idx 匹配（真正的行号）
            idx_val = record.get('Idx')
            if pd.notna(idx_val):
                excel_row = int(idx_val)
                df_row = excel_row - 2  # DataFrame 行索引 = Excel 行号 - 2
                if 0 <= df_row < len(df):
                    row_changes_cache[df_row] = record.to_dict()  # type: ignore
                    continue
            
            # 其次使用 Index 列匹配（普通数据列，通过值来定位行）
            index_val = record.get('Index')
            if pd.notna(index_val):
                # 在 DataFrame 的 Index 列中查找匹配的值
                if 'Index' in df.columns:
                    matching_rows = df[df['Index'] == index_val]
                    if not matching_rows.empty:
                        df_row = matching_rows.index[0]
                        if df_row not in row_changes_cache:
                            row_changes_cache[df_row] = record.to_dict()  # type: ignore
                            logger.debug(f"通过 Index 列匹配到行 {df_row}: '{index_val}'")
                        continue
            
            # 最后使用 Text 列匹配行内容来定位
            text_val = record.get('Text')
            if pd.notna(text_val) and str(text_val).strip():
                # 在 DataFrame 中查找包含该文本的行
                for df_idx, row in df.iterrows():
                    # 在所有文本列中搜索匹配的文本
                    for col in ['台词', '对话', 'text', 'dialogue', '备注']:
                        if col in row and pd.notna(row[col]) and str(row[col]).strip() == str(text_val).strip():
                            if df_idx not in row_changes_cache:
                                row_changes_cache[df_idx] = record.to_dict()  # type: ignore
                                logger.debug(f"通过 Text 匹配到行 {df_idx}: '{text_val}'")
                            break
                    else:
                        continue
                    break
            
            # 如果还是没有匹配到，输出警告
            if pd.isna(idx_val) and pd.isna(index_val) and (pd.isna(text_val) or not str(text_val).strip()):
                logger.warning(f"跳过记录：缺少 Idx、Index 和 Text 列，无法定位行。记录：{record.to_dict()}")  # type: ignore
        
        # 遍历有改动的行 (而不是所有行)
        for row_idx, record in row_changes_cache.items():
            # 遍历所有数据列，记录改动
            for column_name in strategy.data_columns:
                if column_name not in df.columns:
                    logger.warning(f"演出表格缺少列：{column_name}")
                    continue
                
                new_value = record.get(column_name)
                if pd.isna(new_value):
                    continue  # 空值表示不变
                
                old_value = df.at[row_idx, column_name]
                excel_row = row_idx + 2  # Excel 行号
                
                # 记录改动
                self.reporter.add_change(
                    file=str(file_path),
                    sheet=sheet_name,
                    row=excel_row,
                    column=column_name,
                    original_value=old_value if pd.notna(old_value) else '',
                    new_value=new_value,
                    locator_info={
                        'Index': record.get('Index'),
                        'Idx': record.get('Idx'),
                        'Text': record.get('Text')
                    }
                )
                
                logger.debug(f"准备同步：{sheet_name} 行{excel_row} "
                           f"{column_name}: '{old_value}' -> '{new_value}'")
    
    def _apply_changes(self, file_path: Path) -> bool:
        """
        应用改动到 Excel 文件（使用基类的标准实现）
        
        Args:
            file_path: Excel 文件路径
            
        Returns:
            bool: 是否成功
        """
        # 获取所有改动
        all_changes = self.reporter.get_all_changes()
        logger.info(f"准备应用 {len(all_changes)} 个改动到文件：{file_path.name}")
        
        # 调用基类的 _apply_changes 方法（通过 build_cell_updates 转换）
        return super()._apply_changes(file_path)
    
    def build_cell_updates(self, changes: List[ChangeRecord]):
        """
        根据改动记录构建单元格更新列表（子类可以实现自定义转换逻辑）
        
        Args:
            changes: 改动记录列表
            
        Returns:
            List[CellUpdate]: 单元格更新列表
        """
        updates = []
        
        for change in changes:
            # 基础更新
            updates.append(CellUpdate(
                sheet_name=change.sheet,
                row=change.row,
                column=change.column,
                value=change.new_value,
                preserve_style=True
            ))
            
            # 额外的更新（如果有）
            if hasattr(change, 'extra_info'):
                for extra_col, extra_val in change.extra_info.items():
                    if extra_col.endswith('_column'):  # 如 'atr_column'
                        col_name = extra_val
                        val_key = extra_col.replace('_column', '_value')  # 如 'atr_value'
                        if val_key in change.extra_info:
                            updates.append(CellUpdate(
                                sheet_name=change.sheet,
                                row=change.row,
                                column=col_name,
                                value=change.extra_info[val_key],
                                preserve_style=True
                            ))
        
        logger.debug(f"构建了 {len(updates)} 个 CellUpdate 对象，preserve_style=True")
        return updates
    
    def print_preview(self, title: str = "改动同步预览报告",
                     detail_formatter: Optional[Callable[[ChangeRecord], str]] = None,
                     show_run_hint: bool = True):
        """
        打印预览报告
        
        Args:
            title: 报告标题
            detail_formatter: 自定义详情格式化函数 (可选)
            show_run_hint: 是否显示运行提示（默认 True）
        """
        if detail_formatter is None:
            # 使用默认的格式化函数
            def format_detail(change: ChangeRecord) -> str:
                """自定义详情格式化"""
                locator = change.extra_info.get('locator_info', {})
                return (
                    f"📝 {change.sheet} 行{change.row}\n"
                    f"   列名：{change.column}\n"
                    f"   原文：{change.original_value}\n"
                    f"   新文：{change.new_value}\n"
                    f"   定位：Index={locator.get('Index', 'N/A')}, "
                    f"Idx={locator.get('Idx', 'N/A')}, "
                    f"Text='{locator.get('Text', 'N/A')}'"
                )
            detail_formatter = format_detail
        
        super().print_preview(title=title, detail_formatter=detail_formatter, show_run_hint=show_run_hint)


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='改动同步工具 - 从改动表格同步修改到演出表格',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 基本用法（正式运行）
  python sync_changes.py --input ./scenario --changes ./changes.xlsx
  
  # 干跑模式（只预览）
  python sync_changes.py --input ./scenario --changes ./changes.xlsx --dry-run
  
  # 使用默认路径
  python sync_changes.py --changes ./changes.xlsx
        """
    )
    
    parser.add_argument('--input', '-i', type=Path, default=Path('./input'),
                       help='演出表格目录（默认：./input）')
    parser.add_argument('--changes', '-c', type=Path, default=None,
                       help='指定单个改动表格文件（不指定时自动读取 input/sync/下所有 .xlsx 文件）')
    parser.add_argument('--output', '-o', type=Path,
                       help='输出目录（默认原地修改）')
    parser.add_argument('--dry-run', action='store_true',
                       help='干跑模式（只预览，不修改）')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='详细输出')
    parser.add_argument('--locators', nargs='+',default= ["ExcelFilename", "SheetName", "Index", "Idx"],
                       help='自定义定位列列表')
    parser.add_argument('--data-columns', nargs='+', dest='data_columns',default=["Text"],
                       help='自定义数据列列表')

    args = parser.parse_args()

    # 配置日志级别
    if args.verbose:
        import logging
        from core.logger import get_logger
        logger = get_logger()
        logger.setLevel(logging.DEBUG)
    else:
        from core.logger import get_logger
        logger = get_logger()
    
    # 确定运行模式
    dry_run = args.dry_run
    
    if dry_run:
        logger.info("干跑模式 - 仅预览改动，不会修改任何文件")
        print("\n🔍 干跑模式 - 仅预览改动，不会修改任何文件\n")
    else:
        logger.warning("正式运行模式 - 将实际修改 Excel 文件")
        print("\n⚠️  正式运行模式 - 将实际修改 Excel 文件\n")
        confirm = input("确认要继续吗？(y/N): ")
        if confirm.lower() != 'y':
            print("已取消操作")
            return 0

    # 创建工具实例（继承自 BaseParamTool）
    tool = ChangeSyncTool(dry_run=dry_run)

    # 处理目录（使用基类的方法）
    results = tool.process_directory(
        input_dir=args.input,
        changes_file=args.changes,
        dry_run=dry_run,
        locator_columns=args.locators,
        data_columns=args.data_columns
    )

    # 打印预览（使用重写的方法）
    tool.print_preview()
    
    # 输出结果
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    print(f"\n📊 处理完成：{success_count}/{total_count} 个文件成功")
    
    return 0 if success_count == total_count else 1


if __name__ == "__main__":
    sys.exit(main())
