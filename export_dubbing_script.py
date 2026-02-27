"""
导出配音台本工具
从 Excel 剧本中提取所有对话，按角色整合并输出表格
"""
import argparse
from pathlib import Path
from typing import List, Optional
import pandas as pd

from core.config_manager import AppConfig
from core.logger import get_logger
from core.excel_management.excel_file_manager import ExcelFileManager, ExcelFileNotFoundError, ExcelFormatError
from core.excel_management.dataframe_processor import DataFrameProcessor
from core.constants import ColumnName, SheetName

logger = get_logger(__name__)


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
        output_format: str = "excel"
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
        self.merge_files = merge_files
        self.output_format = output_format.lower()

        self.count_dict = {}  # 用于统计每个角色在每个工作表中的对话数量
        self.voice_filename_cache = {}  # 缓存完整的语音文件名，键为(speaker, sheet_name)元组

        self.excel_manager = ExcelFileManager(cache_enabled=True)
        self.df_processor = DataFrameProcessor(config)

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

    def extract_from_file(self, file_path: Path) -> pd.DataFrame:
        """从单个Excel文件提取对话，返回DataFrame"""
        logger.info(f"正在处理: {file_path.name}")
        try:
            excel_data = self.excel_manager.load_excel(file_path)
        except (ExcelFileNotFoundError, ExcelFormatError) as e:
            logger.error(f"跳过文件 {file_path.name}: {e}")
            return pd.DataFrame()

        # 预处理阶段：统计每个角色在各工作表中的出现次数
        temp_count = {}
        for sheet_name, df in excel_data.items():
            if sheet_name == SheetName.PARAM_SHEET.value:
                continue

            valid_df = self.df_processor.extract_valid_rows(df, sheet_name)
            if valid_df.empty:
                continue

            for idx, row in valid_df.iterrows():
                # 提取角色信息
                ignore = row.get(ColumnName.IGNORE.value, "")
                if pd.isna(ignore) or ignore in self.ignore_word:
                    continue
                speaker = row.get(ColumnName.NAME.value, "")
                if pd.isna(speaker) or speaker == "":
                    continue
                
                # 统计出现次数
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
            converted_speaker = self._convert_chinese_to_english(speaker)
            
            for sheet_name, count in sheets.items():
                # 为每个角色-工作表组合创建编号迭代器
                filename_generators[speaker][sheet_name] = iter(range(1, count + 1))

        all_rows = []
        for sheet_name, df in excel_data.items():
            if sheet_name == SheetName.PARAM_SHEET.value:
                continue

            valid_df = self.df_processor.extract_valid_rows(df, sheet_name)
            if valid_df.empty:
                continue

            for idx, row in valid_df.iterrows():
                # 提取角色和文本
                ignore = row.get(ColumnName.IGNORE.value, "")
                if pd.isna(ignore) or ignore in self.ignore_word:
                    continue
                speaker = row.get(ColumnName.NAME.value, "")
                if pd.isna(speaker) or speaker == "":
                    speaker = self.default_speaker
                text = row.get(ColumnName.TEXT.value, "")
                if pd.isna(text) or text == "":
                    continue
                index = row.get(ColumnName.INDEX.value, "")

                # 使用预生成的编号和已转换的角色名
                next_num = next(filename_generators[speaker][sheet_name])
                count_num = f"{next_num:03d}"
                
                # 获取已转换的角色名（通过缓存避免重复转换）
                cache_key = (speaker, sheet_name)
                if cache_key not in self.voice_filename_cache:
                    converted_speaker = self._convert_chinese_to_english(speaker)
                    self.voice_filename_cache[cache_key] = f"{converted_speaker}_{sheet_name}_{count_num}"
                
                voice_file_name = self.voice_filename_cache[cache_key]

                all_rows.append({
                    "Excel文件名": file_path.stem,
                    "工作表名": sheet_name,
                    "文本行号": index,
                    "行号": idx + 2,
                    "语音文件名": voice_file_name,
                    "角色": str(speaker).strip(),
                    "文本": str(text).strip()
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
                base_name = f.stem
                self._save_dataframe(df, self.output_dir / base_name)

    def _save_dataframe(self, df: pd.DataFrame, base_path: Path):
        """保存DataFrame为指定格式"""
        if self.output_format == "excel":
            output_path = base_path.with_suffix(".xlsx")
            df.to_excel(output_path, index=False)
        elif self.output_format == "csv":
            output_path = base_path.with_suffix(".csv")
            df.to_csv(output_path, index=False, encoding="utf-8-sig")
        else:
            logger.error(f"不支持的输出格式: {self.output_format}")
            return
        logger.info(f"已导出 {len(df)} 行到 {output_path}")


def main():
    parser = argparse.ArgumentParser(description="导出配音台本工具")
    parser.add_argument("--input", type=Path, help="输入目录（覆盖配置中的input_dir）")
    parser.add_argument("--output", type=Path, help="输出目录（覆盖配置中的output_dir）")
    parser.add_argument("--sort", nargs="+", default=["角色", "文本行号"],
                        help="排序字段，例如 --sort 角色 行号")
    parser.add_argument("--default-speaker", default="旁白", help="角色为空时的默认名称")
    parser.add_argument("--merge", action="store_true", help="合并所有文件为一个表格")
    parser.add_argument("--format", choices=["excel", "csv"], default="excel",
                        help="输出格式 (默认: excel)")
    args = parser.parse_args()

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
        output_format=args.format
    )
    exporter.export()


if __name__ == "__main__":
    main()