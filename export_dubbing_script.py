"""
导出配音台本工具
从 Excel 剧本中提取所有对话，按角色整合并输出表格
"""
import argparse
from pathlib import Path
import re
from typing import List, Optional
import pandas as pd
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter

from core.config_manager import AppConfig
from core.logger import get_logger
from core.excel_management.excel_file_manager import ExcelFileManager, ExcelFileNotFoundError, ExcelFormatError
from core.excel_management.dataframe_processor import DataFrameProcessor
from core.constants import ColumnName, SheetName, SpecialName
from core.param_process.param_translator import ParamTranslator

logger = get_logger(__name__)

SPECIAL_NAME_VALUES = {member.value for member in SpecialName}

class DialogueExporter:
    """配音台本导出器"""

    def __init__(
        self,
        config: AppConfig,
        input_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        default_speaker: str = "",
        sort_by: Optional[List[str]] = None,
        merge_files: bool = False,
        output_format: str = "excel",
        use_cache_map: bool = False,
        selected_characters: Optional[List[str]] = None,
        per_character: bool = False
    ):
        """
        Args:
            config: 应用配置
            input_dir: 输入目录（覆盖配置）
            output_dir: 输出目录（覆盖配置）
            default_speaker: 角色为空时的默认名称
            sort_by: 排序字段列表，如 ["角色", "行号"]
            merge_files: 是否合并所有文件为一个表格
            output_format: 输出格式 "excel" 或 "csv"
        """
        self.config = config
        self.input_dir = input_dir or config.paths.input_dir
        self.output_dir = output_dir or (config.paths.output_dir / "dialogue_exports")
        self.default_speaker = default_speaker
        self.sort_by = sort_by or ["角色", "行号"]
        self.ignore_word = ["无语音"]
        self.ignore_text = [""]
        self.merge_files = merge_files
        self.output_format = output_format.lower()
        self.use_cache_map = use_cache_map
        self.selected_characters = selected_characters
        self.per_character = per_character

        self.count_dict = {}  # 用于统计每个角色在每个工作表中的对话数量
        self.voice_filename_cache = {}  # 缓存完整的语音文件名，键为(speaker, sheet_name)元组

        self.excel_manager = ExcelFileManager(cache_enabled=True)
        self.df_processor = DataFrameProcessor(config)
        self.translator = ParamTranslator()

    def _convert_chinese_to_english(self, chinese_name: str) -> str:
        """
        将中文角色名转换为英文字符串
        这里可以根据实际需求实现具体的转换逻辑
        """
        # 示例转换规则，实际使用时需要根据项目需求定制
        conversion_map = {
            "主角": "hero",
            "女主角": "heroine", 
            "旁白": "narrator",
            "系统": "system"
            # 可以添加更多映射关系
        }
        
        # 如果在映射表中找到，直接返回映射值
        if chinese_name in conversion_map:
            return conversion_map[chinese_name]
        
        # 如果不在映射表中，可以使用拼音转换或其他方式
        # 这里简化处理，实际项目中可能需要集成pypinyin等库
        import re
        # 移除中文字符，保留英文字母和数字
        english_name = re.sub(r'[^\w]', '_', chinese_name)
        return english_name.lower() or "unknown"

    def translate_name(self, param: str) -> str:
        """使用翻译器进行翻译"""
        return self.translator.translate("Name", param)

    def extract_from_file(self, file_path: Path) -> pd.DataFrame:
        """从单个 Excel 文件提取对话，返回 DataFrame"""
        logger.info(f"正在处理：{file_path.name}")
        try:
            excel_data = self.excel_manager.load_excel(file_path)
        except (ExcelFileNotFoundError, ExcelFormatError) as e:
            logger.error(f"跳过文件 {file_path.name}: {e}")
            return pd.DataFrame()

        # 第一阶段：提取所有有效行并统计每个角色在各工作表中的出现次数
        temp_count = {}
        valid_data_cache = {}  # 缓存每个工作表的有效行数据
        
        for sheet_name, df in excel_data.items():
            if sheet_name == SheetName.PARAM_SHEET.value:
                continue

            # 提取有效行（只调用一次）
            valid_df = self.df_processor.extract_valid_rows(df, sheet_name)
            if valid_df.empty:
                continue
            
            # 缓存有效行数据供后续使用
            valid_data_cache[sheet_name] = valid_df

            # 统计每个角色的出现次数
            for idx, row in valid_df.iterrows():
                ignore = row.get(ColumnName.IGNORE.value, "")
                if pd.isna(ignore) or ignore in self.ignore_word:
                    continue
                speaker = row.get(ColumnName.NAME.value, "")
                if pd.isna(speaker) or speaker == "":
                    continue
                
                if speaker not in temp_count:
                    temp_count[speaker] = {}
                if sheet_name not in temp_count[speaker]:
                    temp_count[speaker][sheet_name] = 0
                temp_count[speaker][sheet_name] += 1

        # 预生成所有语音文件名
        filename_generators = {}
        for speaker, sheets in temp_count.items():
            filename_generators[speaker] = {}
            # 转换角色名为英文（只转换一次）
            if not self.use_cache_map:
                converted_speaker = self.translate_name(speaker)
            else:
                converted_speaker = self._convert_chinese_to_english(speaker)
            
            for sheet_name, count in sheets.items():
                # 为每个角色 - 工作表组合创建编号迭代器
                filename_generators[speaker][sheet_name] = iter(range(1, count + 1))

        # 第二阶段：使用缓存的数据生成最终结果
        all_rows = []
        for sheet_name, valid_df in valid_data_cache.items():
            if valid_df.empty:
                continue

            for idx, row in valid_df.iterrows():
                # 提取角色和文本
                ignore = row.get(ColumnName.IGNORE.value, "")
                if pd.isna(ignore) or ignore in self.ignore_word:
                    continue
                speaker = row.get(ColumnName.NAME.value, "")
                if pd.isna(speaker) or speaker == "" or speaker in SPECIAL_NAME_VALUES:
                    continue
                text = row.get(ColumnName.TEXT.value, "")
                if pd.isna(text) or text == "":
                    continue
                index = row.get(ColumnName.INDEX.value, "")

                # 使用预生成的编号和已转换的角色名
                next_num = next(filename_generators[speaker][sheet_name])
                count_num = f"{next_num:03d}"
                
                # 获取已转换的角色名（通过缓存避免重复转换）
                cache_key = (speaker, sheet_name, idx)
                if cache_key not in self.voice_filename_cache:
                    converted_speaker = self._convert_chinese_to_english(speaker)
                    self.voice_filename_cache[cache_key] = f"{converted_speaker}_{sheet_name}_{count_num}"
                
                voice_file_name = self.voice_filename_cache[cache_key]

                all_rows.append({
                    "Filename": file_path.stem,
                    "Sheet": sheet_name,
                    "Index": index,
                    "Idx": idx + 2,
                    "Voice": voice_file_name,
                    "Name": str(speaker).strip(),
                    "Text": str(text).strip()
                })

        df_result = pd.DataFrame(all_rows)
        logger.info(f"  提取到 {len(df_result)} 条对话")
        return df_result

    def export(self):
        """执行导出"""
        # 获取所有Excel文件
        excel_files = list(self.input_dir.glob("*.xlsx")) + list(self.input_dir.glob("*.xls"))
        excel_files = [f for f in excel_files if not f.name.startswith("~")]

        if not excel_files:
            logger.warning(f"在 {self.input_dir} 中没有找到Excel文件")
            return

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 按角色分别导出
        if self.per_character:
            # 合并所有文件的数据
            all_dfs = []
            for f in excel_files:
                df = self.extract_from_file(f)
                if not df.empty:
                    all_dfs.append(df)
            if not all_dfs:
                logger.warning("没有提取到任何对话")
                return
            combined_df = pd.concat(all_dfs, ignore_index=True)
            combined_df = combined_df.sort_values(by=self.sort_by)

            # 按角色分组
            for role, group_df in combined_df.groupby("Name"):
                # 如果指定了角色列表且当前角色不在其中，则跳过
                if self.selected_characters and role not in self.selected_characters:
                    continue

                # 生成安全的文件名（避免非法字符）
                safe_role = self._sanitize_filename(role)
                base_path = self.output_dir / f"dialogue_{safe_role}"
                self._save_dataframe(group_df, base_path)

            logger.info("所有角色导出完成")
            return

        if self.merge_files:
            # 合并所有文件到一个DataFrame
            all_dfs = []
            for f in excel_files:
                df = self.extract_from_file(f)
                if not df.empty:
                    all_dfs.append(df)
            if not all_dfs:
                logger.warning("没有提取到任何对话")
                return
            combined_df = pd.concat(all_dfs, ignore_index=True)
            combined_df = combined_df.sort_values(by=self.sort_by)
            self._save_dataframe(combined_df, self.output_dir / "all_dialogues")
        else:
            # 每个文件单独导出
            for f in excel_files:
                df = self.extract_from_file(f)
                if df.empty:
                    continue
                df = df.sort_values(by=self.sort_by)
                base_name = f.stem + "_配音台本"
                self._save_dataframe(df, self.output_dir / base_name)

    # 各列预设宽度（可根据实际需要调整）
    COLUMN_WIDTHS = {
        "Filename": 20,
        "Sheet": 12,
        "Index": 10,
        "Idx": 8,
        "Voice": 30,
        "Name": 14,
        "Text": 60,
    }

    def _save_dataframe(self, df: pd.DataFrame, base_path: Path):
        """保存DataFrame为指定格式"""
        if self.output_format == "excel":
            output_path = base_path.with_suffix(".xlsx")
            with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Sheet1")
                ws = writer.sheets["Sheet1"]

                # 设置列宽和居中对齐
                center_align = Alignment(horizontal="center", vertical="center")
                for col_idx, col_name in enumerate(df.columns, start=1):
                    col_letter = get_column_letter(col_idx)

                    # 列宽：优先使用预设宽度，否则根据内容自适应
                    if col_name in self.COLUMN_WIDTHS:
                        ws.column_dimensions[col_letter].width = self.COLUMN_WIDTHS[col_name]
                    else:
                        # 自适应宽度：取列名和内容最大长度 + 2
                        max_len = max(
                            df[col_name].astype(str).map(len, na_action="ignore").max(),
                            len(str(col_name))
                        )
                        ws.column_dimensions[col_letter].width = min(max_len + 2, 80)

                    # 对所有单元格（包括表头）设置居中
                    for row in ws.iter_rows(
                        min_col=col_idx, max_col=col_idx,
                        min_row=1, max_row=ws.max_row
                    ):
                        for cell in row:
                            cell.alignment = center_align

        elif self.output_format == "csv":
            output_path = base_path.with_suffix(".csv")
            df.to_csv(output_path, index=False, encoding="utf-8-sig")
        else:
            logger.error(f"不支持的输出格式: {self.output_format}")
            return
        logger.info(f"已导出 {len(df)} 行到 {output_path}")


    def _sanitize_filename(self, name: str) -> str:
        """将角色名转换为安全的文件名（只保留字母、数字、下划线、连字符）"""
        # 可以先用翻译器转换成英文（如果有映射）
        translated = self.translate_name(name)
        # 移除非法的文件名字符
        safe = re.sub(r'[^\w\-_]', '_', translated)
        return safe or "unknown"

    def convert_to_performance_format(
        self,
        dialogue_df: pd.DataFrame,
        include_voice_prefix: bool = True,
        include_index: bool = True
    ) -> pd.DataFrame:
        """
        将配音台本 DataFrame 转换为演出脚本生成器可识别的格式
        
        Args:
            dialogue_df: 配音台本的 DataFrame（包含列：角色、文本、语音文件名、文本行号）
            include_voice_prefix: 是否在文本前添加语音文件名前缀
            include_index: 是否包含 Index 列
            
        Returns:
            转换后的 DataFrame，包含列：Name、Text、Voice、Index（可选）
        """
        if dialogue_df.empty:
            return dialogue_df
        
        result_rows = []
        
        for idx, row in dialogue_df.iterrows():
            speaker = row.get("Name", "")
            text = row.get("Text", "")
            voice_file = row.get("Voice", "")
            line_index = row.get("Index", "")
            
            # 构建新的文本（如果需要添加语音文件名和行号前缀）
            new_text = text
            if include_voice_prefix and voice_file:
                # 格式：[语音文件名][行号] 文本
                if include_index and line_index:
                    new_text = f"[{voice_file}][{line_index}] {text}"
                else:
                    new_text = f"[{voice_file}] {text}"
            elif include_index and line_index:
                new_text = f"[{line_index}] {text}"
            
            # 构建新行
            new_row = {
                ColumnName.NAME.value: speaker,
                ColumnName.TEXT.value: new_text,
                ColumnName.VOICE.value: voice_file,
            }
            
            # 添加 Index 列（用于追踪定位）
            if include_index:
                new_row[ColumnName.INDEX.value] = line_index
            
            result_rows.append(new_row)
        
        return pd.DataFrame(result_rows)


