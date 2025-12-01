"""
资源同步器模块
从资源库同步缺失的资源到项目库
"""
import shutil
from typing import Dict, List
from pathlib import Path
from core.logger import get_logger

logger = get_logger()


class ResourceSyncer:
    """资源同步器 - 从资源库同步资源到项目库"""

    def __init__(
        self,
        project_root: Path,
        source_root: Path
    ):
        """
        初始化资源同步器

        Args:
            project_root: 项目资源根目录
            source_root: 资源库根目录
        """
        self.project_root = Path(project_root)
        self.source_root = Path(source_root)

    def create_sync_plan(
        self,
        validation_results: Dict,
        resource_folders: Dict[str, str]
    ) -> List[Dict]:
        """
        创建同步计划

        Args:
            validation_results: 验证结果
            resource_folders: 资源文件夹映射

        Returns:
            List[Dict]: 同步计划列表，每项包含 source_path 和 target_path
        """
        sync_plan = []

        comparison = validation_results.get("comparison", {})
        source_results = validation_results.get("source", {})

        # 统计两个库都缺失的文件
        total_missing_in_both = 0

        for resource_type, comp_data in comparison.items():
            folder = resource_folders.get(resource_type, "")
            if not folder:
                continue

            # 检查两个库都缺失的文件
            missing_in_both = comp_data.get("missing_in_both", [])
            if missing_in_both:
                total_missing_in_both += len(missing_in_both)
                logger.warning(
                    f"{resource_type}: {len(missing_in_both)} 个文件在项目库和资源库中都不存在"
                )
                # 显示前几个文件名作为示例
                for name in list(missing_in_both)[:3]:
                    logger.warning(f"  - {name}")
                if len(missing_in_both) > 3:
                    logger.warning(f"  ... 还有 {len(missing_in_both) - 3} 个")

            # 获取项目库缺失但资源库存在的文件
            missing_files = comp_data.get("missing_in_project_but_in_source", [])

            for resource_name in missing_files:
                source_filename = source_results[resource_type].get(resource_name)
                if source_filename:
                    source_path = self.source_root / folder / source_filename
                    target_path = self.project_root / folder / source_filename

                    sync_plan.append({
                        "resource_type": resource_type,
                        "resource_name": resource_name,
                        "source_path": source_path,
                        "target_path": target_path
                    })

        # 如果有文件在两个库都缺失，给出总体警告
        if total_missing_in_both > 0:
            logger.warning(
                f"警告: 共有 {total_missing_in_both} 个文件在项目库和资源库中都不存在，"
                f"需要手动添加到资源库后重新同步"
            )

        return sync_plan

    def execute_sync(
        self,
        sync_plan: List[Dict],
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        执行同步

        Args:
            sync_plan: 同步计划
            dry_run: 是否为干跑模式

        Returns:
            Dict[str, int]: 统计信息 {"success": 0, "failed": 0, "skipped": 0}
        """
        stats = {"success": 0, "failed": 0, "skipped": 0}

        for item in sync_plan:
            source_path = item["source_path"]
            target_path = item["target_path"]

            try:
                # 检查目标文件是否已存在
                if target_path.exists():
                    logger.warning(f"目标文件已存在，跳过: {target_path.name}")
                    stats["skipped"] += 1
                    continue

                # 确保目标目录存在
                target_path.parent.mkdir(parents=True, exist_ok=True)

                if dry_run:
                    logger.info(f"[干跑] 将复制: {source_path.name}")
                    stats["success"] += 1
                else:
                    # 执行复制
                    shutil.copy2(source_path, target_path)
                    logger.info(f"已复制: {source_path.name} -> {target_path}")
                    stats["success"] += 1

            except Exception as e:
                logger.error(f"复制失败: {source_path.name} - {e}")
                stats["failed"] += 1

        return stats
