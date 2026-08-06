from unittest.mock import Mock, patch

from core.config_manager import AppConfig
from engines.renpy.config import RenpyConfig
from generate_scenario import GenerationSummary
from gui.controllers.param_controller import ParamUpdateWorker
from gui.controllers.scenario_controller import ScenarioGeneratorWorker


def test_scenario_worker_uses_shared_generation_service():
    config = AppConfig(engine=RenpyConfig())
    worker = ScenarioGeneratorWorker(config)
    finished = []
    worker.finished.connect(lambda success, message: finished.append((success, message)))
    summary = GenerationSummary(total_files=2, succeeded_files=2)

    with patch(
        "gui.controllers.scenario_controller.generate_scenarios",
        return_value=summary,
    ) as generate:
        worker.run()

    generate.assert_called_once()
    assert generate.call_args.args[0] is config
    assert finished == [(True, "成功生成 2 个脚本")]


def test_param_worker_explicitly_runs_complete_update_flow():
    config = AppConfig(engine=RenpyConfig())
    worker = ParamUpdateWorker(config)
    finished = []
    worker.finished.connect(lambda success, message: finished.append((success, message)))
    updater = Mock()
    updater.update_mappings.return_value = True

    with patch("update_param.ParamUpdater", return_value=updater):
        worker.run()

    updater.update_mappings.assert_called_once_with(
        generate_mapping_files=True,
        update_parameter_sheets=True,
        dry_run=False,
    )
    assert finished == [(True, "参数映射与演出表格参数表更新成功")]


def test_param_worker_can_generate_mappings_without_syncing_sheets():
    config = AppConfig(engine=RenpyConfig())
    worker = ParamUpdateWorker(
        config,
        generate_mapping_files=True,
        update_parameter_sheets=False,
    )
    finished = []
    worker.finished.connect(lambda success, message: finished.append((success, message)))
    updater = Mock()
    updater.update_mappings.return_value = True

    with patch("update_param.ParamUpdater", return_value=updater):
        worker.run()

    updater.update_mappings.assert_called_once_with(
        generate_mapping_files=True,
        update_parameter_sheets=False,
        dry_run=False,
    )
    assert finished == [(True, "生成参数映射成功")]


def test_param_worker_can_sync_sheets_without_generating_mappings():
    config = AppConfig(engine=RenpyConfig())
    worker = ParamUpdateWorker(
        config,
        generate_mapping_files=False,
        update_parameter_sheets=True,
    )
    finished = []
    worker.finished.connect(lambda success, message: finished.append((success, message)))
    updater = Mock()
    updater.update_mappings.return_value = True

    with patch("update_param.ParamUpdater", return_value=updater):
        worker.run()

    updater.update_mappings.assert_called_once_with(
        generate_mapping_files=False,
        update_parameter_sheets=True,
        dry_run=False,
    )
    assert finished == [(True, "同步演出表参数表成功")]
