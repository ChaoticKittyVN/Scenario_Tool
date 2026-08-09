"""Naninovel-specific resource resolution."""
import re
from pathlib import Path
from typing import Dict, Optional

from core.resource_resolution import ResourceResolution


class NaninovelDeclarationResolver:
    """Resolve prefab members declared by a Naninovel controller file."""

    def __init__(
        self,
        project_root: Path,
        declaration_files: Dict[str, Dict[str, str]],
    ):
        self.project_root = Path(project_root)
        self.declaration_files = declaration_files
        self._declaration_cache: Dict[Path, str] = {}

    def resolve(
        self,
        folder: Path,
        resource_name: str,
        resource_type: str,
    ) -> Optional[ResourceResolution]:
        declarations = self.declaration_files.get(resource_type, {})
        normalized_name = resource_name.replace("\\", "/")
        if not declarations or "/" not in normalized_name:
            return None

        base_name, member_name = normalized_name.split("/", 1)
        declaration_value = declarations.get(base_name)
        if not declaration_value:
            return None

        base_prefab = folder / f"{base_name}.prefab"
        declaration_path = Path(declaration_value)
        if not declaration_path.is_absolute():
            declaration_path = self.project_root / declaration_path
        if not base_prefab.exists() or not declaration_path.exists():
            return None

        if declaration_path not in self._declaration_cache:
            self._declaration_cache[declaration_path] = declaration_path.read_text(
                encoding="utf-8",
                errors="ignore",
            )

        declaration_text = self._declaration_cache[declaration_path]
        pattern = rf"(?<![A-Za-z0-9_]){re.escape(member_name)}(?![A-Za-z0-9_])"
        if not re.search(pattern, declaration_text):
            return None

        return ResourceResolution(
            found_file=(
                f"{base_prefab.name}|"
                f"{declaration_path.name}#{member_name}"
            ),
            match_type="naninovel_declaration",
            match_label="Naninovel 声明",
        )


def create_naninovel_resource_resolver(project_root, engine_config):
    """Create the optional resolver registered with the Naninovel engine."""
    declaration_files = getattr(engine_config, "declaration_files", {})
    if not declaration_files:
        return None
    return NaninovelDeclarationResolver(project_root, declaration_files)
