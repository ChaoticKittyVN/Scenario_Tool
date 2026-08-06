import json
import sys
from pathlib import Path

import pytest
import yaml

from tools.run_workflow import WorkflowError, WorkflowRunner, load_workflow


HELPER_SCRIPT = """
import json
import pathlib
import sys

output = pathlib.Path(sys.argv[1])
record = {
    "args": sys.argv[2:],
    "stdin": sys.stdin.read(),
}
with output.open("a", encoding="utf-8") as stream:
    stream.write(json.dumps(record, ensure_ascii=False) + "\\n")

if "--fail" in sys.argv:
    raise SystemExit(3)
"""


def write_workflow(tmp_path: Path, data: dict) -> Path:
    workflow_path = tmp_path / "workflow.yaml"
    workflow_path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return workflow_path


def read_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_load_workflow_requires_one_entrypoint(tmp_path):
    workflow_path = write_workflow(
        tmp_path,
        {
            "version": 1,
            "steps": [
                {
                    "id": "invalid",
                    "script": "one.py",
                    "module": "tools.two",
                }
            ],
        },
    )

    with pytest.raises(WorkflowError, match="必须且只能指定"):
        load_workflow(workflow_path)


def test_dry_run_executes_safe_preview_and_skips_unsafe_step(tmp_path):
    helper = tmp_path / "helper.py"
    helper.write_text(HELPER_SCRIPT, encoding="utf-8")
    output = tmp_path / "records.jsonl"
    workflow_path = write_workflow(
        tmp_path,
        {
            "version": 1,
            "name": "preview-test",
            "variables": {"output": str(output)},
            "steps": [
                {
                    "id": "safe",
                    "script": "helper.py",
                    "args": ["{output}", "base"],
                    "dry_run_args": ["--preview"],
                    "dry_run_stdin": "",
                },
                {
                    "id": "unsafe",
                    "script": "helper.py",
                    "args": ["{output}", "write"],
                },
            ],
        },
    )

    runner = WorkflowRunner(
        workflow=load_workflow(workflow_path),
        workflow_path=workflow_path,
        mode="dry-run",
        python_executable=Path(sys.executable),
        repo_root=tmp_path,
    )
    report = runner.run()

    assert report["status"] == "success"
    assert report["counts"] == {"success": 1, "failed": 0, "skipped": 1}
    assert read_records(output) == [{"args": ["base", "--preview"], "stdin": ""}]
    assert report["results"][1]["reason"] == "no_safe_preview"


def test_apply_expands_targets_and_formats_target_variables(tmp_path):
    helper = tmp_path / "helper.py"
    helper.write_text(HELPER_SCRIPT, encoding="utf-8")
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "a.xlsx").touch()
    (input_dir / "b.xlsx").touch()
    (input_dir / "~temp.xlsx").touch()
    output = tmp_path / "records.jsonl"
    workflow_path = write_workflow(
        tmp_path,
        {
            "version": 1,
            "name": "target-test",
            "variables": {"output": str(output)},
            "targets": ["input/*.xlsx"],
            "steps": [
                {
                    "id": "per-target",
                    "script": "helper.py",
                    "for_each": "targets",
                    "args": ["{output}", "{target}", "{target_name}"],
                    "apply_stdin": "yes\n",
                }
            ],
        },
    )

    runner = WorkflowRunner(
        workflow=load_workflow(workflow_path),
        workflow_path=workflow_path,
        mode="apply",
        python_executable=Path(sys.executable),
        repo_root=tmp_path,
    )
    report = runner.run()

    assert report["counts"] == {"success": 2, "failed": 0, "skipped": 0}
    records = read_records(output)
    assert [record["args"] for record in records] == [
        ["input\\a.xlsx", "a.xlsx"],
        ["input\\b.xlsx", "b.xlsx"],
    ]
    assert all(record["stdin"] == "yes\n" for record in records)


def test_failure_stops_following_steps_by_default(tmp_path):
    helper = tmp_path / "helper.py"
    helper.write_text(HELPER_SCRIPT, encoding="utf-8")
    output = tmp_path / "records.jsonl"
    workflow_path = write_workflow(
        tmp_path,
        {
            "version": 1,
            "variables": {"output": str(output)},
            "steps": [
                {
                    "id": "failure",
                    "script": "helper.py",
                    "args": ["{output}", "--fail"],
                    "apply_stdin": "",
                },
                {
                    "id": "after",
                    "script": "helper.py",
                    "args": ["{output}", "after"],
                    "apply_stdin": "",
                },
            ],
        },
    )

    runner = WorkflowRunner(
        workflow=load_workflow(workflow_path),
        workflow_path=workflow_path,
        mode="apply",
        python_executable=Path(sys.executable),
        repo_root=tmp_path,
    )
    report = runner.run()

    assert report["status"] == "failed"
    assert report["counts"] == {"success": 0, "failed": 1, "skipped": 1}
    assert report["results"][1]["reason"] == "previous_failure"
    assert len(read_records(output)) == 1
