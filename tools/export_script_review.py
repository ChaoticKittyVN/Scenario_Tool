"""
剧本审查文本导出工具
从演出表格中提取 Index、Name、Text 列，输出为 txt 文件供 AI 进行剧本文本问题筛查
"""
import argparse
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from core.logger import get_logger
from core.excel_management.excel_file_manager import ExcelFileManager
from core.constants import ColumnName, SheetName, TEMP_FILE_PREFIX

logger = get_logger(__name__)


class ScriptReviewExporter:
    """剧本审查文本导出器"""

    def __init__(self, input_dir: Optional[Path] = None, output_dir: Optional[Path] = None):
        """
        Args:
            input_dir: 演出表格输入目录（默认 ./input）
            output_dir: txt 输出目录（默认 ./output/script_review）
        """
        self.input_dir = Path(input_dir) if input_dir else Path("./input")
        self.output_dir = Path(output_dir) if output_dir else Path("./output/script_review")
        self.excel_manager = ExcelFileManager(cache_enabled=True)

    def export(self):
        """执行导出"""
        if not self.input_dir.exists():
            logger.error(f"输入目录不存在：{self.input_dir}")
            print(f"错误：输入目录不存在 - {self.input_dir}")
            return

        excel_files = [
            f for f in self.input_dir.iterdir()
            if f.suffix in ['.xlsx', '.xls'] and not f.name.startswith(TEMP_FILE_PREFIX)
        ]

        if not excel_files:
            logger.warning(f"在 {self.input_dir} 中没有找到 Excel 文件")
            print(f"警告：在 {self.input_dir} 中没有找到 Excel 文件")
            return

        self.output_dir.mkdir(parents=True, exist_ok=True)

        total_files = 0
        total_sheets = 0
        total_lines = 0

        for file_path in sorted(excel_files):
            logger.info(f"处理文件：{file_path.name}")

            try:
                excel_data = self.excel_manager.load_excel(file_path)
            except Exception as e:
                logger.error(f"加载文件失败 {file_path.name}: {e}")
                continue

            for sheet_name, df in excel_data.items():
                # 跳过参数表
                if sheet_name == SheetName.PARAM_SHEET.value:
                    continue

                if df.empty:
                    continue

                lines = self._extract_lines(df, sheet_name, file_path)
                if not lines:
                    continue

                # 输出文件名：{Excel文件名}_{工作表名}.txt
                safe_sheet = self._sanitize_filename(sheet_name)
                output_path = self.output_dir / f"{file_path.stem}_{safe_sheet}.txt"

                output_path.write_text("\n".join(lines), encoding="utf-8")

                logger.info(f"  导出 {sheet_name}: {len(lines)} 行 -> {output_path.name}")
                total_sheets += 1
                total_lines += len(lines)

            total_files += 1

        print(f"\n导出完成：{total_files} 个文件，{total_sheets} 个工作表，{total_lines} 行文本")
        print(f"输出目录：{self.output_dir.resolve()}")

    def _extract_lines(self, df: pd.DataFrame, sheet_name: str, file_path: Path) -> list:
        """
        从 DataFrame 中提取文本行

        Args:
            df: 工作表 DataFrame
            sheet_name: 工作表名称
            file_path: 源文件路径

        Returns:
            list: 格式化后的文本行列表
        """
        # 查找实际列名
        index_col = self._find_column(df, [ColumnName.INDEX.value, "Idx", "idx"])
        name_col = self._find_column(df, [ColumnName.NAME.value, "说话人", "角色", "name", "speaker", "character"])
        text_col = self._find_column(df, [ColumnName.TEXT.value, "台词", "对话", "text", "dialogue"])

        if not text_col:
            logger.debug(f"工作表 {sheet_name} 没有 Text 列，跳过")
            return []

        lines = []

        for idx in range(len(df)):
            text_val = df.at[idx, text_col]
            if pd.isna(text_val) or str(text_val).strip() == "":
                continue

            text = str(text_val).strip()

            # 获取 Index
            index_val = ""
            if index_col:
                val = df.at[idx, index_col]
                if not pd.isna(val) and str(val).strip() != "":
                    index_val = str(val).strip()

            # 获取 Name
            name_val = ""
            if name_col:
                val = df.at[idx, name_col]
                if not pd.isna(val) and str(val).strip() != "":
                    name_val = str(val).strip()

            # 格式化输出
            if name_val:
                line = f"index:{index_val} {name_val}：{text}"
            else:
                line = f"index:{index_val} {text}"

            lines.append(line)

        return lines

    def _find_column(self, df: pd.DataFrame, candidates: list) -> Optional[str]:
        """在 DataFrame 中查找第一个匹配的列名"""
        for col in candidates:
            if col in df.columns:
                return col
        return None

    def _sanitize_filename(self, name: str) -> str:
        """将工作表名转换为安全的文件名"""
        import re
        safe = re.sub(r'[\\/:*?"<>|]', '_', name)
        return safe


def main():
    parser = argparse.ArgumentParser(
        description="剧本审查文本导出工具 - 从演出表格提取文本供 AI 审查",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 基本用法（默认读取 ./input，输出到 ./output/script_review）
  python export_script_review.py

  # 指定输入目录
  python export_script_review.py --input ./scenario

  # 指定输出目录
  python export_script_review.py --output ./my_review
        """
    )

    parser.add_argument("--input", "-i", type=Path, default=Path("./input"),
                        help="演出表格输入目录（默认：./input）")
    parser.add_argument("--output", "-o", type=Path, default=Path("./output/script_review"),
                        help="txt 输出目录（默认：./output/script_review）")

    args = parser.parse_args()

    exporter = ScriptReviewExporter(
        input_dir=args.input,
        output_dir=args.output,
    )
    exporter.export()


if __name__ == "__main__":
    main()
