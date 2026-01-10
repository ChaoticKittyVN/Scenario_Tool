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

            # 规范化 folder 路径（去除首尾斜杠，避免路径构建问题）
            folder_normalized = folder.strip().strip('/\\')

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
                if not source_filename:
                    logger.warning(f"资源 {resource_name} 在验证结果中未找到文件名，跳过")
                    continue

                # 规范化文件名路径（统一使用正斜杠）
                source_filename_normalized = str(source_filename).replace('\\', '/')
                
                # 构建源路径和目标路径
                source_path = self.source_root / folder_normalized / source_filename_normalized
                target_path = self.project_root / folder_normalized / source_filename_normalized

                # 验证路径安全性（确保路径在预期根目录下）
                try:
                    source_resolved = source_path.resolve()
                    target_resolved = target_path.resolve()
                    source_root_resolved = self.source_root.resolve()
                    project_root_resolved = self.project_root.resolve()

                    # 检查源路径是否在源根目录下
                    if not str(source_resolved).startswith(str(source_root_resolved)):
                        logger.warning(
                            f"源路径不在预期根目录下，跳过: {source_path} "
                            f"(预期根目录: {source_root_resolved})"
                        )
                        continue

                    # 检查目标路径是否在项目根目录下
                    if not str(target_resolved).startswith(str(project_root_resolved)):
                        logger.warning(
                            f"目标路径不在预期根目录下，跳过: {target_path} "
                            f"(预期根目录: {project_root_resolved})"
                        )
                        continue

                except Exception as e:
                    logger.warning(f"验证路径安全性失败: {e}，跳过资源 {resource_name}")
                    continue

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
            source_path = Path(item["source_path"])
            target_path = Path(item["target_path"])
            resource_name = item.get("resource_name", "未知")

            try:
                # 检查源文件是否存在
                if not source_path.exists():
                    logger.error(
                        f"源文件不存在，跳过: {source_path} "
                        f"(资源: {resource_name})"
                    )
                    stats["skipped"] += 1
                    continue

                # 检查源文件是否是文件（而不是目录）
                if not source_path.is_file():
                    logger.warning(
                        f"源路径不是文件，跳过: {source_path} "
                        f"(资源: {resource_name})"
                    )
                    stats["skipped"] += 1
                    continue

                # 检查目标文件是否已存在
                if target_path.exists():
                    logger.warning(
                        f"目标文件已存在，跳过: {target_path} "
                        f"(资源: {resource_name})"
                    )
                    stats["skipped"] += 1
                    continue

                # 确保目标目录存在
                try:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    logger.error(
                        f"创建目标目录失败: {target_path.parent} - {e} "
                        f"(资源: {resource_name})"
                    )
                    stats["failed"] += 1
                    continue

                if dry_run:
                    logger.info(
                        f"[干跑] 将复制: {source_path} -> {target_path} "
                        f"(资源: {resource_name})"
                    )
                    stats["success"] += 1
                else:
                    # 执行复制
                    try:
                        shutil.copy2(source_path, target_path)
                        logger.info(
                            f"已复制: {source_path} -> {target_path} "
                            f"(资源: {resource_name})"
                        )
                        stats["success"] += 1
                    except Exception as copy_error:
                        logger.error(
                            f"复制操作失败: {source_path} -> {target_path} - {copy_error} "
                            f"(资源: {resource_name})"
                        )
                        stats["failed"] += 1

            except Exception as e:
                logger.error(
                    f"处理资源失败: {resource_name} - {e}",
                    exc_info=True
                )
                stats["failed"] += 1

        return stats
