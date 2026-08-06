from pathlib import Path
from unittest.mock import Mock, patch

from core.config_manager import AppConfig
from engines.renpy.config import RenpyConfig
from generate_scenario import generate_scenarios


def generation_config(tmp_path: Path) -> AppConfig:
    config = AppConfig(engine=RenpyConfig())
    config.paths.input_dir = tmp_path / "input"
    config.paths.output_dir = tmp_path / "output"
    config.paths.param_config_dir = tmp_path / "param_config"
    config.paths.input_dir.mkdir()
    config.paths.param_config_dir.mkdir()
    return config


def test_generate_scenarios_shares_complete_batch_workflow(tmp_path):
    config = generation_config(tmp_path)
    first = config.paths.input_dir / "01.xlsx"
    second = config.paths.input_dir / "02.xlsx"
    first.touch()
    second.touch()
    translator = Mock()
    translator.get_untranslatable_count.return_value = 2
    translator.export_untranslatable_log.return_value = config.paths.output_dir / "missing.txt"
    progress = []

    with (
        patch("generate_scenario.import_engine_module") as import_engine,
        patch("generate_scenario.ParamTranslator", return_value=translator),
        patch("generate_scenario.create_processor", return_value=Mock()) as create_processor,
        patch("generate_scenario.process_excel_file") as process_file,
    ):
        summary = generate_scenarios(config, progress.append)

    assert summary.success
    assert summary.total_files == 2
    assert summary.succeeded_files == 2
    assert summary.failed_files == 0
    assert summary.untranslatable_count == 2
    import_engine.assert_called_once_with("renpy")
    create_processor.assert_called_once()
    assert process_file.call_count == 2
    assert progress[0] == "准备生成 2 个文件"
    assert progress[-1] == "生成完成：成功 2，失败 0"


def test_generate_scenarios_reports_partial_failure(tmp_path):
    config = generation_config(tmp_path)
    (config.paths.input_dir / "01.xlsx").touch()
    (config.paths.input_dir / "02.xlsx").touch()
    translator = Mock()
    translator.get_untranslatable_count.return_value = 0

    with (
        patch("generate_scenario.import_engine_module"),
        patch("generate_scenario.ParamTranslator", return_value=translator),
        patch("generate_scenario.create_processor", return_value=Mock()),
        patch(
            "generate_scenario.process_excel_file",
            side_effect=[None, RuntimeError("broken")],
        ),
    ):
        summary = generate_scenarios(config)

    assert not summary.success
    assert summary.succeeded_files == 1
    assert summary.failed_files == 1


def test_generate_scenarios_reports_missing_input(tmp_path):
    config = AppConfig(engine=RenpyConfig())
    config.paths.input_dir = tmp_path / "missing"
    config.paths.output_dir = tmp_path / "output"
    config.paths.param_config_dir = tmp_path / "param_config"

    summary = generate_scenarios(config)

    assert not summary.success
    assert "输入路径不存在" in summary.error
