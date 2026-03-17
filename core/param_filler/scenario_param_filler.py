"""
智能参数填写器主模块
整合所有组件实现智能填充功能
"""
from typing import Dict, List, Any, Optional, Tuple, Callable
from pathlib import Path
import pandas as pd
from core.logger import get_logger
from core.excel_management.excel_file_manager import ExcelFileManager
from core.excel_management.excel_editor import ExcelEditor
from .rule_engine import RuleEngine, FillingRule
from .filling_strategy import (
    StrategyManager,
    StrategyRegistry, 
    FillingStrategy,
    DefaultValueStrategy,
    ContextInheritStrategy,
    PatternGenerateStrategy,
    CharacterNameMappingStrategy,
    VoiceIdGeneratorStrategy
)

logger = get_logger()


class ChangeRecord:
    """改动记录"""
    def __init__(self, file: str, sheet: str, row: int, column: str, 
                 original_value: Any, new_value: Any, **kwargs):
        self.file = file
        self.sheet = sheet
        self.row = row
        self.column = column
        self.original_value = original_value
        self.new_value = new_value
        self.extra_info = kwargs  # 额外的字段（如 atr_column, new_atr_value 等）


class ChangeReporter:
    """改动报告器 - 提供标准的干跑预览功能"""
    
    def __init__(self):
        """初始化"""
        self.changes: List[ChangeRecord] = []
        self.stats = {
            'files_processed': 0,
            'sheets_processed': 0,
            'total_changes': 0,
        }
    
    def add_change(self, file: str, sheet: str, row: int, column: str,
                   original_value: Any, new_value: Any, **kwargs):
        """添加改动记录"""
        change = ChangeRecord(file, sheet, row, column, original_value, new_value, **kwargs)
        self.changes.append(change)
        self.stats['total_changes'] += 1
    
    def print_preview(self, title: str = "改动预览报告", 
                     detail_formatter: Optional[Callable[[ChangeRecord], str]] = None):
        """
        打印预览报告
        
        Args:
            title: 报告标题
            detail_formatter: 自定义详情格式化函数（可选），接收 ChangeRecord 返回字符串
        """
        print("\n" + "=" * 80)
        print(f"📊 {title}")
        print("=" * 80)
        
        if not self.changes:
            print("\n✅ 无需任何改动！")
        else:
            print(f"\n📝 发现 {self.stats['total_changes']} 处需要修改:\n")
            
            # 按文件和工作表分组
            grouped = {}
            for change in self.changes:
                key = (change.file, change.sheet)
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(change)
            
            # 打印每个工作表的改动
            for (file_name, sheet_name), changes in grouped.items():
                print(f"\n📄 文件：{file_name} | 工作表：{sheet_name}")
                print("-" * 80)
                
                if detail_formatter:
                    # 使用自定义格式化函数
                    print(detail_formatter(changes[0]))
                    print("-" * 80)
                    for change in changes:
                        print(detail_formatter(change))
                else:
                    # 使用默认格式
                    print(f"{'行号':<8} {'列名':<10} {'原值':<20} {'->':<5} {'新值':<20}")
                    print("-" * 80)
                    for change in changes:
                        print(
                            f"{change.row:<8} "
                            f"{change.column:<10} "
                            f"{str(change.original_value):<20} "
                            f"-> {str(change.new_value):<20}"
                        )
        
        # 打印统计信息
        print("\n" + "=" * 80)
        print("📈 统计信息")
        print("=" * 80)
        print(f"处理文件数：{self.stats['files_processed']}")
        print(f"处理工作表数：{self.stats['sheets_processed']}")
        print(f"总改动数：{self.stats['total_changes']}")
        print("=" * 80)
        
        if self.changes:
            print("\n💡 提示：使用 --run 参数执行实际修改")
        print()
    
    def get_all_changes(self) -> List[ChangeRecord]:
        """获取所有改动记录"""
        return self.changes
    
    def has_changes(self) -> bool:
        """判断是否有改动"""
        return len(self.changes) > 0
    
    def clear(self):
        """清空所有改动记录和统计"""
        self.changes.clear()
        self.stats = {
            'files_processed': 0,
            'sheets_processed': 0,
            'total_changes': 0,
        }


