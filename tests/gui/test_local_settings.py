from pathlib import Path
import sys

from PySide6.QtCore import QByteArray, QSettings

from gui.controllers.tool_controller import (
    inspect_python_executable,
    resolve_python_executable,
)
from gui.app_settings import LocalGuiSettings


def local_settings(tmp_path):
    backend = QSettings(
        str(tmp_path / "gui-settings.ini"),
        QSettings.Format.IniFormat,
    )
    backend.clear()
    return LocalGuiSettings(backend)


def test_local_settings_store_python_outside_project_config(tmp_path):
    settings = local_settings(tmp_path)
    executable = Path(sys.executable).resolve()

    settings.set_python_executable(executable)

    assert settings.python_executable == executable
    assert not (tmp_path / "config.yaml").exists()

    settings.set_python_executable(None)
    assert settings.python_executable is None


def test_local_settings_round_trip_window_geometry(tmp_path):
    settings = local_settings(tmp_path)
    geometry = QByteArray(b"window-geometry")

    settings.set_window_geometry(geometry)

    assert settings.window_geometry == geometry


def test_python_resolution_and_validation():
    executable = Path(sys.executable).resolve()

    assert resolve_python_executable(executable) == executable
    success, version = inspect_python_executable(executable)

    assert success is True
    assert version.startswith("Python ")
