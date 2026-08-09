"""Validate resource references against project and source libraries."""
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from core.logger import get_logger
from core.resource_resolution import ResourceResolution, ResourceResolver


logger = get_logger()


class ResourceValidator:
    """Validate resource files and delegate engine-specific lookups."""

    def __init__(
        self,
        project_root: Path,
        source_root: Path,
        extensions: Dict[str, List[str]],
        validate_source: bool = True,
        filename_normalization: Optional[Dict[str, List[str]]] = None,
        resource_resolvers: Optional[List[ResourceResolver]] = None,
    ):
        self.project_root = Path(project_root)
        self.source_root = Path(source_root)
        self.extensions = extensions
        self.validate_source = validate_source
        self.filename_normalization = filename_normalization or {}
        self.resource_resolvers = resource_resolvers or []

    def validate_resources(
        self,
        resources: Dict[str, Dict[str, Set[str]]],
        resource_folders: Dict[str, str],
    ) -> Dict:
        results = {
            "project": {},
            "source": {},
            "comparison": {},
            "source_enabled": self.validate_source,
        }

        for category, types in resources.items():
            for resource_type, resource_names in types.items():
                folder = resource_folders.get(resource_type, "")
                if not folder:
                    logger.warning(
                        f"未找到资源类型 {resource_type} 的文件夹配置"
                    )
                    continue

                folder_normalized = folder.strip().strip("/\\")
                try:
                    project_results, project_matches = self._validate_in_library(
                        self.project_root / folder_normalized,
                        resource_names,
                        self.extensions.get(category, []),
                        category,
                        resource_type,
                        use_resolvers=True,
                    )
                except Exception as exc:
                    logger.error(
                        f"验证项目库资源失败: resource_type={resource_type}, "
                        f"project_root={self.project_root}, folder={folder}, "
                        f"error={exc}",
                        exc_info=True,
                    )
                    project_results = {name: "" for name in resource_names}
                    project_matches = []

                source_results = {}
                if self.validate_source:
                    try:
                        source_results, _ = self._validate_in_library(
                            self.source_root / folder_normalized,
                            resource_names,
                            self.extensions.get(category, []),
                            category,
                            resource_type,
                            use_resolvers=False,
                        )
                    except Exception as exc:
                        logger.error(
                            f"验证资源库资源失败: resource_type={resource_type}, "
                            f"source_root={self.source_root}, folder={folder}, "
                            f"error={exc}",
                            exc_info=True,
                        )
                        source_results = {name: "" for name in resource_names}

                results["project"][resource_type] = project_results
                results["source"][resource_type] = source_results
                results["comparison"][resource_type] = self._compare_results(
                    resource_names,
                    project_results,
                    source_results,
                    self.validate_source,
                    project_matches,
                )

        return results

    def _validate_in_library(
        self,
        folder: Path,
        resource_names: Set[str],
        extensions: List[str],
        category: str = "",
        resource_type: str = "",
        use_resolvers: bool = False,
    ) -> Tuple[Dict[str, str], List[Dict[str, str]]]:
        results = {}
        alternate_matches = []

        try:
            if self._is_root_path(folder):
                logger.warning(f"文件夹路径是根路径，可能导致问题: {folder}")
                return (
                    {name: "" for name in resource_names},
                    alternate_matches,
                )

            if not folder.exists():
                logger.warning(f"文件夹不存在: {folder}")
                return (
                    {name: "" for name in resource_names},
                    alternate_matches,
                )

            for resource_name in resource_names:
                try:
                    resolution = self._find_file(
                        folder, resource_name, extensions, category
                    )
                    if resolution is None and use_resolvers:
                        resolution = self._resolve_with_extensions(
                            folder, resource_name, resource_type
                        )

                    results[resource_name] = (
                        resolution.found_file if resolution else ""
                    )
                    if resolution and resolution.match_type != "exact":
                        alternate_matches.append({
                            "resource_name": resource_name,
                            "found_file": resolution.found_file,
                            "match_type": resolution.match_type,
                            "match_label": resolution.match_label,
                        })
                except Exception as exc:
                    logger.debug(
                        f"查找文件失败: folder={folder}, "
                        f"resource_name={resource_name}, error={exc}"
                    )
                    results[resource_name] = ""
        except Exception as exc:
            logger.error(
                f"验证资源库失败: folder={folder}, error={exc}",
                exc_info=True,
            )
            results = {name: "" for name in resource_names}

        return results, alternate_matches

    def _is_root_path(self, folder: Path) -> bool:
        folder_str = str(folder).rstrip("/\\")
        return (
            folder_str == ""
            or folder_str.endswith(":")
            or (len(folder.parts) == 1 and folder.parts[0] in ("/", "\\"))
            or folder.parent == folder
        )

    def _find_file(
        self,
        folder: Path,
        resource_name: str,
        extensions: List[str],
        category: str = "",
    ) -> Optional[ResourceResolution]:
        normalized_name = resource_name.replace("\\", "/")
        candidates = [ResourceResolution(normalized_name)]

        rules = self.filename_normalization.get(category, [])
        if "spaces_to_underscores" in rules:
            underscored_name = normalized_name.replace(" ", "_")
            if underscored_name != normalized_name:
                candidates.append(ResourceResolution(
                    underscored_name,
                    match_type="filename_normalization",
                    match_label="空格转下划线",
                ))

        for candidate in candidates:
            found_file = self._find_candidate(
                folder, candidate.found_file, extensions
            )
            if found_file:
                return ResourceResolution(
                    found_file,
                    match_type=candidate.match_type,
                    match_label=candidate.match_label,
                )
        return None

    def _resolve_with_extensions(
        self,
        folder: Path,
        resource_name: str,
        resource_type: str,
    ) -> Optional[ResourceResolution]:
        for resolver in self.resource_resolvers:
            resolution = resolver.resolve(folder, resource_name, resource_type)
            if resolution is not None:
                return resolution
        return None

    def _find_candidate(
        self,
        folder: Path,
        resource_name: str,
        extensions: List[str],
    ) -> str:
        for extension in extensions:
            try:
                if "/" in resource_name:
                    file_path = (folder / resource_name).with_suffix(extension)
                else:
                    file_path = folder / f"{resource_name}{extension}"
            except Exception as exc:
                logger.debug(
                    f"构建文件路径失败: folder={folder}, "
                    f"resource_name={resource_name}, ext={extension}, error={exc}"
                )
                continue

            if not self._is_within_folder(file_path, folder):
                logger.warning(
                    "忽略超出资源目录的路径: "
                    f"folder={folder}, resource_name={resource_name}"
                )
                continue

            if not file_path.exists():
                continue
            if "/" not in resource_name:
                return file_path.name
            if self._is_root_path(folder):
                return f"{resource_name}{extension}"

            try:
                return str(file_path.relative_to(folder)).replace("\\", "/")
            except (ValueError, AttributeError):
                try:
                    return os.path.relpath(
                        str(file_path), str(folder)
                    ).replace("\\", "/")
                except (ValueError, AttributeError):
                    logger.debug(
                        f"无法计算相对路径: file_path={file_path}, "
                        f"folder={folder}, 使用资源名称: "
                        f"{resource_name}{extension}"
                    )
                    return f"{resource_name}{extension}"

        return ""

    @staticmethod
    def _is_within_folder(candidate: Path, folder: Path) -> bool:
        try:
            candidate.resolve().relative_to(folder.resolve())
            return True
        except (OSError, RuntimeError, ValueError):
            return False

    def _compare_results(
        self,
        resource_names: Set[str],
        project_results: Dict[str, str],
        source_results: Dict[str, str],
        source_enabled: bool = True,
        project_matches: Optional[List[Dict[str, str]]] = None,
    ) -> Dict:
        project_found = [
            name for name in resource_names if project_results.get(name)
        ]
        project_missing = [
            name for name in resource_names if not project_results.get(name)
        ]
        source_found = (
            [name for name in resource_names if source_results.get(name)]
            if source_enabled else []
        )
        source_missing = (
            [name for name in resource_names if not source_results.get(name)]
            if source_enabled else []
        )
        missing_in_project_but_in_source = (
            [name for name in project_missing if name in source_found]
            if source_enabled else []
        )
        missing_in_both = (
            [name for name in project_missing if name in source_missing]
            if source_enabled else []
        )

        project_matches = project_matches or []
        normalized_matches = [
            match for match in project_matches
            if match["match_type"] == "filename_normalization"
        ]
        resolver_matches = [
            match for match in project_matches
            if match["match_type"] != "filename_normalization"
        ]

        return {
            "project_found": project_found,
            "project_missing": project_missing,
            "source_found": source_found,
            "source_missing": source_missing,
            "missing_in_project_but_in_source": missing_in_project_but_in_source,
            "missing_in_both": missing_in_both,
            "project_normalized_matches": normalized_matches,
            "project_resolver_matches": resolver_matches,
        }
