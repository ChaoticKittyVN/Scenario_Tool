"""Update parameter mappings and synchronize scenario workbook parameter sheets."""

import argparse
from pathlib import Path

from core.config_manager import AppConfig, _create_engine_config
from core.logger import get_logger
from core.engine_loader import discover_engine_names
from core.param_update import ParamUpdater


logger = get_logger()

__all__ = ["ParamUpdater", "parse_args", "main"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="更新参数映射并同步演出表格的参数表。")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径。")
    parser.add_argument(
        "--engine",
        choices=discover_engine_names(),
        help="覆盖 config.yaml 中的 engine_type。",
    )
    parser.add_argument(
        "--workbook",
        action="append",
        help="只同步指定演出工作簿的参数表，可重复指定。省略时处理配置中的 input_dir。",
    )
    execution_mode = parser.add_mutually_exclusive_group()
    execution_mode.add_argument(
        "--dry-run",
        action="store_true",
        help="只读取并报告将执行的操作，不写入映射文件或 Excel。",
    )
    execution_mode.add_argument(
        "--apply",
        action="store_true",
        help="显式执行写入；不带 --dry-run 时本来就会执行，用于提高命令可读性。",
    )
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument(
        "--mappings-only",
        action="store_true",
        help="只生成 param_mappings.py 和 variant_mappings.py，不更新演出表格。",
    )
    scope.add_argument(
        "--parameter-sheet-only",
        action="store_true",
        help="只从 param_data/variant_data 同步参数表，不重新生成映射模块。",
    )
    scope.add_argument(
        "--variant-mappings-only",
        action="store_true",
        help="只从 variant_data.xlsx 生成普通 variant_mappings.py。",
    )
    scope.add_argument(
        "--agent-variant-doc-only",
        action="store_true",
        help="只从 variant_data.xlsx 生成供 Agent 使用的差分 JSON 文档。",
    )
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        config_path = Path(args.config)
        if not config_path.exists():
            logger.error(f"配置文件不存在: {config_path}")
            return 2

        config = AppConfig.from_file(config_path)
        if args.engine:
            if config.engines.enabled and args.engine not in config.engines.enabled:
                logger.error(
                    f"引擎 '{args.engine}' 未包含在 engines.enabled 中: "
                    f"{', '.join(config.engines.enabled)}"
                )
                return 2
            config.engine = _create_engine_config(args.engine)

        workbooks = (
            [Path(path).resolve() for path in args.workbook]
            if args.workbook
            else None
        )
        updater = ParamUpdater(config)
        if args.variant_mappings_only:
            success, _ = updater.generate_variant_mappings(args.dry_run)
        elif args.agent_variant_doc_only:
            success = updater.export_agent_variant_document(args.dry_run)
        else:
            generate_mapping_files = not args.parameter_sheet_only
            update_parameter_sheets = not args.mappings_only
            success = updater.update_mappings(
                workbooks,
                generate_mapping_files=generate_mapping_files,
                update_parameter_sheets=update_parameter_sheets,
                dry_run=args.dry_run,
            )
        if (args.mappings_only or args.variant_mappings_only or args.agent_variant_doc_only) and workbooks:
            logger.warning("当前模式不会使用 --workbook 参数")
        if success:
            return 0
        logger.error("参数映射更新失败")
        return 1
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        return 130
    except Exception as exc:
        logger.critical(f"参数更新过程失败: {exc}", exc_info=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
