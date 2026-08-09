"""Shared contracts for engine-specific resource resolution."""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol


@dataclass(frozen=True)
class ResourceResolution:
    """A resource match returned by the core lookup or an engine resolver."""

    found_file: str
    match_type: str = "exact"
    match_label: str = ""


class ResourceResolver(Protocol):
    """Resolve resources represented by engine declarations instead of files."""

    def resolve(
        self,
        folder: Path,
        resource_name: str,
        resource_type: str,
    ) -> Optional[ResourceResolution]:
        ...
