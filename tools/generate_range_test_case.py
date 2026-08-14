"""从演出表格的一个或多个 Excel 行范围生成独立测试片段。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Optional

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config_manager import AppConfig
from core.scenario_test_case import (
    RANGE_MODES,
    RANGE_MODE_WARMUP,
    ScenarioRangeCase,
    ScenarioTestCaseGenerator,
)


def parse_range(value: str) -> tuple[str, int, int, Optional[int]]:
    """Parse SHEET:START-END or SHEET:START-END@CONTEXT_START."""
    try:
        sheet, row_part = value.rsplit(":", 1)
        range_part, separator, context_part = row_part.partition("@")
        start_text, end_text = range_part.split("-", 1)
        context_start = int(context_part) if separator else None
        return sheet, int(start_text), int(end_text), context_start
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError(
            "范围格式应为 工作表:起始行-结束行，或 工作表:起始行-结束行@上下文起始行"
        ) from exc


def _case_from_mapping(data: dict[str, Any]) -> ScenarioRangeCase:
    rows = str(data.get("rows", ""))
    try:
        start_text, end_text = rows.split("-", 1)
        start_row = int(start_text)
        end_row = int(end_text)
    except ValueError as exc:
        raise ValueError(f"测试用例 rows 格式无效: {rows!r}") from exc

    label_value = data.get("label")
    label = str(label_value) if label_value not in (None, False, "") else None
    return ScenarioRangeCase(
        name=str(data["name"]) if data.get("name") else None,
        sheet=str(data.get("sheet", "")),
        start_row=start_row,
        end_row=end_row,
        context_start=(
            int(data["context_start"])
            if data.get("context_start") is not None
            else None
        ),
        label=label,
        mode=str(data.get("mode", RANGE_MODE_WARMUP)),
        replay_start=(
            int(data["replay_start"])
            if data.get("replay_start") is not None
            else None
        ),
    )


def load_plan(path: Path) -> tuple[Path, Optional[Path], list[ScenarioRangeCase]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("计划文件根节点必须是映射")
    if not data.get("input"):
        raise ValueError("计划文件缺少 input")
    raw_cases = data.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("计划文件 cases 必须是非空列表")
    if not all(isinstance(item, dict) for item in raw_cases):
        raise ValueError("计划文件中的每个 case 必须是映射")

    cases = [_case_from_mapping(item) for item in raw_cases]
    return (
        Path(data["input"]),
        Path(data["output_dir"]) if data.get("output_dir") else None,
        cases,
    )


def build_cli_cases(
    ranges: list[tuple[str, int, int, Optional[int]]],
    with_label: bool,
    label_prefix: str,
    mode: str = RANGE_MODE_WARMUP,
    replay_start: Optional[int] = None,
) -> list[ScenarioRangeCase]:
    cases = []
    for number, (sheet, start_row, end_row, context_start) in enumerate(ranges, 1):
        cases.append(
            ScenarioRangeCase(
                sheet=sheet,
                start_row=start_row,
                end_row=end_row,
                context_start=context_start,
                label=f"{label_prefix}{number:02d}" if with_label else None,
                mode=mode,
                replay_start=replay_start,
            )
        )
    return cases


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="单个演出表格")
    source.add_argument("--plan", type=Path, help="YAML 批量测试计划")
    parser.add_argument(
        "--range",
        dest="ranges",
        action="append",
        type=parse_range,
        help="工作表:起始行-结束行；可追加 @上下文起始行，可重复使用",
    )
    parser.add_argument("--output-dir", type=Path, help="输出目录")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument(
        "--mode",
        choices=sorted(RANGE_MODES),
        default=RANGE_MODE_WARMUP,
        help="范围执行模式（默认：warmup）",
    )
    parser.add_argument(
        "--replay-start",
        type=int,
        help="状态回放起始 Excel 行；warmup/context/prefix 默认从第 2 行回放",
    )
    parser.add_argument(
        "--with-label",
        action="store_true",
        help="为命令行指定的范围自动生成 Test01、Test02 等测试标签",
    )
    parser.add_argument(
        "--label-prefix",
        default="Test",
        help="自动标签前缀（默认：Test）",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        config = AppConfig.from_file(args.config)
        if args.plan:
            input_path, plan_output_dir, cases = load_plan(args.plan)
            output_dir = args.output_dir or plan_output_dir
        else:
            if not args.ranges:
                raise ValueError("使用 --input 时至少需要一个 --range")
            input_path = args.input
            cases = build_cli_cases(
                args.ranges,
                with_label=args.with_label,
                label_prefix=args.label_prefix,
                mode=args.mode,
                replay_start=args.replay_start,
            )
            output_dir = args.output_dir

        if not input_path.exists():
            raise ValueError(f"输入表格不存在: {input_path}")
        output_dir = output_dir or (
            Path(config.paths.output_dir) / "test_cases" / input_path.stem
        )

        manifest = ScenarioTestCaseGenerator(config).generate(
            input_path,
            cases,
            output_dir,
        )
    except (OSError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"生成失败：{exc}", file=sys.stderr)
        return 1

    for case in manifest["cases"]:
        status = "成功" if case["success"] else "失败"
        print(
            f"[{status}] {case['name']}: {case['sheet']} "
            f"{case['mode']} R{case['target_start']}-R{case['target_end']} -> "
            f"{case['output_file'] or '未输出'}"
        )
        if case["skipped_rows"]:
            skipped = ", ".join(map(str, case["skipped_rows"]))
            print(f"  跳过行: {skipped}")
    print(f"清单: {manifest['manifest']}")
    return 0 if manifest["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
