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
        self._sync_status: Dict[Any, str] = {}
        self._pending_change_count = 0
        
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
        
        df = self._prepare_changes_dataframe(df)
        
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
                
                try:
                    df = ChangeSyncStrategy.normalize_changes_dataframe(
                        df,
                        required_columns=ChangeSyncStrategy.REQUIRED_LOCATOR_COLUMNS,
                    )
                except ValueError as error:
                    logger.warning(f"文件 {file_path.name} 无法作为同步表加载：{error}，跳过")
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
        merged_df = self._prepare_changes_dataframe(
            pd.concat(all_dfs, ignore_index=True)
        )
        
        logger.info(f"成功加载 {len(merged_df)} 条改动记录（来自 {len(all_dfs)} 个文件）")
        return merged_df

    def _prepare_changes_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        normalized = ChangeSyncStrategy.normalize_changes_dataframe(
            df,
            required_columns=ChangeSyncStrategy.REQUIRED_LOCATOR_COLUMNS,
        )
        normalized = normalized.reset_index(drop=True)
        normalized['_sync_record_id'] = range(len(normalized))
        self._sync_status = {
            record_id: 'pending' for record_id in normalized['_sync_record_id']
        }
        self._pending_change_count = 0
        return normalized

    def _record_id(self, record: pd.Series) -> Any:
        record_id = record.get('_sync_record_id', record.name)
        self._sync_status.setdefault(record_id, 'pending')
        return record_id

    def _set_record_status(self, record: pd.Series, status: str) -> None:
        self._sync_status[self._record_id(record)] = status

    def get_sync_summary(self, finalize: bool = False) -> Dict[str, int]:
        if finalize:
            for record_id, status in list(self._sync_status.items()):
                if status == 'pending':
                    self._sync_status[record_id] = 'skipped'
        return {
            'matched': sum(status == 'matched' for status in self._sync_status.values()),
            'conflicts': sum(status == 'conflict' for status in self._sync_status.values()),
            'skipped': sum(status == 'skipped' for status in self._sync_status.values()),
            'pending_changes': self._pending_change_count,
        }
    
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
        results = super().process_directory(input_dir, dry_run)
        self.get_sync_summary(finalize=True)
        return results
    
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
        # 获取策略对象
        strategy: Optional[ChangeSyncStrategy] = self.filler.strategy_manager.get("change_sync")  # type: ignore
        if not strategy:
            logger.error("策略未找到")
            return

        sheet_changes = strategy.get_changes_for_sheet(file_path.stem, sheet_name)
        if sheet_changes.empty:
            logger.debug(f"工作表 {sheet_name} 没有改动记录，跳过")
            return

        logger.debug(f"工作表 {sheet_name} 有 {len(sheet_changes)} 条改动记录")
        
        candidates: Dict[int, List[pd.Series]] = {}
        for _, record in sheet_changes.iterrows():
            locator = strategy.locate_record(df, record.to_dict())
            if locator.position is None:
                logger.warning(
                    f"同步记录定位失败：status={locator.status}, "
                    f"Index={record.get('Index')}, Idx={record.get('Idx')}"
                )
                if locator.status in {'missing_index', 'index_not_found'}:
                    self._set_record_status(record, 'skipped')
                else:
                    self._set_record_status(record, 'conflict')
                continue

            position = locator.position

            source_row = df.iloc[position]
            cross_check_failed = False
            for column_name in ('Text', 'Name'):
                expected = record.get(column_name)
                if strategy.is_blank(expected):
                    continue
                if column_name not in df.columns or not strategy.values_equal(
                    source_row.get(column_name), expected
                ):
                    logger.warning(
                        f"{column_name} 交叉检查失败：Index={record.get('Index')}"
                    )
                    cross_check_failed = True
                    break
            if cross_check_failed:
                self._set_record_status(record, 'conflict')
                continue

            candidates.setdefault(position, []).append(record)

        for position, records in candidates.items():
            if len(records) > 1:
                logger.warning(f"同一目标行存在多条同步记录：Excel 行 {position + 2}")
                for record in records:
                    self._set_record_status(record, 'conflict')
                continue

            record = records[0]
            excel_row = position + 2
            has_sync_value = False
            for column_name in strategy.data_columns:
                new_value = record.get(column_name)
                if strategy.is_blank(new_value):
                    continue
                has_sync_value = True
                if column_name not in df.columns:
                    logger.warning(f"演出表格缺少列：{column_name}")
                    self._set_record_status(record, 'conflict')
                    break

                old_value = df.iloc[position].get(column_name)
                self._set_record_status(record, 'matched')
                if strategy.values_equal(old_value, new_value):
                    continue

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
                        'Text': record.get('Text'),
                        'Name': record.get('Name'),
                    }
                )
                self._pending_change_count += 1
            if not has_sync_value:
                self._set_record_status(record, 'skipped')
    
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
        summary = self.get_sync_summary(finalize=True)
        print("同步记录统计：")
        print(f"  匹配：{summary['matched']}")
        print(f"  冲突：{summary['conflicts']}")
        print(f"  跳过：{summary['skipped']}")
        print(f"  实际待修改：{summary['pending_changes']}")


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
    parser.add_argument('--locators', nargs='+',default= ["ExcelFilename", "SheetName", "Index", "Idx", "Text"],
                       help='自定义定位列列表')
    parser.add_argument('--data-columns', nargs='+', dest='data_columns',default=["Voice"],
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
