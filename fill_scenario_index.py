"""
Index列清理填充工具
自动清理并填充演出表格的 Index 列，按照有效的 Text 数据进行排序编号
"""
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import pandas as pd
from core.logger import get_logger
from core.param_filler.scenario_param_filler import BaseParamTool, ChangeRecord
from core.constants import SpecialName
from core.excel_management.excel_editor import ExcelEditor, CellUpdate

logger = get_logger()


class FillIndexTool(BaseParamTool):
    """
    Index列清理填充工具
    
    功能:
    - 遍历所有演出表格，为 Index列填充连续序号
    - 仅对有效的 Text 行进行编号（Text 非空且 Name 不在排除列表中）
    - 排除的名称包括：renpy, naninovel, label, steam, unlock, choice, jump 等
    - 支持自定义排除的名称列表
    - 默认干跑模式，预览改动但不实际修改文件
    
    工作流程:
    1. 加载 Excel 文件
    2. 逐行检查 Name 和 Text 列
    3. 当 Text 非空且 Name 有效时，递增计数器
    4. 记录需要更新的 Index 值
    5. 输出改动预览或执行实际修改
    """
    
    # 默认需要排除的特殊名称
    DEFAULT_EXCLUDED_NAMES = set([
        SpecialName.RENPY_COMMAND.value,
        SpecialName.NANINOVEL_COMMAND.value,
        SpecialName.LABEL_COMMAND.value,
        SpecialName.STEAM_COMMAND.value,
        SpecialName.UNLOCK_COMMAND.value,
        SpecialName.CHOICE_COMMAND.value,
        SpecialName.JUMP_COMMAND.value,
    ])
    
    def __init__(self, excluded_names: Optional[List[str]] = None, dry_run: bool = True):
        """
        初始化 Index列清理填充工具
        
        Args:
            excluded_names: 需要排除的名称列表（可选，默认使用 DEFAULT_EXCLUDED_NAMES）
            dry_run: 是否干跑模式（默认 True）。干跑模式下不会实际修改文件。
        """
        # 调用父类初始化（注册一个虚拟策略，实际不使用）
        from core.param_filler.filling_strategy import FillingStrategy
        from abc import ABCMeta
        
        # 创建一个临时的空策略用于初始化
        class DummyStrategy(FillingStrategy, metaclass=ABCMeta):
            def can_fill(self, cell_value: Any, context: Dict[str, Any]) -> bool:
                return False
            
            def fill(self, cell_value: Any, context: Dict[str, Any], params: Dict[str, Any]) -> Any:
                return cell_value
        
        super().__init__(DummyStrategy, "dummy", dry_run=dry_run)
        
        # 设置排除的名称列表
        self.excluded_names = set(excluded_names) if excluded_names else self.DEFAULT_EXCLUDED_NAMES.copy()
        
        # 添加常见的变体形式
        self.excluded_names.update([
            name.lower() for name in list(self.excluded_names)
        ])
        self.excluded_names.update([
            name.upper() for name in list(self.excluded_names)
        ])
        
        # 列索引缓存：{(sheet_name, column_name): column_index}
        self._column_cache: Dict[tuple, int] = {}
        
        # Excel 编辑器实例
        self.excel_editor = ExcelEditor()
        
        logger.debug(f"FillIndexTool 初始化完成，excluded_names={self.excluded_names}, dry_run={dry_run}")
    
    def is_valid_text_row(self, row_data: Dict[str, Any]) -> bool:
        """
        判断某一行是否是有效的文本行
        
        条件:
        1. Text 列非空
        2. Name 列不在排除列表中（如果有 Name 列）
        
        Args:
            row_data: 行数据字典
            
        Returns:
            bool: 是否有效
        """
        # 获取 Text 列的值（支持多种列名）
        text_columns = ['Text', '台词', '对话', 'text', 'dialogue']
        text_value = None
        
        for col in text_columns:
            if col in row_data:
                text_value = row_data.get(col)
                break
        
        # Text 为空则无效
        if pd.isna(text_value) or str(text_value).strip() == "":
            return False
        
        # 获取 Name 列的值（支持多种列名）
        name_columns = ['Name', '说话人', '角色', 'name', 'speaker', 'character']
        name_value = None
        
        for col in name_columns:
            if col in row_data:
                name_value = row_data.get(col)
                break
        
        # 没有 Name 列或 Name 为空，视为有效
        if pd.isna(name_value) or str(name_value).strip() == "":
            return True
        
        # 检查 Name 是否在排除列表中
        name_str = str(name_value).strip()
        if name_str in self.excluded_names:
            return False
        
        # 也检查小写和大写形式
        if name_str.lower() in self.excluded_names:
            return False
        
        if name_str.upper() in self.excluded_names:
            return False
        
        return True
    
    def process_dataframe(self, df: pd.DataFrame, sheet_name: str, file_path: Path):
        """
        处理单个 DataFrame
        
        Args:
            df: DataFrame
            sheet_name: 工作表名称
            file_path: 文件路径
        """
        # 检查是否有 Index列
        index_columns = ['Index', 'Idx', 'idx', 'index']
        index_column = None
        
        for col in index_columns:
            if col in df.columns:
                index_column = col
                break
        
        if not index_column:
            logger.debug(f"工作表 {sheet_name} 没有 Index 列，跳过")
            return
        
        # 检查是否有 Text 列
        text_columns = ['Text', '台词', '对话', 'text', 'dialogue']
        has_text_column = any(col in df.columns for col in text_columns)
        
        if not has_text_column:
            logger.debug(f"工作表 {sheet_name} 没有 Text 列，跳过")
            return
        
        logger.debug(f"处理工作表：{sheet_name}，共 {len(df)} 行")
        
        # 提前获取实际列名和 Series 数据
        actual_text_col = next((col for col in text_columns if col in df.columns), None)
        name_columns = ['Name', '说话人', '角色', 'name', 'speaker', 'character']
        actual_name_col = next((col for col in name_columns if col in df.columns), None)
        
        text_series = df[actual_text_col] if actual_text_col else None
        name_series = df[actual_name_col] if actual_name_col else None
        index_series = df[index_column]
        
        # 向量化判断有效性，避免 to_dict() 和函数调用
        valid_flags = []
        excluded_names = self.excluded_names
        
        for idx in range(len(df)):
            # 直接从 Series 获取值，避免 to_dict()
            text_value = text_series.iloc[idx] if text_series is not None else None
            
            # Text 为空则无效
            if pd.isna(text_value) or str(text_value).strip() == "":
                valid_flags.append(False)
                continue
            
            # 检查 Name 列
            name_value = name_series.iloc[idx] if name_series is not None else None
            if pd.isna(name_value) or str(name_value).strip() == "":
                valid_flags.append(True)
                continue
            
            # 检查是否在排除列表中
            name_str = str(name_value).strip()
            if (name_str in excluded_names or 
                name_str.lower() in excluded_names or 
                name_str.upper() in excluded_names):
                valid_flags.append(False)
            else:
                valid_flags.append(True)
        
        # 计算有效的 Index 并收集更新
        current_index = 0
        updates_needed = []
        
        for idx in range(len(df)):
            if valid_flags[idx]:
                # 有效文本行
                current_index += 1
                expected_index = current_index
                old_index_value = index_series.iloc[idx]
                
                # 检查是否需要更新
                needs_update = False
                old_index_str = str(old_index_value).strip() if not pd.isna(old_index_value) else ""
                
                if pd.isna(old_index_value) or old_index_str == "":
                    needs_update = True
                else:
                    try:
                        old_index_int = int(float(old_index_value))
                        if old_index_int != expected_index:
                            needs_update = True
                    except (ValueError, TypeError):
                        needs_update = True
                
                if needs_update:
                    updates_needed.append((idx, expected_index, old_index_value, False))
                    logger.debug(f"行 {idx + 2}: Index {old_index_value} -> {expected_index}")
            else:
                # 无效行，检查是否需要清空
                old_index_value = index_series.iloc[idx]
                old_index_str = str(old_index_value).strip() if not pd.isna(old_index_value) else ""
                if not pd.isna(old_index_value) and old_index_str != "":
                    updates_needed.append((idx, '', old_index_value, True))
                    logger.debug(f"行 {idx + 2}: Index {old_index_value} -> '' (清空)")
        
        # 记录所有改动
        for row_idx, new_index, old_index, is_clear in updates_needed:
            excel_row = row_idx + 2  # Excel 行号从 2 开始（第 1 行是表头）
            
            self.reporter.add_change(
                file=str(file_path),
                sheet=sheet_name,
                row=excel_row,
                column=index_column,
                original_value=old_index if pd.notna(old_index) else '',
                new_value=new_index,
                is_clear=is_clear  # 标记是否为清空操作
            )
        
        # 统计信息
        fill_count = sum(1 for u in updates_needed if not u[3])
        clear_count = sum(1 for u in updates_needed if u[3])
        logger.info(f"工作表 {sheet_name}: 发现 {len(updates_needed)} 处需要更新 Index (填充：{fill_count}, 清空：{clear_count})")
    
    def _find_column_index_cached(self, file_path: Path, sheet_name: str, column_name: str) -> int:
        """
        查找列索引，使用缓存
        
        Args:
            file_path: Excel 文件路径
            sheet_name: 工作表名称
            column_name: 列名
            
        Returns:
            int: 列索引（从 1 开始）
        """
        # 尝试从缓存获取
        cache_key = (file_path.stem, sheet_name, column_name)
        if cache_key in self._column_cache:
            return self._column_cache[cache_key]
        
        # 使用 ExcelEditor 的方法查找
        col_idx = self.excel_editor.find_column_index(file_path, sheet_name, column_name)
        
        if col_idx is None:
            raise ValueError(f"列名不存在：{column_name}")
        
        # 缓存结果
        self._column_cache[cache_key] = col_idx
        return col_idx
    
    def _apply_changes(self, file_path: Path) -> bool:
        """
        应用改动到 Excel 文件（优化版：复用 excel_editor 模块）
        
        Args:
            file_path: Excel 文件路径
            
        Returns:
            bool: 是否成功
        """
        try:
            changes = self.reporter.get_all_changes()
            if not changes:
                return True
            
            logger.info(f"准备应用 {len(changes)} 个改动到文件：{file_path.name}")
            
            # 构建 CellUpdate 列表
            updates = []
            for change in changes:
                update = CellUpdate(
                    sheet_name=change.sheet,
                    row=change.row,
                    column=change.column,
                    value=change.new_value,
                    preserve_style=True
                )
                updates.append(update)
            
            # 使用 ExcelEditor 的批量更新方法
            success = self.excel_editor.update_cells_batch(file_path, updates)
            
            if success:
                logger.info(f"成功应用 {len(updates)} 个改动到 {file_path.name}")
            else:
                logger.warning(f"部分改动应用失败：{file_path.name}")
            
            return success
            
        except Exception as e:
            logger.error(f"应用改动失败：{file_path} - {e}", exc_info=True)
            return False
    
    def print_preview(self, title: str = "Index列清理填充预览报告",
                     detail_formatter: Optional[Callable[[ChangeRecord], str]] = None,
                     show_run_hint: bool = True):
        """
        打印预览报告（精简版）
        
        Args:
            title: 报告标题
            detail_formatter: 自定义详情格式化函数（可选）
            show_run_hint: 是否显示运行提示（默认 True）
        """
        # 定义默认的格式化函数
        def default_format_detail(change: ChangeRecord) -> str:
            """精简详情格式化"""
            action = "清空" if change.extra_info.get('is_clear', False) else f"{change.new_value}"
            return f"  行{change.row:<5} {change.column:<8} {str(change.original_value):<10} -> {action}"
        
        # 如果没有提供自定义格式化器，使用默认的
        if detail_formatter is None:
            detail_formatter = default_format_detail
        
        print("\n" + "=" * 60)
        print(f"📊 {title}")
        print("=" * 60)
        
        changes = self.reporter.get_all_changes()
        
        # 按文件和工作表分组统计（移到条件判断外，确保始终有定义）
        grouped = {}
        
        if not changes:
            print("\n✅ 无需任何改动！")
        else:
            for change in changes:
                key = (change.file, change.sheet)
                if key not in grouped:
                    grouped[key] = {'fill': [], 'clear': []}
                
                is_clear = change.extra_info.get('is_clear', False)
                if is_clear:
                    grouped[key]['clear'].append(change)
                else:
                    grouped[key]['fill'].append(change)
            
            print(f"\n📝 发现 {len(changes)} 处需要修改:\n")
            
            # 打印每个工作表的改动（精简格式）
            for (file_name, sheet_name), changes_dict in grouped.items():
                fill_count = len(changes_dict['fill'])
                clear_count = len(changes_dict['clear'])
                
                print(f"📄 {file_name} | {sheet_name}")
                if fill_count > 0:
                    print(f"   填充 {fill_count} 个 Index:")
                    # 只显示前 5 个，其余省略
                    for change in changes_dict['fill'][:5]:
                        print(detail_formatter(change))
                    if fill_count > 5:
                        print(f"   ... 还有 {fill_count - 5} 个填充")
                
                if clear_count > 0:
                    print(f"   清空 {clear_count} 个 Index:")
                    for change in changes_dict['clear'][:5]:
                        print(detail_formatter(change))
                    if clear_count > 5:
                        print(f"   ... 还有 {clear_count - 5} 个清空")
                print()
        
        # 打印统计信息（精简版）
        stats = self.reporter.stats
        fill_total = sum(len(g['fill']) for g in grouped.values()) if changes else 0
        clear_total = sum(len(g['clear']) for g in grouped.values()) if changes else 0
        
        print("=" * 60)
        print(f"📈 统计：{stats['files_processed']} 个文件，{stats['sheets_processed']} 个工作表")
        print(f"   总改动数：{stats['total_changes']} (填充：{fill_total}, 清空：{clear_total})")
        print("=" * 60)
        
        if changes and show_run_hint:
            print("\n💡 提示：使用 --run 参数执行实际修改")
        print()


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Index 列清理填充工具 - 自动为演出表格填充连续的 Index 序号',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 基本用法（干跑模式，只预览）
  python fill_scenario_index.py --input ./scenario
  
  # 正式执行
  python fill_scenario_index.py --input ./scenario --run
  
  # 自定义排除的名称
  python fill_scenario_index.py --input ./scenario --exclude name1 name2 name3
  
  # 指定特定目录
  python fill_scenario_index.py --input ./my_scenarios --run
        """
    )
    
    parser.add_argument('--input', '-i', type=Path, default=Path('./input'),
                       help='演出表格目录（默认：./input）')
    parser.add_argument('--output', '-o', type=Path,
                       help='输出目录（默认原地修改）')
    parser.add_argument('--dry-run', action='store_true',
                       help='干跑模式（只预览，不修改）')
    parser.add_argument('--exclude', nargs='+', default=None,
                       help='自定义需要排除的名称列表（默认使用 constants 中定义的特殊名称）')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='详细输出')
    
    args = parser.parse_args()
    
    # 配置日志级别
    if args.verbose:
        import logging
        logger.setLevel(logging.DEBUG)
    
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
    
    # 创建工具实例
    tool = FillIndexTool(excluded_names=args.exclude, dry_run=dry_run)
    
    # 处理目录
    results = tool.process_directory(input_dir=args.input, dry_run=dry_run)
    
    # 打印预览
    tool.print_preview()
    
    # 输出结果
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    print(f"\n📊 处理完成：{success_count}/{total_count} 个文件成功")
    
    return 0 if success_count == total_count else 1


if __name__ == "__main__":
    sys.exit(main())
