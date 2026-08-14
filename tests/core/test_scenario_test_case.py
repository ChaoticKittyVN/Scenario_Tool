from pathlib import Path

import pandas as pd
import pytest

from core.config_manager import AppConfig
from core.scenario_test_case import ScenarioRangeCase, ScenarioTestCaseGenerator
from engines.naninovel.config import NaninovelConfig
from engines.renpy.config import RenpyConfig


class FakeExcelManager:
    def __init__(self, sheets):
        self.sheets = sheets

    def load_excel(self, _path):
        return self.sheets


class FakeOutputManager:
    def __init__(self):
        self.outputs = {}

    def output(self, data, output_path, **_kwargs):
        self.outputs[Path(output_path).name] = list(data)
        return True


class FakeTranslator:
    def __init__(self):
        self.contexts = []

    def set_context(self, file_name, sheet_name, row_index, scenario_index):
        self.contexts.append((file_name, sheet_name, row_index, scenario_index))


class StatefulProcessor:
    def __init__(self):
        self.seen = []

    def process_row(self, row):
        name = row.get("Name", "")
        text = row.get("Text", "")
        if name == "label":
            return [f"label {text}:"]
        self.seen.append(text)
        return [f"{len(self.seen)}:{text}"] if text else []


def make_config(tmp_path):
    config = AppConfig(engine=RenpyConfig())
    config.paths.output_dir = tmp_path / "output"
    config.paths.param_config_dir = tmp_path / "param_config"
    config.processing.ignore_mode = True
    config.processing.ignore_words = ["忽略"]
    return config


def source_dataframe():
    return pd.DataFrame(
        {
            "Index": ["A", "B", "C", "D", ""],
            "Name": ["Alice", "Alice", "Bob", "Bob", ""],
            "Text": ["第一行", "被忽略", "第三行", "第四行", ""],
            "Ignore": ["", "忽略", "", "", ""],
            "Note": ["", "", "", "", "END"],
        }
    )


def test_multiple_ranges_share_one_warmup_pass_and_preserve_excel_rows(tmp_path):
    output_manager = FakeOutputManager()
    processor = StatefulProcessor()
    generator = ScenarioTestCaseGenerator(
        make_config(tmp_path),
        excel_manager=FakeExcelManager({"Scene": source_dataframe()}),
        output_manager=output_manager,
        translator=FakeTranslator(),
        processor_factory=lambda: processor,
    )

    manifest = generator.generate(
        tmp_path / "scenario.xlsx",
        [
            ScenarioRangeCase("Scene", 4, 4),
            ScenarioRangeCase("Scene", 5, 5, label="Test01"),
        ],
        tmp_path / "cases",
    )

    assert processor.seen == ["第一行", "第三行", "第四行"]
    assert output_manager.outputs["Scene_R4-R4.rpy"] == ["2:第三行"]
    assert output_manager.outputs["Scene_R5-R5.rpy"] == [
        "label Test01:",
        "3:第四行",
    ]
    assert manifest["success"] is True


def test_context_range_reports_rows_removed_by_ignore_rules(tmp_path):
    output_manager = FakeOutputManager()
    generator = ScenarioTestCaseGenerator(
        make_config(tmp_path),
        excel_manager=FakeExcelManager({"Scene": source_dataframe()}),
        output_manager=output_manager,
        translator=FakeTranslator(),
        processor_factory=StatefulProcessor,
    )

    manifest = generator.generate(
        tmp_path / "scenario.xlsx",
        [ScenarioRangeCase("Scene", 4, 5, context_start=2)],
        tmp_path / "cases",
    )

    case = manifest["cases"][0]
    assert case["output_start"] == 2
    assert case["processed_rows"] == 3
    assert case["warmup_rows"] == 0
    assert case["output_rows"] == 3
    assert case["skipped_rows"] == [3]
    assert output_manager.outputs["Scene_R4-R5.rpy"] == [
        "1:第一行",
        "2:第三行",
        "3:第四行",
    ]


