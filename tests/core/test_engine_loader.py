import subprocess
import sys

import pytest

from core.engine_loader import (
    discover_engine_names,
    discover_engines,
    load_engine,
)
from core.engine_registry import EngineRegistry
from core.exceptions import EngineNotRegisteredError


@pytest.fixture(autouse=True)
def reset_registry():
    EngineRegistry.reset()
    yield
    EngineRegistry.reset()


def test_discovery_reports_only_existing_engine_packages(monkeypatch, tmp_path):
    engines_dir = tmp_path / "engines"
    (engines_dir / "renpy").mkdir(parents=True)
    (engines_dir / "renpy" / "__init__.py").touch()
    (engines_dir / "helper.py").touch()

    import engines

    monkeypatch.setattr(engines, "__path__", [str(engines_dir)])

    assert discover_engine_names() == ["renpy"]


def test_cached_engine_module_can_restore_registry_after_reset():
    first = load_engine("renpy")
    EngineRegistry.reset()

    restored = load_engine("renpy")

    assert restored.name == first.name == "renpy"
    assert EngineRegistry.is_registered("renpy") is True


def test_missing_optional_engine_reports_available_names(monkeypatch):
    monkeypatch.setattr(
        "core.engine_loader.discover_engine_names",
        lambda: ["renpy"],
    )

    with pytest.raises(
        EngineNotRegisteredError,
        match="可用引擎: renpy",
    ):
        load_engine("naninovel")


def test_discovery_respects_project_allowlist():
    engines = discover_engines(["renpy"])

    assert list(engines) == ["renpy"]


def test_importing_core_does_not_import_optional_engine_configs():
    code = """
import sys

class BlockOptionalEngines:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith(('engines.naninovel', 'engines.utage')):
            raise RuntimeError(f'unexpected eager import: {fullname}')
        return None

sys.meta_path.insert(0, BlockOptionalEngines())
import core
assert 'NaninovelConfig' not in core.__all__
assert 'UtageConfig' not in core.__all__
"""

    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
