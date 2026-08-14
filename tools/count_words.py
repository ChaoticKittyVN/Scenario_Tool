"""统计演出表格字数，并输出可复核的文件、工作表和角色明细。"""

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Set

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config_manager import AppConfig
from core.constants import EXCEL_EXTENSIONS, SheetName, SpecialName, TEMP_FILE_PREFIX
from core.excel_management import DataFrameProcessor, ExcelFileManager
from core.word_counter import BasicWordCounter, WordCounter, WordStyleWordCounter
from core.word_statistics import UNRECOGNIZED_SPEAKER, calculate_dataframe_word_statistics


SPECIAL_NAME_VALUES = {member.value for member in SpecialName}
COUNT_MODE_BASIC = "basic"
COUNT_MODE_WORD = "word"
COUNT_MODE_WORD_WITH_PUNCTUATION = "word-with-punctuation"
COUNT_MODE_ALL = "all"
COUNT_MODES = (
    COUNT_MODE_BASIC,
    COUNT_MODE_WORD,
    COUNT_MODE_WORD_WITH_PUNCTUATION,
    COUNT_MODE_ALL,
)
COUNT_LABELS = {
    COUNT_MODE_BASIC: "Basic 字符数",
    COUNT_MODE_WORD: "Word 字数",
    COUNT_MODE_WORD_WITH_PUNCTUATION: "Word 字数（含标点）",
}

TOOL_UI = {
    "title": "字数统计",
    "description": "直接读取一个或多个演出表格，按工作表和名称筛选后统计 Text 字数。",
    "arguments": {
        "input_files": {
            "label": "演出表格",
            "group": "输入",
            "kind": "file",
            "file_filter": "Excel 文件 (*.xlsx *.xls)",
            "order": 10,
        },
        "input_dirs": {
            "label": "批量目录",
            "group": "输入",
            "kind": "directory",
            "order": 20,
        },
        "sheets": {"label": "工作表", "group": "统计范围", "order": 30},
        "only_names": {"label": "只看名称", "group": "名称筛选", "order": 40},
        "exclude_names": {"label": "排除名称", "group": "名称筛选", "order": 50},
        "include_special_names": {
            "label": "纳入特殊名称",
            "group": "名称筛选",
            "order": 60,
        },
        "include_all_special_names": {
            "label": "纳入全部特殊名称",
            "group": "名称筛选",
            "order": 70,
        },
        "all_rows": {"label": "统计整张工作表", "group": "高级", "order": 80},
        "count_mode": {"label": "统计口径", "group": "统计范围", "order": 85},
        "output": {
            "label": "JSON 报告",
            "group": "输出",
            "kind": "save_file",
            "file_filter": "JSON 文件 (*.json)",
            "order": 90,
        },
        "config": {
            "label": "项目配置",
            "group": "高级",
            "kind": "file",
            "file_filter": "YAML 文件 (*.yaml *.yml)",
            "order": 100,
        },
        "inputs": {"hidden": True},
        "list_special_names": {"hidden": True},
    },
}


def discover_excel_files(paths: Iterable[Path]) -> List[Path]:
    """Resolve files and non-recursive directories into a stable file list."""
    files = set()
    extensions = {extension.lower() for extension in EXCEL_EXTENSIONS}
    for path in paths:
        path = path.resolve()
        if path.is_file():
            if path.suffix.lower() in extensions and not path.name.startswith(TEMP_FILE_PREFIX):
                files.add(path)
            continue
        if path.is_dir():
            files.update(
                child.resolve()
                for child in path.iterdir()
                if child.is_file()
                and child.suffix.lower() in extensions
                and not child.name.startswith(TEMP_FILE_PREFIX)
            )
    return sorted(files, key=lambda item: str(item).lower())


def _normalized_name(value) -> str:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return UNRECOGNIZED_SPEAKER
    return str(value).strip()


def filter_rows_by_name(
    dataframe: pd.DataFrame,
    only_names: Optional[Set[str]] = None,
    exclude_names: Optional[Set[str]] = None,
    include_special_names: Optional[Set[str]] = None,
    include_all_special_names: bool = False,
) -> pd.DataFrame:
    """Apply exact, case-sensitive speaker filters to a table."""
    if "Name" not in dataframe.columns:
        speakers = pd.Series([UNRECOGNIZED_SPEAKER] * len(dataframe), index=dataframe.index)
    else:
        speakers = dataframe["Name"].map(_normalized_name)

    only_names = only_names or set()
    exclude_names = exclude_names or set()
    include_special_names = include_special_names or set()

    def should_include(speaker: str) -> bool:
        if speaker in exclude_names:
            return False
        is_special = speaker in SPECIAL_NAME_VALUES
        special_is_included = include_all_special_names or speaker in include_special_names
        if is_special and not special_is_included:
            return False
        if only_names and speaker not in only_names and not (is_special and special_is_included):
            return False
        return True

    return dataframe[speakers.map(should_include)].copy()


