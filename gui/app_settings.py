"""Machine-local GUI settings kept outside the project configuration."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray, QSettings


class LocalGuiSettings:
    """Store per-machine GUI preferences without modifying config.yaml."""

    PYTHON_KEY = "tools/python_executable"
    GEOMETRY_KEY = "window/geometry"

    def __init__(self, backend: QSettings | None = None):
        self.backend = backend if backend is not None else QSettings("ChaoticKittyVN", "ScenarioTool")

    @property
    def python_executable(self) -> Path | None:
        value = self.backend.value(self.PYTHON_KEY, "", type=str).strip()
        return Path(value) if value else None

    def set_python_executable(self, executable: Path | None) -> None:
        if executable is None:
            self.backend.remove(self.PYTHON_KEY)
        else:
            self.backend.setValue(self.PYTHON_KEY, str(Path(executable).resolve()))
        self.backend.sync()

    @property
    def window_geometry(self) -> QByteArray | None:
        value = self.backend.value(self.GEOMETRY_KEY)
        return value if isinstance(value, QByteArray) and not value.isEmpty() else None

    def set_window_geometry(self, geometry: QByteArray) -> None:
        self.backend.setValue(self.GEOMETRY_KEY, geometry)
        self.backend.sync()
