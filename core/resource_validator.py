"""
资源验证器模块
验证资源文件是否存在于项目库和资源库中
"""
from typing import Dict, Set, List
from pathlib import Path
from collections import defaultdict
import os
from core.logger import get_logger

logger = get_logger()


class ResourceValidator:
    """资源验证器 - 验证资源文件是否存在"""

    def __init__(
        self,
        project_root: Path,
        source_root: Path,
        extensions: Dict[str, List[str]]
    ):
        """
        初始化资源验证器

        Args:
            project_root: 项目资源根目录
            source_root: 资源库根目录
            extensions: 文件扩展名配置 {"图片": [".png", ".jpg"], "音频": [".ogg", ".mp3"]}
        """
        self.project_root = Path(project_root)
        self.source_root = Path(source_root)
        self.extensions = extensions

    def validate_resources(
        self,
        resources: Dict[str, Dict[str, Set[str]]],
        resource_folders: Dict[str, str]
    ) -> Dict:
        """
        验证资源文件是否存在

        Args:
            resources: 资源字典 {资源类别: {资源类型: {资源名集合}}}
            resource_folders: 资源文件夹映射 {资源类型: 文件夹路径}

        Returns:
            Dict: 验证结果
        """
        results = {
            "project": {},  # 项目库验证结果
            "source": {},   # 资源库验证结果
            "comparison": {}  # 对比结果
        }

        for category, types in resources.items():
            for resource_type, resource_names in types.items():
                folder = resource_folders.get(resource_type, "")
                if not folder:
                    logger.warning(f"未找到资源类型 {resource_type} 的文件夹配置")
                    continue

                # 规范化 folder 路径（去除首尾斜杠，避免路径构建问题）
                folder_normalized = folder.strip().strip('/\\')
                
                try:
                    # 构建项目库路径并验证
                    project_folder = self.project_root / folder_normalized
                    project_results = self._validate_in_library(
                        project_folder,
                        resource_names,
                        self.extensions.get(category, [])
                    )
                except Exception as e:
                    logger.error(
                        f"验证项目库资源失败: resource_type={resource_type}, "
                        f"project_root={self.project_root}, folder={folder}, error={e}",
                        exc_info=True
                    )
                    project_results = {name: "" for name in resource_names}

                try:
                    # 构建资源库路径并验证
                    source_folder = self.source_root / folder_normalized
                    source_results = self._validate_in_library(
                        source_folder,
                        resource_names,
                        self.extensions.get(category, [])
                    )
                except Exception as e:
                    logger.error(
                        f"验证资源库资源失败: resource_type={resource_type}, "
                        f"source_root={self.source_root}, folder={folder}, error={e}",
                        exc_info=True
                    )
                    source_results = {name: "" for name in resource_names}

                # 保存结果
                results["project"][resource_type] = project_results
                results["source"][resource_type] = source_results

                # 对比结果
                comparison = self._compare_results(
                    resource_names,
                    project_results,
                    source_results
                )
                results["comparison"][resource_type] = comparison

        return results

    def _validate_in_library(
        self,
        folder: Path,
        resource_names: Set[str],
        extensions: List[str]
    ) -> Dict[str, str]:
        """
        在指定文件夹中验证资源

        Args:
            folder: 文件夹路径
            resource_names: 资源名集合
            extensions: 文件扩展名列表

        Returns:
            Dict[str, str]: {资源名: 找到的文件名}，未找到则值为空字符串
        """
        results = {}

        try:
            # 检查是否是根路径（可能导致问题）
            if self._is_root_path(folder):
                logger.warning(f"文件夹路径是根路径，可能导致问题: {folder}")
                for name in resource_names:
                    results[name] = ""
                return results

            if not folder.exists():
                logger.warning(f"文件夹不存在: {folder}")
                for name in resource_names:
                    results[name] = ""
                return results

            for resource_name in resource_names:
                try:
                    found_file = self._find_file(folder, resource_name, extensions)
                    results[resource_name] = found_file
                except Exception as e:
                    logger.debug(
                        f"查找文件失败: folder={folder}, resource_name={resource_name}, error={e}"
                    )
                    results[resource_name] = ""

        except Exception as e:
            logger.error(
                f"验证资源库失败: folder={folder}, error={e}",
                exc_info=True
            )
            # 返回空结果
            for name in resource_names:
                results[name] = ""

        return results

    def _is_root_path(self, folder: Path) -> bool:
        """
        检查路径是否是根路径

        Args:
            folder: 要检查的路径

        Returns:
            bool: 是否是根路径
        """
        folder_str = str(folder).rstrip('/\\')
        return (
            folder_str == '' or
            folder_str.endswith(':') or  # Windows 驱动器根: D:
            (len(folder.parts) == 1 and folder.parts[0] in ('/', '\\')) or  # Unix 根
            folder.parent == folder  # 根路径的 parent 等于自身
        )

    def _find_file(
        self,
        folder: Path,
        resource_name: str,
        extensions: List[str]
    ) -> str:
        """
        在文件夹中查找文件（支持子文件夹路径）

        Args:
            folder: 文件夹路径
            resource_name: 资源名（可能包含路径，如 "alice/happy" 或 "alice\\happy"）
            extensions: 文件扩展名列表

        Returns:
            str: 找到的文件路径（相对路径，如 "alice/happy.png"），未找到返回空字符串
        """
        # 规范化路径分隔符（统一使用正斜杠，Path 对象会自动处理）
        resource_name_normalized = resource_name.replace('\\', '/')
        
        for ext in extensions:
            try:
                # 如果资源名称包含路径分隔符，构建完整路径
                if '/' in resource_name_normalized:
                    # 使用 Path 对象构建路径，然后添加扩展名
                    # 例如：folder / "alice/happy" -> folder/alice/happy，然后添加 .png
                    # 先构建路径，再添加扩展名，避免路径构建错误
                    base_path = folder / resource_name_normalized
                    file_path = base_path.with_suffix(ext)
                else:
                    # 否则在根文件夹下查找
                    file_path = folder / f"{resource_name_normalized}{ext}"
            except Exception as e:
                logger.debug(
                    f"构建文件路径失败: folder={folder}, resource_name={resource_name_normalized}, "
                    f"ext={ext}, error={e}"
                )
                continue
            
            if file_path.exists():
                # 返回相对路径（相对于 folder）
                # 如果包含子文件夹，返回完整相对路径；否则只返回文件名
                if '/' in resource_name_normalized:
                    # 检查是否是根路径，如果是则直接返回资源名称
                    if self._is_root_path(folder):
                        return f"{resource_name_normalized}{ext}"
                    
                    try:
                        # 尝试使用 relative_to 计算相对路径
                        relative_path = file_path.relative_to(folder)
                        return str(relative_path).replace('\\', '/')
                    except (ValueError, AttributeError):
                        # 如果 relative_to 失败，使用 os.path.relpath 作为备选
                        try:
                            relative_path = os.path.relpath(str(file_path), str(folder))
                            return relative_path.replace('\\', '/')
                        except (ValueError, AttributeError):
                            # 如果还是失败，直接返回资源名称加上扩展名
                            logger.debug(
                                f"无法计算相对路径: file_path={file_path}, folder={folder}, "
                                f"使用资源名称: {resource_name_normalized}{ext}"
                            )
                            return f"{resource_name_normalized}{ext}"
                else:
                    return file_path.name

        return ""

    def _compare_results(
        self,
        resource_names: Set[str],
        project_results: Dict[str, str],
        source_results: Dict[str, str]
    ) -> Dict:
        """
        对比项目库和资源库的验证结果

        Returns:
            Dict: {
                "project_found": [...],
                "project_missing": [...],
                "source_found": [...],
                "source_missing": [...],
                "missing_in_project_but_in_source": [...],
                "missing_in_both": [...]
            }
        """
        project_found = [name for name in resource_names if project_results.get(name)]
        project_missing = [name for name in resource_names if not project_results.get(name)]
        source_found = [name for name in resource_names if source_results.get(name)]
        source_missing = [name for name in resource_names if not source_results.get(name)]

        missing_in_project_but_in_source = [
            name for name in project_missing if name in source_found
        ]

        missing_in_both = [
            name for name in project_missing if name in source_missing
        ]

        return {
            "project_found": project_found,
            "project_missing": project_missing,
            "source_found": source_found,
            "source_missing": source_missing,
            "missing_in_project_but_in_source": missing_in_project_but_in_source,
            "missing_in_both": missing_in_both
        }