def build_report(
    files: Iterable[Path],
    config: AppConfig,
    all_rows: bool = False,
    sheets: Optional[Iterable[str]] = None,
    only_names: Optional[Iterable[str]] = None,
    exclude_names: Optional[Iterable[str]] = None,
    include_special_names: Optional[Iterable[str]] = None,
    include_all_special_names: bool = False,
    count_mode: str = COUNT_MODE_BASIC,
) -> dict:
    manager = ExcelFileManager(cache_enabled=False)
    processor = DataFrameProcessor(config)
    selected_sheets = set(sheets or [])
    only_name_set = set(only_names or [])
    exclude_name_set = set(exclude_names or [])
    included_special_set = set(include_special_names or [])
    unknown_special_names = included_special_set - SPECIAL_NAME_VALUES
    if unknown_special_names:
        unknown = ", ".join(sorted(unknown_special_names))
        raise ValueError(f"不是已知的特殊名称: {unknown}")
    if count_mode not in COUNT_MODES:
        raise ValueError(f"不支持的统计口径: {count_mode}")

    counters: dict[str, WordCounter] = {
        COUNT_MODE_BASIC: BasicWordCounter(),
        COUNT_MODE_WORD: WordStyleWordCounter(),
        COUNT_MODE_WORD_WITH_PUNCTUATION: WordStyleWordCounter(include_punctuation=True),
    }
    selected_modes = tuple(counters) if count_mode == COUNT_MODE_ALL else (count_mode,)

    report = {
        "total": 0,
        "text_rows": 0,
        "filters": {
            "sheets": sorted(selected_sheets),
            "only_names": sorted(only_name_set),
            "exclude_names": sorted(exclude_name_set),
            "include_special_names": sorted(included_special_set),
            "include_all_special_names": include_all_special_names,
            "all_rows": all_rows,
        },
        "files": [],
    }

    for file_path in files:
        file_report = {"path": str(file_path), "total": 0, "text_rows": 0, "sheets": []}
        excel_data = manager.load_excel(file_path)

        for sheet_name, dataframe in excel_data.items():
            if sheet_name == SheetName.PARAM_SHEET.value or (
                selected_sheets and sheet_name not in selected_sheets
            ):
                continue

            counted_df = dataframe if all_rows else processor.extract_valid_rows(dataframe, sheet_name)
            counted_df = filter_rows_by_name(
                counted_df,
                only_names=only_name_set,
                exclude_names=exclude_name_set,
                include_special_names=included_special_set,
                include_all_special_names=include_all_special_names,
            )
            statistics_by_mode = {
                mode: calculate_dataframe_word_statistics(counted_df, counter=counters[mode])
                for mode in selected_modes
            }
            statistics = statistics_by_mode[selected_modes[0]]
            sheet_report = {
                "name": sheet_name,
                "total": statistics.total,
                "text_rows": statistics.text_rows,
                "by_speaker": dict(sorted(statistics.by_speaker.items())),
            }
            if count_mode == COUNT_MODE_ALL:
                sheet_report["counts"] = {
                    mode: mode_statistics.total
                    for mode, mode_statistics in statistics_by_mode.items()
                }
                all_speakers = sorted(
                    {
                        speaker
                        for mode_statistics in statistics_by_mode.values()
                        for speaker in mode_statistics.by_speaker
                    }
                )
                sheet_report["by_speaker_counts"] = {
                    speaker: {
                        mode: mode_statistics.by_speaker.get(speaker, 0)
                        for mode, mode_statistics in statistics_by_mode.items()
                    }
                    for speaker in all_speakers
                }
            file_report["sheets"].append(sheet_report)
            file_report["total"] += statistics.total
            file_report["text_rows"] += statistics.text_rows

        report["files"].append(file_report)
        report["total"] += file_report["total"]
        report["text_rows"] += file_report["text_rows"]

    if count_mode != COUNT_MODE_BASIC:
        report["count_mode"] = count_mode
    if count_mode == COUNT_MODE_ALL:
        report["counts"] = {
            mode: sum(
                sheet["counts"][mode]
                for file_report in report["files"]
                for sheet in file_report["sheets"]
            )
            for mode in selected_modes
        }
        for file_report in report["files"]:
            file_report["counts"] = {
                mode: sum(sheet["counts"][mode] for sheet in file_report["sheets"])
                for mode in selected_modes
            }

    return report


