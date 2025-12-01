"""
资源验证器模块
验证资源文件是否存在于项目库和资源库中
"""
from typing import Dict, Set, List
from pathlib import Path
from collections import defaultdict
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

                # 在项目库中验证
                project_results = self._validate_in_library(
                    self.project_root / folder,
                    resource_names,
                    self.extensions.get(category, [])
                )

                # 在资源库中验证
                source_results = self._validate_in_library(
                    self.source_root / folder,
                    resource_names,
                    self.extensions.get(category, [])
                )

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

        if not folder.exists():
            logger.warning(f"文件夹不存在: {folder}")
            for name in resource_names:
                results[name] = ""
            return results

        for resource_name in resource_names:
            found_file = self._find_file(folder, resource_name, extensions)
            results[resource_name] = found_file

        return results

    def _find_file(
        self,
        folder: Path,
        resource_name: str,
        extensions: List[str]
    ) -> str:
        """
        在文件夹中查找文件

        Args:
            folder: 文件夹路径
            resource_name: 资源名（可能包含空格，如 "alice happy smile"）
            extensions: 文件扩展名列表

        Returns:
            str: 找到的文件名（带扩展名），未找到返回空字符串
        """
        for ext in extensions:
            file_path = folder / f"{resource_name}{ext}"
            if file_path.exists():
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