def test_range_must_end_before_end_marker(tmp_path):
    generator = ScenarioTestCaseGenerator(
        make_config(tmp_path),
        excel_manager=FakeExcelManager({"Scene": source_dataframe()}),
        output_manager=FakeOutputManager(),
        translator=FakeTranslator(),
        processor_factory=StatefulProcessor,
    )

    with pytest.raises(ValueError, match="必须早于 END"):
        generator.generate(
            tmp_path / "scenario.xlsx",
            [ScenarioRangeCase("Scene", 5, 6)],
            tmp_path / "cases",
        )


def test_sanitized_output_names_must_remain_unique(tmp_path):
    generator = ScenarioTestCaseGenerator(
        make_config(tmp_path),
        excel_manager=FakeExcelManager({"Scene": source_dataframe()}),
        output_manager=FakeOutputManager(),
        translator=FakeTranslator(),
        processor_factory=StatefulProcessor,
    )

    with pytest.raises(ValueError, match="输出文件名冲突"):
        generator.generate(
            tmp_path / "scenario.xlsx",
            [
                ScenarioRangeCase("Scene", 2, 2, name="Case:A"),
                ScenarioRangeCase("Scene", 4, 4, name="Case/A"),
            ],
            tmp_path / "cases",
        )


@pytest.mark.parametrize("label", ["01Test", "Test 01", "测试01"])
def test_label_must_be_a_portable_engine_identifier(label):
    with pytest.raises(ValueError, match="测试标签"):
        ScenarioRangeCase("Scene", 2, 3, label=label)


def test_target_only_and_warmup_modes_have_distinct_generator_state(tmp_path):
    config = AppConfig(engine=NaninovelConfig())
    config.paths.output_dir = tmp_path / "output"
    config.paths.param_config_dir = tmp_path / "param_config"
    config.processing.ignore_mode = False
    output_manager = FakeOutputManager()
    dataframe = pd.DataFrame(
        [
            {
                "Index": "A",
                "Character": "Alice",
                "Pose": "左",
                "Text": "",
                "Note": "",
            },
            {
                "Index": "B",
                "CharAnim": "Alice",
                "CharAnimParam": "JumpUp",
                "Text": "",
                "Note": "",
            },
            {"Index": "", "Text": "", "Note": "END"},
        ]
    )
    generator = ScenarioTestCaseGenerator(
        config,
        excel_manager=FakeExcelManager({"Scene": dataframe}),
        output_manager=output_manager,
    )

    manifest = generator.generate(
        tmp_path / "scenario.xlsx",
        [
            ScenarioRangeCase("Scene", 3, 3, name="warm", mode="warmup"),
            ScenarioRangeCase("Scene", 3, 3, name="cold", mode="target-only"),
        ],
        tmp_path / "cases",
    )

    assert any("position:-100,50" in line for line in output_manager.outputs["warm.nani"])
    assert any("position:0,50" in line for line in output_manager.outputs["cold.nani"])
    assert manifest["cases"][0]["warmup_rows"] == 1
    assert manifest["cases"][1]["warmup_rows"] == 0


def test_prefix_mode_outputs_from_replay_start(tmp_path):
    output_manager = FakeOutputManager()
    generator = ScenarioTestCaseGenerator(
        make_config(tmp_path),
        excel_manager=FakeExcelManager({"Scene": source_dataframe()}),
        output_manager=output_manager,
        translator=FakeTranslator(),
        processor_factory=StatefulProcessor,
    )

    manifest = generator.generate(
        tmp_path / "scenario.xlsx",
        [ScenarioRangeCase("Scene", 5, 5, mode="prefix", replay_start=4)],
        tmp_path / "cases",
    )

    assert output_manager.outputs["Scene_R5-R5.rpy"] == [
        "1:第三行",
        "2:第四行",
    ]
    assert manifest["cases"][0]["output_start"] == 4
    assert manifest["cases"][0]["replay_start"] == 4
