"""通用表格变更工具。"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config_manager import AppConfig
from core.logger import get_logger
from core.table_transform import TableTransformEngine, summarize_results


logger = get_logger()


TOOL_UI = {
    "title": "通用表格变更",
    "description": "按照 YAML 规则预览或执行演出表格的批量变更。",
    "arguments": {
        "config": {"label": "规则文件", "group": "输入", "kind": "file", "file_filter": "YAML 文件 (*.yaml *.yml)", "order": 10},
        "input_dir": {"label": "输入目录", "group": "输入", "kind": "directory", "order": 20},
        "sheets": {"label": "限定工作表", "group": "处理范围", "placeholder": "多个名称使用逗号分隔", "order": 30},
        "dry_run": {"label": "安全预览", "group": "执行模式", "order": 40},
        "apply": {"label": "实际执行", "group": "执行模式", "order": 41},
        "report": {"label": "报告文件", "group": "输出", "kind": "save_file", "file_filter": "JSON 文件 (*.json)", "order": 50},
        "no_report": {"label": "不生成报告", "group": "输出", "order": 60},
        "verbose": {"label": "显示详细变更", "group": "高级参数", "order": 90},
    },
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="通用表格变更工具 - 根据 YAML 操作配置生成并应用单元格变更计划"
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        default=Path("config/filling_rules.yaml"),
        help="操作配置文件（默认：config/filling_rules.yaml）",
    )
    parser.add_argument(
        "--input-dir",
        "-i",
        type=Path,
        help="输入目录（默认使用 config.yaml 中的 input_dir）",
    )
    parser.add_argument(
        "--sheets",
        "-s",
        help="只处理指定工作表，多个名称使用逗号分隔",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", "-d", action="store_true", help="只生成变更计划，不写入 Excel")
    mode.add_argument(
        "--apply",
        action="store_true",
        help="显式执行写入；不带 --dry-run 时本来就会写入，用于命令可读性",
    )
    parser.add_argument("--report", type=Path, help="JSON 变更报告路径")
    parser.add_argument("--no-report", action="store_true", help="不生成 JSON 变更报告")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示每个计划变更")
    return parser


def default_report_path(dry_run: bool) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    mode = "preview" if dry_run else "apply"
    return PROJECT_ROOT / "logs" / "table_transform" / f"{timestamp}-{mode}.json"


def write_report(path: Path, config_path: Path, dry_run: bool, results) -> None:
    summary = summarize_results(results)
    payload = {
        "config": str(config_path.resolve()),
        "mode": "dry-run" if dry_run else "apply",
        "summary": summary,
        "results": [result.to_dict() for result in results],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    dry_run = args.dry_run

    try:
        app_config_path = PROJECT_ROOT / "config.yaml"
        app_config = (
            AppConfig.from_file(app_config_path)
            if app_config_path.exists()
            else AppConfig.create_default("naninovel")
        )
        input_dir = args.input_dir or app_config.paths.input_dir
        if not input_dir.is_absolute():
            input_dir = PROJECT_ROOT / input_dir
        config_path = args.config
        if not config_path.is_absolute():
            config_path = PROJECT_ROOT / config_path
        sheet_names = (
            [name.strip() for name in args.sheets.split(",") if name.strip()]
            if args.sheets
            else None
        )

        engine = TableTransformEngine.from_config(config_path)
        results = engine.process_directory(
            input_dir=input_dir,
            dry_run=dry_run,
            sheet_names=sheet_names,
        )
        summary = summarize_results(results)

        for result in results:
            if not result.success:
                logger.error(f"表格处理失败: {result.file_path.name} - {result.error}")
            elif result.plan.changes:
                action = "计划修改" if dry_run else "已修改"
                logger.info(f"{action}: {result.file_path.name} ({len(result.plan.changes)} 处)")
                if args.verbose:
                    for change in result.plan.changes:
                        logger.info(
                            f"  {change.sheet}!{change.column}{change.row}: "
                            f"{change.original_value!r} -> {change.new_value!r} [{change.operation}]"
                        )
            else:
                logger.info(f"无变化: {result.file_path.name}")

        report_path = args.report
        if not args.no_report:
            report_path = report_path or default_report_path(dry_run)
            if not report_path.is_absolute():
                report_path = PROJECT_ROOT / report_path
            write_report(report_path, config_path, dry_run, results)
            logger.info(f"变更报告: {report_path.resolve()}")

        logger.info(
            "处理完成: "
            f"文件 {summary['files']}, 成功 {summary['success']}, "
            f"失败 {summary['failed']}, 变更 {summary['changes']}"
        )
        if summary["files"] == 0:
            logger.warning(f"输入目录中没有可处理的 Excel 文件: {input_dir}")
            return 1
        return 0 if summary["failed"] == 0 else 1
    except KeyboardInterrupt:
        logger.warning("用户中断操作")
        return 130
    except Exception as exc:
        logger.critical(f"表格变更失败: {exc}", exc_info=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