class BaseParamTool:
    """参数工具基类 - 定义标准的工具开发模板
    
    使用模板方法模式，定义标准的处理流程：
    1. 初始化（注册策略）
    2. 处理目录（遍历文件）
    3. 处理文件（加载 Excel）
    4. 分析数据（调用子类实现）
    5. 预览/执行（干跑或正式运行）
    
    子类只需实现特定步骤即可快速创建新工具
    """
    
    def __init__(self, strategy_class: type[FillingStrategy], strategy_name: str):
        """
        初始化基类
        
        Args:
            strategy_class: 策略类
            strategy_name: 策略名称
        """
        # 创建智能填充器（不自动注册策略）
        self.filler = SmartParameterFiller(auto_register=False)
        
        # 注册策略
        self.filler.register_custom_strategy(strategy_class, name=strategy_name, verbose=False)
        
        # 获取策略实例
        self.strategy = self.filler.strategy_manager.get(strategy_name)
        if not self.strategy:
            raise RuntimeError(f"策略注册失败：{strategy_name}")
        
        # 创建报告器
        self.reporter = ChangeReporter()
        
        logger.debug(f"{self.__class__.__name__} 初始化完成")
    
    def process_directory(self, input_dir: Path, dry_run: bool = True) -> Dict[Path, bool]:
        """
        处理整个目录（标准流程，子类通常不需要重写）
        
        Args:
            input_dir: 输入目录
            dry_run: 是否干跑模式
            
        Returns:
            Dict[Path, bool]: {文件路径：是否成功}
        """
        results = {}
        
        if not input_dir.exists():
            logger.error(f"输入目录不存在：{input_dir}")
            return results
        
        # 发现 Excel 文件
        excel_files = [
            f for f in input_dir.iterdir()
            if f.suffix in ['.xlsx', '.xls'] and not f.name.startswith('~')
        ]
        
        logger.info(f"发现 {len(excel_files)} 个 Excel 文件")
        
        # 处理每个文件
        for file_path in sorted(excel_files):
            success = self.process_file(file_path, dry_run)
            results[file_path] = success
        
        return results
    
    def process_file(self, file_path: Path, dry_run: bool = True) -> bool:
        """
        处理单个文件（标准流程，子类通常不需要重写）
        
        Args:
            file_path: Excel 文件路径
            dry_run: 是否干跑模式
            
        Returns:
            bool: 是否成功
        """
        try:
            mode_str = '[干跑] ' if dry_run else ''
            logger.info(f"{mode_str}处理文件：{file_path.name}")
            
            # 加载 Excel
            excel_data = self.filler.excel_manager.load_excel(file_path)
            
            # 分析数据（子类实现）
            self.analyze_dataframes(excel_data, file_path)
            
            # 输出结果
            change_count = len(self.reporter.get_all_changes())
            if change_count > 0:
                logger.info(f"发现 {change_count} 处需要修改")
            else:
                logger.info("无需修改")
            
            # 如果不是干跑模式，执行实际修改
            if not dry_run and self.reporter.has_changes():
                self._apply_changes(file_path)
            
            self.reporter.stats['files_processed'] += 1
            return True
            
        except Exception as e:
            logger.error(f"处理文件失败：{file_path} - {e}", exc_info=True)
            return False
    
    def analyze_dataframes(self, excel_data: Dict[str, pd.DataFrame], file_path: Path):
        """
        分析 DataFrame（由子类实现具体分析逻辑）
        
        Args:
            excel_data: {工作表名：DataFrame}
            file_path: 文件路径
        """
        for sheet_name, df in excel_data.items():
            if df.empty:
                logger.debug(f"工作表 {sheet_name} 为空，跳过")
                continue
            
            self.reporter.stats['sheets_processed'] += 1
            self.process_dataframe(df, sheet_name, file_path)
    
    def process_dataframe(self, df: pd.DataFrame, sheet_name: str, file_path: Path):
        """
        处理单个 DataFrame（由子类实现）
        
        Args:
            df: DataFrame
            sheet_name: 工作表名称
            file_path: 文件路径
        """
        raise NotImplementedError("子类必须实现 process_dataframe 方法")
    
    def _apply_changes(self, file_path: Path) -> bool:
        """
        应用改动到 Excel 文件（子类可以实现自定义的写入逻辑）
        
        Args:
            file_path: Excel 文件路径
            
        Returns:
            bool: 是否成功
        """
        try:
            updates = self.build_cell_updates(self.reporter.get_all_changes())
            
            if not updates:
                return True
            
            # 批量更新
            success = self.filler.excel_editor.update_cells_batch(file_path, updates)
            
            if success:
                logger.info(f"成功应用 {len(updates)} 个改动")
            else:
                logger.warning(f"部分改动应用失败")
            
            return success
            
        except Exception as e:
            logger.error(f"应用改动失败：{file_path} - {e}", exc_info=True)
            return False
    
    def build_cell_updates(self, changes: List[ChangeRecord]):
        """
        根据改动记录构建单元格更新列表（子类可以实现自定义转换逻辑）
        
        Args:
            changes: 改动记录列表
            
        Returns:
            List[CellUpdate]: 单元格更新列表
        """
        from core.excel_management.excel_editor import CellUpdate
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
        
        return updates
    
    def print_preview(self, title: str = "改动预览报告",
                     detail_formatter: Optional[Callable[[ChangeRecord], str]] = None):
        """
        打印预览报告
        
        Args:
            title: 报告标题
            detail_formatter: 自定义详情格式化函数（可选）
        """
        self.reporter.print_preview(title=title, detail_formatter=detail_formatter)