def convert_dialogue_to_performance(
    input_path: Path,
    output_path: Optional[Path] = None,
    include_voice_prefix: bool = True,
    include_index: bool = True,
    output_format: str = "excel"
):
    """
    快速转换函数：读取配音台本文件并转换为演出脚本格式
    
    Args:
        input_path: 输入的配音台本文件路径
        output_path: 输出路径（如果为 None，则在输入文件同目录下生成）
        include_voice_prefix: 是否在文本前添加语音文件名
        include_index: 是否包含 Index 列
        output_format: 输出格式 "excel" 或 "csv"
    """
    logger.info(f"开始转换配音台本：{input_path.name}")
    
    # 读取配音台本
    if input_path.suffix == ".xlsx":
        df = pd.read_excel(input_path)
    else:
        df = pd.read_csv(input_path, encoding="utf-8-sig")
    
    # 检查必需的列
    required_cols = ["Name", "Text", "Voice"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        logger.error(f"缺少必需的列：{missing_cols}")
        logger.error(f"当前列：{list(df.columns)}")
        raise ValueError(f"配音台本格式不正确，缺少必需的列：{missing_cols}")
    
    # 创建导出器实例（使用默认配置）
    config_path = Path("config.yaml")
    if config_path.exists():
        config = AppConfig.from_file(config_path)
    else:
        config = AppConfig.create_default("naninovel")
    
    exporter = DialogueExporter(config=config)
    
    # 转换为演出脚本格式
    performance_df = exporter.convert_to_performance_format(
        df,
        include_voice_prefix=include_voice_prefix,
        include_index=include_index
    )
    
    # 确定输出路径
    if output_path is None:
        output_dir = input_path.parent
        base_name = input_path.stem.replace("配音台本", "演出脚本")
        if output_format.lower() == "excel":
            output_path = output_dir / f"{base_name}.xlsx"
        else:
            output_path = output_dir / f"{base_name}.csv"
    
    # 保存结果
    logger.info(f"转换完成，共 {len(performance_df)} 条记录")
    
    if output_format.lower() == "excel":
        performance_df.to_excel(output_path, index=False)
    else:
        performance_df.to_csv(output_path, index=False, encoding="utf-8-sig")
    
    logger.info(f"已保存到：{output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="导出配音台本工具")
    parser.add_argument("--input", type=Path, help="输入目录（覆盖配置中的 input_dir）")
    parser.add_argument("--output", type=Path, help="输出目录（覆盖配置中的 output_dir）")
    parser.add_argument("--sort", nargs="+", default=["角色", "文本行号"],
                        help="排序字段，例如 --sort 角色 行号")
    parser.add_argument("--default-speaker", default="", help="角色为空时的默认名称")
    parser.add_argument("--merge", action="store_true", help="合并所有文件为一个表格")
    parser.add_argument("--format", choices=["excel", "csv"], default="excel",
                        help="输出格式 (默认：excel)")
    parser.add_argument("--per-character", action="store_true",
                    help="按角色分别导出为单独的文件（自动合并所有输入文件）")
    
    # 新增：转换模式参数
    parser.add_argument("--convert", type=Path,
                        help="将配音台本转换为演出脚本格式（指定配音台本文件路径）")
    parser.add_argument("--no-voice-prefix", action="store_true",
                        help="不在文本前添加语音文件名前缀")
    parser.add_argument("--no-index", action="store_true",
                        help="不添加 Index 列和行号前缀")
    
    args = parser.parse_args()

    # 如果是转换模式
    if args.convert:
        convert_dialogue_to_performance(
            input_path=args.convert,
            include_voice_prefix=not args.no_voice_prefix,
            include_index=not args.no_index
        )
        return

    # 加载配置
    config_path = Path("config.yaml")
    if config_path.exists():
        config = AppConfig.from_file(config_path)
    else:
        logger.warning("config.yaml 不存在，使用默认配置")
        config = AppConfig.create_default("naninovel")  # 引擎类型不影响导出

    exporter = DialogueExporter(
        config=config,
        input_dir=args.input,
        output_dir=args.output,
        default_speaker=args.default_speaker,
        sort_by=args.sort,
        merge_files=args.merge,
        output_format=args.format,
        selected_characters=getattr(args, 'characters', None),
        per_character=args.per_character,
    )
    exporter.export()


if __name__ == "__main__":
    main()