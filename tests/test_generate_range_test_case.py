from pathlib import Path

import pytest

from core.engine_loader import load_engine
from core.param_process.param_translator import ParamTranslator
from tools.generate_range_test_case import build_cli_cases, load_plan, parse_range


def test_parse_multiple_range_forms():
    assert parse_range("ch09:120-140") == ("ch09", 120, 140, None)
    assert parse_range("ch09:250-275@230") == ("ch09", 250, 275, 230)


def test_cli_cases_can_add_sequential_test_labels():
    cases = build_cli_cases(
        [parse_range("ch09:120-140"), parse_range("ch09:250-275")],
        with_label=True,
        label_prefix="Test",
    )

    assert [case.label for case in cases] == ["Test01", "Test02"]


def test_cli_cases_apply_execution_mode_and_replay_start():
    cases = build_cli_cases(
        [parse_range("ch09:120-140")],
        with_label=False,
        label_prefix="Test",
        mode="prefix",
        replay_start=100,
    )

    assert cases[0].effective_mode == "prefix"
    assert cases[0].effective_replay_start == 100
    assert cases[0].output_start_row == 100


def test_load_yaml_plan_supports_named_context_cases(tmp_path):
    plan = tmp_path / "plan.yaml"
    plan.write_text(
        """
input: input/ch09.xlsx
output_dir: output/test_cases
cases:
  - name: camera_move
    sheet: ch09
    rows: 120-140
    context_start: 100
    label: TestCamera
    mode: context
    replay_start: 80
  - sheet: ch09
    rows: 250-275
""".strip(),
        encoding="utf-8",
    )

    input_path, output_dir, cases = load_plan(plan)

    assert input_path == Path("input/ch09.xlsx")
    assert output_dir == Path("output/test_cases")
    assert cases[0].case_name == "camera_move"
    assert cases[0].context_start == 100
    assert cases[0].label == "TestCamera"
    assert cases[0].effective_mode == "context"
    assert cases[0].effective_replay_start == 80
    assert cases[1].label is None


@pytest.mark.parametrize(
    ("engine_name", "expected"),
    [
        ("renpy", "label Test01:"),
        ("naninovel", "# Test01"),
        ("utage", {"Command": "*Test01"}),
    ],
)
def test_existing_engine_generators_support_synthetic_label_rows(
    engine_name,
    expected,
    tmp_path,
):
    metadata = load_engine(engine_name)
    translator = ParamTranslator(
        str(tmp_path / "missing_mappings.py"),
        str(tmp_path / "missing_variants.py"),
    )
    processor = metadata.processor_factory(metadata.config_class(), translator)

    import pandas as pd

    row = pd.Series({"Name": "label", "Text": "Test01"})
    commands = processor.process_row(row)

    assert expected in commands