class SmartParameterFiller:
    """智能参数填写器"""
    
    def __init__(self, config_path: Optional[Path] = None, auto_register: bool = True, dry_run: bool = False):
        """
        初始化智能参数填写器
        
        Args:
            config_path: YAML 配置文件路径（可选）
            auto_register: 是否自动注册所有内置策略（默认 True）
            dry_run: 是否为干跑模式（默认 False）。干跑模式下不会实际修改文件，仅进行规则匹配和值生成的模拟。
        """
        self.rule_engine = RuleEngine(config_path)
        self.excel_manager = ExcelFileManager(cache_enabled=True)
        self.excel_editor = ExcelEditor()
        
        # 获取策略管理器单例
        self.strategy_manager = StrategyManager()
        
        # 根据参数决定是否注册所有策略
        if auto_register:
            self._register_strategies()
        else:
            logger.debug("智能参数填写器初始化完成（未自动注册策略）")
        
        # 设置干跑模式
        self.dry_run = dry_run
        if dry_run:
            logger.info("智能参数填写器已启用干跑模式")
        else:
            logger.info("智能参数填写器初始化完成")
    
    def _register_strategies(self):
        """注册所有可用的填充策略"""
        # 基础策略
        self.strategy_manager.register(DefaultValueStrategy())
        self.strategy_manager.register(ContextInheritStrategy())
        self.strategy_manager.register(PatternGenerateStrategy())
        
        # 高级策略
        self.strategy_manager.register(CharacterNameMappingStrategy())
        self.strategy_manager.register(VoiceIdGeneratorStrategy())
        
        logger.info("已注册所有内置填充策略")
    
    def register_custom_strategy(self, strategy_class: type[FillingStrategy], name: Optional[str] = None, verbose: bool = True):
        """
        注册自定义策略类（对外接口）
        
        Args:
            strategy_class: 自定义策略类
            name: 策略名称（可选）
            verbose: 是否输出日志信息（默认 True）
            
        Example:
            ```python
            filler = SmartParameterFiller()
            
            # 方式 1：使用类名作为策略名
            filler.register_custom_strategy(MyCustomStrategy)
            
            # 方式 2：指定策略名
            filler.register_custom_strategy(MyCustomStrategy, "my_custom")
            
            # 方式 3：静默注册
            filler.register_custom_strategy(MyCustomStrategy, "my_custom", verbose=False)
            ```
        """
        self.strategy_manager.register_custom_strategy(strategy_class, name)
        if verbose:
            logger.info(f"注册自定义策略：{name or strategy_class.__name__}")
    
    def discover_files(self, input_dir: Path) -> List[Path]:
        """
        发现需要处理的 Excel 文件
        
        Args:
            input_dir: 输入目录
            
        Returns:
            List[Path]: Excel 文件路径列表
        """
        if not input_dir.exists():
            logger.error(f"输入目录不存在：{input_dir}")
            return []
        
        excel_files = [
            f for f in input_dir.iterdir()
            if f.suffix in ['.xlsx', '.xls'] and not f.name.startswith('~')
        ]
        
        logger.info(f"发现 {len(excel_files)} 个 Excel 文件")
        return sorted(excel_files)
    
    def discover_sheets(self, file_path: Path) -> List[str]:
        """
        发现需要处理的工作表
        
        Args:
            file_path: Excel 文件路径
            
        Returns:
            List[str]: 工作表名称列表
        """
        try:
            sheet_names = self.excel_manager.get_sheet_names(file_path)
            logger.debug(f"文件 {file_path.name} 包含 {len(sheet_names)} 个工作表")
            return sheet_names
        except Exception as e:
            logger.error(f"获取工作表失败：{file_path} - {e}")
            return []
    
    def extract_parameters(self, df: pd.DataFrame, sheet_name: str) -> Dict[str, List[Tuple[int, Any]]]:
        """
        从工作表中提取需要填充的参数
        
        Args:
            df: DataFrame
            sheet_name: 工作表名称
            
        Returns:
            Dict[str, List[Tuple[int, Any]]]: {列名：[(行索引，单元格值)]}
        """
        params_to_fill = {}
        
        for column in df.columns:
            # 检查该列是否有规则适用
            rules = self.rule_engine.get_applicable_rules(sheet_name, column)
            if not rules:
                continue
            
            # 找出该列中需要填充的单元格
            needs_fill = []
            for idx, value in enumerate(df[column]):
                if pd.isna(value) or value == "":
                    needs_fill.append((idx, value))
            
            if needs_fill:
                params_to_fill[column] = needs_fill
                logger.debug(f"工作表 {sheet_name} 的列 {column} 有 {len(needs_fill)} 个单元格需要填充")
        
        return params_to_fill
    
    def generate_filling_plan(
        self,
        sheet_name: str,
        column_name: str,
        cell_index: int,
        cell_value: Any,
        df: pd.DataFrame
    ) -> Optional[Tuple[FillingRule, Any]]:
        """
        生成单个单元格的填充方案
        
        Args:
            sheet_name: 工作表名称
            column_name: 列名
            cell_index: 单元格行索引
            cell_value: 单元格值
            df: DataFrame
            
        Returns:
            Optional[Tuple[FillingRule, Any]]: (规则，填充值)，无合适方案返回 None
        """
        rules = self.rule_engine.get_applicable_rules(sheet_name, column_name)
        
        for rule in rules:
            # 通过策略管理器获取策略
            strategy = self.strategy_manager.get(rule.strategy_name)
            if strategy is None:
                logger.warning(f"策略未找到：{rule.strategy_name}")
                continue
            
            # 构建上下文
            context = {
                'sheet_name': sheet_name,
                'column_name': column_name,
                'row_index': cell_index,
                'cell_value': cell_value,
                'dataframe': df,
                'row_data': df.iloc[cell_index].to_dict() if cell_index < len(df) else {}
            }
            
            # 添加额外条件检查
            if rule.condition:
                condition_func = self._parse_condition(rule.condition)
                if condition_func:
                    context['additional_condition'] = condition_func
            
            # 检查是否可以填充
            if strategy.can_fill(cell_value, context):
                fill_value = strategy.fill(cell_value, context, rule.params)
                logger.debug(f"应用规则 {rule.name} -> 填充值：{fill_value}")
                return (rule, fill_value)
        
        return None
    
    def _parse_condition(self, condition: str) -> Optional[Callable[[Dict[str, Any]], bool]]:
        """
        解析条件字符串为函数
        
        Args:
            condition: 条件字符串
            
        Returns:
            Optional[Callable[[Dict[str, Any]], bool]]: 条件函数
        """
        # 预定义的条件
        conditions = {
            'cell_is_empty': lambda ctx: True,
            'cell_is_empty_and_has_text': lambda ctx: self._check_has_text_in_row(ctx),
        }
        return conditions.get(condition)
    
    def _check_has_text_in_row(self, context: Dict[str, Any]) -> bool:
        """检查行中是否有文本内容"""
        row_data = context.get('row_data', {})
        text_columns = ['台词', '对话', 'text', 'dialogue']
        
        for col in text_columns:
            if col in row_data:
                value = row_data.get(col)
                if pd.notna(value) and str(value).strip():
                    return True
        
        return False
    
    def execute_filling(
        self,
        file_path: Path,
        sheet_name: str,
        filling_plan: Dict[int, Dict[str, Any]]
    ) -> bool:
        """
        执行填充
        
        Args:
            file_path: Excel 文件路径
            sheet_name: 工作表名称
            filling_plan: {行索引：{列名：填充值}} 的字典
            
        Returns:
            bool: 是否成功
        """
        try:
            updates = []
            for row_idx, column_values in filling_plan.items():
                # column_values 是 {列名：填充值} 的字典
                for column_name, value in column_values.items():
                    # 使用 CellUpdate 对象进行批量更新
                    from core.excel_management.excel_editor import CellUpdate
                    update = CellUpdate(
                        sheet_name=sheet_name,
                        row=row_idx + 2,  # Excel 行号从 2 开始（第 1 行是表头）
                        column=column_name,
                        value=value,
                        preserve_style=True
                    )
                    updates.append(update)
            
            if not updates:
                return True
            
            # 干跑模式下不实际执行更新
            if self.dry_run:
                logger.info(f"[DRY RUN] 模拟填充完成：{file_path.name} -> {sheet_name}，共 {len(updates)} 个单元格")
                return True
            
            # 正常模式下执行批量更新
            success = self.excel_editor.update_cells_batch(file_path, updates)
            
            if success:
                logger.info(f"工作表 {sheet_name} 填充完成，共 {len(updates)} 个单元格")
            else:
                logger.warning(f"工作表 {sheet_name} 部分填充失败")
            
            return success
            
        except Exception as e:
            logger.error(f"执行填充失败：{file_path} -> {sheet_name} - {e}", exc_info=True)
            return False
    
    def process_file(self, file_path: Path, sheet_names: Optional[List[str]] = None) -> bool:
        """
        处理单个 Excel 文件
        
        Args:
            file_path: Excel 文件路径
            sheet_names: 要处理的工作表列表（None 表示所有）
            
        Returns:
            bool: 是否成功
        """
        try:
            logger.info(f"开始处理文件：{file_path.name}")
            
            # 加载 Excel
            excel_data = self.excel_manager.load_excel(file_path)
            
            # 确定要处理的工作表
            if sheet_names:
                sheets_to_process = [s for s in sheet_names if s in excel_data]
            else:
                sheets_to_process = list(excel_data.keys())
            
            success_count = 0
            for sheet_name in sheets_to_process:
                df = excel_data[sheet_name]
                
                if df.empty:
                    logger.debug(f"工作表为空：{sheet_name}")
                    continue
                
                # 提取需要填充的参数
                params_to_fill = self.extract_parameters(df, sheet_name)
                
                if not params_to_fill:
                    logger.debug(f"工作表 {sheet_name} 没有需要填充的参数")
                    continue
                
                # 为每个参数生成填充方案
                filling_plan: Dict[int, Dict[str, Any]] = {}
                for column_name, cells in params_to_fill.items():
                    for row_idx, cell_value in cells:
                        plan = self.generate_filling_plan(
                            sheet_name, column_name, row_idx, cell_value, df
                        )
                        
                        if plan:
                            rule, fill_value = plan
                            if row_idx not in filling_plan:
                                filling_plan[row_idx] = {}
                            filling_plan[row_idx][column_name] = fill_value
                
                # 执行填充
                if filling_plan:
                    success = self.execute_filling(file_path, sheet_name, filling_plan)
                    if success:
                        success_count += 1
            
            logger.info(f"文件 {file_path.name} 处理完成，成功 {success_count}/{len(sheets_to_process)} 个工作表")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"处理文件失败：{file_path} - {e}", exc_info=True)
            return False
    
    def process_directory(self, input_dir: Path, sheet_names: Optional[List[str]] = None) -> Dict[Path, bool]:
        """
        处理整个目录
        
        Args:
            input_dir: 输入目录
            sheet_names: 要处理的工作表列表
            
        Returns:
            Dict[Path, bool]: {文件路径：是否成功} 的字典
        """
        results = {}
        
        files = self.discover_files(input_dir)
        for file_path in files:
            success = self.process_file(file_path, sheet_names)
            results[file_path] = success
        
        return results