def print_report(report: dict) -> None:
    count_mode = report.get("count_mode", COUNT_MODE_BASIC)
    if count_mode == COUNT_MODE_ALL:
        _print_all_counts_report(report)
        return

    unit = "字" if count_mode == COUNT_MODE_BASIC else "词/字"
    if count_mode != COUNT_MODE_BASIC:
        print(f"统计口径: {COUNT_LABELS[count_mode]}")
    for file_report in report["files"]:
        print(f"\n{Path(file_report['path']).name}: {file_report['total']} {unit} / {file_report['text_rows']} 行")
        for sheet in file_report["sheets"]:
            print(f"  {sheet['name']}: {sheet['total']} {unit} / {sheet['text_rows']} 行")
            for speaker, count in sheet["by_speaker"].items():
                print(f"    {speaker}: {count}")
    print(f"\n合计: {report['total']} {unit} / {report['text_rows']} 行 / {len(report['files'])} 个文件")


def _format_counts(counts: dict) -> str:
    return " / ".join(f"{COUNT_LABELS[mode]}: {count}" for mode, count in counts.items())


def _print_all_counts_report(report: dict) -> None:
    print("统计口径: 全部")
    for file_report in report["files"]:
        print(
            f"\n{Path(file_report['path']).name}: "
            f"{_format_counts(file_report['counts'])} / {file_report['text_rows']} 行"
        )
        for sheet in file_report["sheets"]:
            print(
                f"  {sheet['name']}: {_format_counts(sheet['counts'])} / "
                f"{sheet['text_rows']} 行"
            )
            for speaker, counts in sheet["by_speaker_counts"].items():
                print(f"    {speaker}: {_format_counts(counts)}")
    print(
        f"\n合计: {_format_counts(report['counts'])} / "
        f"{report['text_rows']} 行 / {len(report['files'])} 个文件"
    )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        dest="input_files",
        action="append",
        type=Path,
        help="直接选择一个 Excel 文件；可重复使用",
    )
    parser.add_argument(
        "--input-dir",
        dest="input_dirs",
        action="append",
        type=Path,
        help="批量统计目录中的 Excel；可重复使用",
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        type=Path,
        help="Excel 文件或目录；省略时使用 config.yaml 中的 input_dir",
    )
    parser.add_argument("--config", type=Path, default=Path("config.yaml"), help="项目配置文件")
    parser.add_argument("--output", type=Path, help="可选的 JSON 报告输出路径")
    parser.add_argument(
        "--sheet",
        dest="sheets",
        action="append",
        help="只统计指定工作表；可重复使用",
    )
    parser.add_argument(
        "--only-name",
        dest="only_names",
        action="append",
        help="只统计指定 Name；可重复使用",
    )
    parser.add_argument(
        "--exclude-name",
        dest="exclude_names",
        action="append",
        help="排除指定 Name；优先级最高，可重复使用",
    )
    parser.add_argument(
        "--include-special-name",
        dest="include_special_names",
        action="append",
        help="纳入指定 SpecialName；可重复使用",
    )
    parser.add_argument(
        "--include-all-special-names",
        action="store_true",
        help="纳入全部 SpecialName",
    )
    parser.add_argument(
        "--list-special-names",
        action="store_true",
        help="列出可用的特殊名称后退出",
    )
    parser.add_argument(
        "--all-rows",
        action="store_true",
        help="统计整张工作表，不应用 END 和 Ignore 规则",
    )
    parser.add_argument(
        "--count-mode",
        choices=COUNT_MODES,
        default=COUNT_MODE_BASIC,
        help=(
            "统计口径：basic 保持原字符统计；word 使用 Word 风格且忽略标点；"
            "word-with-punctuation 计入标点；all 同时输出三种结果"
        ),
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.list_special_names:
        print("\n".join(sorted(SPECIAL_NAME_VALUES)))
        return 0

    config = AppConfig.from_file(args.config)
    inputs = [*(args.input_files or []), *(args.input_dirs or []), *args.inputs]
    if not inputs:
        inputs = [Path(config.paths.input_dir)]
    files = discover_excel_files(inputs)
    if not files:
        print("未找到可统计的 Excel 文件。", file=sys.stderr)
        return 1

    try:
        report = build_report(
            files,
            config,
            all_rows=args.all_rows,
            sheets=args.sheets,
            only_names=args.only_names,
            exclude_names=args.exclude_names,
            include_special_names=args.include_special_names,
            include_all_special_names=args.include_all_special_names,
            count_mode=args.count_mode,
        )
    except ValueError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    print_report(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"JSON 报告: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
