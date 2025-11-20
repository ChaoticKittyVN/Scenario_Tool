"""
资源同步工具
从资源库同步缺失的资源到项目库
"""
import shutil
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from core.config_manager import AppConfig
from core.logger import get_logger

logger = get_logger()


class ResourceSyncer:
    """资源同步器"""

    def __init__(self, config: AppConfig, project_dirs: Dict[str, Path], source_dirs: Dict[str, Path]):
        """
        初始化资源同步器

        Args:
            config: 应用配置
            project_dirs: 项目资源目录配置
            source_dirs: 资源库目录配置
        """
        self.config = config
        self.project_dirs = project_dirs
        self.source_dirs = source_dirs
        self.extensions_map = {
            "图片": [".png", ".jpg", ".jpeg", ".webp"],
            "音频": [".mp3", ".ogg", ".wav", ".m4a"],
            "视频": [".mp4", ".webm", ".ogv"],
        }

    def read_validation_report(self, report_path: Path) -> Dict[str, Set[str]]:
        """
        读取验证报告，提取缺失文件列表

        Args:
            report_path: 验证报告路径

        Returns:
            Dict[str, Set[str]]: 资源类型 -> 缺失文件集合
        """
        missing_files = {}
        current_type = None

        try:
            with open(report_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            in_missing_section = False

            for line in lines:
                line = line.strip()

                # 检测资源类型
                if line.endswith("文件:"):
                    current_type = line.replace("文件:", "")
                    missing_files[current_type] = set()
                    in_missing_section = False

                # 检测缺失文件列表开始
                elif "缺失文件列表:" in line:
                    in_missing_section = True

                # 提取缺失文件名
                elif in_missing_section and line.startswith("- "):
                    filename = line[2:].strip()
                    if current_type and filename:
                        missing_files[current_type].add(filename)

                # 检测章节结束
                elif line.startswith("=") or line.startswith("总计统计:"):
                    in_missing_section = False

            logger.info(f"从报告中读取到 {sum(len(v) for v in missing_files.values())} 个缺失文件")
            return missing_files

        except Exception as e:
            logger.error(f"读取验证报告失败: {e}", exc_info=True)
            return {}

    def find_in_source_library(
        self,
        resource_type: str,
        filename: str
    ) -> Optional[Path]:
        """
        在资源库中查找文件

        Args:
            resource_type: 资源类型
            filename: 文件名（不含扩展名）

        Returns:
            Optional[Path]: 找到的文件路径，未找到返回 None
        """
        source_dir = self.source_dirs.get(resource_type)
        if not source_dir or not source_dir.exists():
            return None

        # 尝试不同的扩展名
        extensions = self.extensions_map.get(resource_type, [])
        for ext in extensions:
            file_path = source_dir / f"{filename}{ext}"
            if file_path.exists():
                return file_path

        return None

    def create_sync_plan(
        self,
        missing_files: Dict[str, Set[str]]
    ) -> Tuple[Dict[str, List[Tuple[Path, Path]]], Dict[str, Set[str]]]:
        """
        创建同步计划

        Args:
            missing_files: 缺失文件字典

        Returns:
            Tuple[Dict, Dict]: (同步计划, 未找到的文件)
                - 同步计划: 资源类型 -> [(源路径, 目标路径)]
                - 未找到: 资源类型 -> {文件名}
        """
        sync_plan = {}
        not_found = {}

        for resource_type, filenames in missing_files.items():
            sync_plan[resource_type] = []
            not_found[resource_type] = set()

            for filename in filenames:
                # 在资源库中查找
                source_file = self.find_in_source_library(resource_type, filename)

                if source_file:
                    # 找到了，添加到同步计划
                    project_dir = self.project_dirs.get(resource_type)
                    if project_dir:
                        target_file = project_dir / source_file.name
                        sync_plan[resource_type].append((source_file, target_file))
                else:
                    # 未找到，添加到警告列表
                    not_found[resource_type].add(filename)

        return sync_plan, not_found

    def show_sync_plan(
        self,
        sync_plan: Dict[str, List[Tuple[Path, Path]]],
        not_found: Dict[str, Set[str]]
    ):
        """
        显示同步计划

        Args:
            sync_plan: 同步计划
            not_found: 未找到的文件
        """
        print("\n" + "=" * 60)
        print("资源同步计划")
        print("=" * 60)

        # 统计
        total_to_sync = sum(len(v) for v in sync_plan.values())
        total_not_found = sum(len(v) for v in not_found.values())

        print(f"\n总计:")
        print(f"  可同步: {total_to_sync} 个文件")
        print(f"  未找到: {total_not_found} 个文件")

        # 显示可同步的文件
        if total_to_sync > 0:
            print(f"\n可同步的文件:")
            print("-" * 60)
            for resource_type, files in sync_plan.items():
                if files:
                    print(f"\n{resource_type}文件 ({len(files)} 个):")
                    for source, target in files:
                        print(f"  ✓ {source.name}")
                        print(f"    从: {source}")
                        print(f"    到: {target}")

        # 显示未找到的文件
        if total_not_found > 0:
            print(f"\n未找到的文件（将跳过）:")
            print("-" * 60)
            for resource_type, filenames in not_found.items():
                if filenames:
                    print(f"\n{resource_type}文件 ({len(filenames)} 个):")
                    for filename in sorted(filenames):
                        print(f"  ✗ {filename}")

        print("\n" + "=" * 60)

    def execute_sync(
        self,
        sync_plan: Dict[str, List[Tuple[Path, Path]]],
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        执行同步

        Args:
            sync_plan: 同步计划
            dry_run: 是否为干跑模式

        Returns:
            Dict[str, int]: 统计信息
        """
        stats = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "total": 0
        }

        for resource_type, files in sync_plan.items():
            for source, target in files:
                stats["total"] += 1

                try:
                    # 检查目标文件是否已存在
                    if target.exists():
                        logger.warning(f"目标文件已存在，跳过: {target.name}")
                        stats["skipped"] += 1
                        continue

                    # 确保目标目录存在
                    target.parent.mkdir(parents=True, exist_ok=True)

                    if dry_run:
                        logger.info(f"[干跑] 将复制: {source.name}")
                        stats["success"] += 1
                    else:
                        # 执行复制
                        shutil.copy2(source, target)
                        logger.info(f"已复制: {source.name} -> {target}")
                        stats["success"] += 1

                except Exception as e:
                    logger.error(f"复制失败: {source.name} - {e}")
                    stats["failed"] += 1

        return stats


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

        # 配置项目资源目录
        project_dirs = {
            "图片": Path("project/images"),
            "音频": Path("project/audio"),
            "视频": Path("project/video"),
        }

        # 配置资源库目录
        source_dirs = {
            "图片": Path("resource_library/images"),
            "音频": Path("resource_library/audio"),
            "视频": Path("resource_library/video"),
        }

        logger.info("=" * 60)
        logger.info("资源同步工具")
        logger.info("=" * 60)

        # 查找验证报告
        report_dir = config.paths.output_dir / "validation_reports"
        if not report_dir.exists():
            logger.error(f"验证报告目录不存在: {report_dir}")
            logger.info("请先运行 validate_resources.py 生成验证报告")
            return

        report_files = list(report_dir.glob("*_validation.txt"))
        if not report_files:
            logger.warning(f"未找到验证报告: {report_dir}")
            logger.info("请先运行 validate_resources.py 生成验证报告")
            return

        logger.info(f"找到 {len(report_files)} 个验证报告")

        # 创建同步器
        syncer = ResourceSyncer(config, project_dirs, source_dirs)

        # 处理每个报告
        for report_file in report_files:
            logger.info(f"\n处理报告: {report_file.name}")

            # 读取缺失文件列表
            missing_files = syncer.read_validation_report(report_file)

            if not missing_files or sum(len(v) for v in missing_files.values()) == 0:
                logger.info("没有缺失的文件需要同步")
                continue

            # 创建同步计划
            sync_plan, not_found = syncer.create_sync_plan(missing_files)

            # 显示同步计划
            syncer.show_sync_plan(sync_plan, not_found)

            # 询问用户确认
            total_to_sync = sum(len(v) for v in sync_plan.values())
            if total_to_sync == 0:
                logger.warning("没有可同步的文件（所有文件都未在资源库中找到）")
                continue

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
            print(f"  总计: {stats['total']}")

            if dry_run:
                print("\n注意: 当前为干跑模式，未实际执行复制操作")

        logger.info("\n所有报告处理完成")

    except Exception as e:
        logger.critical(f"同步过程失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
