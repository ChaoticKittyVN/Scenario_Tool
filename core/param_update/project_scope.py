"""Resolve project-specific parameter sources for scenario workbooks."""

from pathlib import Path
from typing import Dict, List, Optional

from core.logger import get_logger


logger = get_logger()


class ProjectScopeMixin:
    """Provide multi-project matching and merge behavior."""

    @property
    def multi_project_mode(self) -> bool:
        """Whether project-specific parameter data is enabled."""
        processing = getattr(self.config, "processing", None)
        return getattr(processing, "multi_project_mode", False) is True

    @property
    def projects(self) -> Dict[str, str]:
        """Return valid project keys and workbook filename markers."""
        projects = getattr(self.config, "projects", {})
        if not isinstance(projects, dict):
            return {}
        return {
            str(project_key): str(match_text)
            for project_key, match_text in projects.items()
            if str(project_key).strip() and str(match_text).strip()
        }

    def _find_project_param_files(self) -> List[tuple[Path, str]]:
        """Find enabled project-specific parameter workbooks."""
        if not self.multi_project_mode:
            return []

        param_dir = Path(self.config.paths.param_config_dir)
        results = []
        for project_key in self.projects:
            project_file = param_dir / f"param_data_{project_key}.xlsx"
            if project_file.exists():
                results.append((project_file, project_key))
                logger.info(
                    f"发现项目参数文件: {project_file.name} (项目: {project_key})"
                )
            else:
                logger.warning(f"项目参数文件不存在，跳过: {project_file}")
        return results

    @staticmethod
    def _merge_mappings(
        mappings_list: List[Dict[str, Dict[str, str]]],
    ) -> Dict[str, Dict[str, str]]:
        """Merge mappings in order, allowing later project values to win."""
        merged: Dict[str, Dict[str, str]] = {}
        for mappings in mappings_list:
            for sheet_name, sheet_mapping in mappings.items():
                merged.setdefault(sheet_name, {}).update(sheet_mapping)
        return merged

    @staticmethod
    def _merge_validation_data(
        data_list: List[Dict[str, List[str]]],
    ) -> Dict[str, List[str]]:
        """Merge validation values without changing their original order."""
        merged: Dict[str, List[str]] = {}
        for data in data_list:
            for param_type, values in data.items():
                target = merged.setdefault(param_type, [])
                existing = set(target)
                for value in values:
                    if value not in existing:
                        target.append(value)
                        existing.add(value)
        return merged

    def _match_project_for_excel(self, excel_file: Path) -> Optional[str]:
        """Match a scenario workbook to a configured project."""
        if not self.multi_project_mode:
            return None

        filename = excel_file.name
        matches = [
            (project_key, match_text)
            for project_key, match_text in self.projects.items()
            if match_text in filename
        ]
        if not matches:
            logger.debug(f"文件 {filename} 未匹配到项目参数")
            return None
        if len(matches) > 1:
            matched_keys = ", ".join(project_key for project_key, _ in matches)
            logger.warning(
                f"文件 {filename} 匹配到多个项目 ({matched_keys})，使用第一个"
            )
        project_key, match_text = matches[0]
        logger.info(f"文件 {filename} 匹配到项目: {project_key} ({match_text})")
        return project_key

    def _validation_data_for_workbook(
        self,
        excel_file: Path,
        base_validation_data: Dict[str, List[str]],
        project_cache: Dict[str, Dict[str, List[str]]],
    ) -> Dict[str, List[str]]:
        """Merge base data with the project data selected for one workbook."""
        project_key = self._match_project_for_excel(excel_file)
        if project_key is None:
            return base_validation_data

        if project_key not in project_cache:
            project_file = (
                Path(self.config.paths.param_config_dir)
                / f"param_data_{project_key}.xlsx"
            )
            if not project_file.exists():
                logger.warning(
                    f"项目 '{project_key}' 的参数文件不存在: {project_file}"
                )
                project_cache[project_key] = {}
            else:
                project_cache[project_key] = self.collect_validation_data(project_file)

        project_data = project_cache[project_key]
        if not project_data:
            return base_validation_data
        logger.info(f"为 {excel_file.name} 合并项目 '{project_key}' 的定制参数")
        return self._merge_validation_data([base_validation_data, project_data])
