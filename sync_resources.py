"""
资源同步工具
从资源库同步缺失的资源到项目库
"""
import json
from pathlib import Path
from typing import Dict, Optional
from core.config_manager import AppConfig
from core.resource_syncer import ResourceSyncer
from core.logger import get_logger

logger = get_logger()


def load_validation_report(report_dir: Path, excel_name: str) -> Optional[Dict]:
    """
    从 JSON 文件加载验证报告

    Args:
        report_dir: 报告目录
        excel_name: Excel 文件名（不含扩展名）

    Returns:
        Dict: 验证报告数据，如果文件不存在则返回 None
    """
    json_file = report_dir / f"{excel_name}_validation.json"

    if not json_file.exists():
        return None

    try:
        with open(json_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"读取验证报告失败: {e}")
        return None


def show_sync_plan(sync_plan, resource_folders):
    """显示同步计划"""
    print("\n" + "=" * 60)
    print("资源同步计划")
    print("=" * 60)

    total_files = len(sync_plan)
    print(f"\n总计: {total_files} 个文件需要同步")

    if total_files > 0:
        print("\n文件列表:")
        print("-" * 60)
        for item in sync_plan:
            print(f"  [{item['resource_type']}] {item['resource_name']}")
            print(f"    从: {item['source_path']}")
            print(f"    到: {item['target_path']}")
            print()

    print("=" * 60)


def main():
    """主函数"""
    try:
        # 加载配置
        config_path = Path("config.yaml")
        if config_path.exists():
            config = AppConfig.from_file(config_path)
        else:
            logger.error("配置文件不存在: config.yaml")
            return

        logger.info("=" * 60)
        logger.info("资源同步工具")
        logger.info("=" * 60)

        # 检查验证报告目录
        report_dir = config.paths.output_dir / "validation_reports"
        if not report_dir.exists():
            logger.error(f"验证报告目录不存在: {report_dir}")
            logger.error("请先运行 validate_resources.py 进行资源验证")
            return

        # 获取所有 JSON 验证报告
        json_reports = list(report_dir.glob("*_validation.json"))
        if not json_reports:
            logger.error("未找到任何验证报告")
            logger.error("请先运行 validate_resources.py 进行资源验证")
            return

        logger.info(f"找到 {len(json_reports)} 个验证报告")

        # 创建资源同步器
        syncer = ResourceSyncer(
            config.resources.project_root,
            config.resources.source_root
        )

        # 处理每个验证报告
        for json_report in json_reports:
            logger.info(f"\n处理报告: {json_report.name}")

            # 加载验证报告
            try:
                with open(json_report, "r", encoding="utf-8") as f:
                    report_data = json.load(f)
            except Exception as e:
                logger.error(f"读取报告失败: {e}")
                continue

            # 提取数据
            validation_results = report_data.get("validation_results", {})
            resource_folders = report_data.get("resource_folders", {})
            excel_name = report_data.get("excel_name", "未知")

            logger.info(f"Excel 文件: {excel_name}")

            # 创建同步计划
            sync_plan = syncer.create_sync_plan(validation_results, resource_folders)

            if not sync_plan:
                logger.info("没有需要同步的文件")
                continue

            # 显示同步计划
            show_sync_plan(sync_plan, resource_folders)

            # 询问用户确认
            response = input(f"\n是否执行同步? (y/N): ").strip().lower()
            if response != 'y':
                logger.info("已取消同步")
                continue

            # 询问是否干跑
            dry_run_response = input("是否为干跑模式（仅预览，不实际复制）? (y/N): ").strip().lower()
            dry_run = (dry_run_response == 'y')

            # 执行同步
            logger.info(f"\n开始同步{'（干跑模式）' if dry_run else ''}...")
            stats = syncer.execute_sync(sync_plan, dry_run)

            # 显示统计
            print(f"\n同步结果:")
            print(f"  成功: {stats['success']}")
            print(f"  失败: {stats['failed']}")
            print(f"  跳过: {stats['skipped']}")

            if dry_run:
                print("\n注意: 当前为干跑模式，未实际执行复制操作")

        logger.info("\n所有文件处理完成")

    except Exception as e:
        logger.critical(f"同步过程失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
