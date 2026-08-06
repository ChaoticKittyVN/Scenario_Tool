from pathlib import Path

from gui.tools import ToolCatalog


SCRIPT = '''"""示例批处理工具

用于测试动态参数读取。
"""
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="输入目录")
    parser.add_argument("--dry-run", action="store_true", help="只预览")
    parser.add_argument("--format", choices=["excel", "csv"], default="excel")
    parser.add_argument("--columns", nargs="+", default=[])
    parser.add_argument("--set", action="append", default=[])
'''


def test_catalog_discovers_module_metadata_and_arguments(tmp_path):
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    (tools_dir / "__init__.py").write_text("", encoding="utf-8")
    (tools_dir / "_private.py").write_text("", encoding="utf-8")
    script_path = tools_dir / "sample_tool.py"
    script_path.write_text(SCRIPT, encoding="utf-8")

    tools = ToolCatalog(tools_dir).discover()

    assert len(tools) == 1
    tool = tools[0]
    assert tool.name == "sample_tool"
    assert tool.title == "示例批处理工具"
    assert tool.supports_dry_run
    arguments = {argument.dest: argument for argument in tool.arguments}
    assert arguments["input"].required
    assert arguments["input"].type_name == "Path"
    assert arguments["format"].choices == ("excel", "csv")
    assert arguments["columns"].takes_multiple


def test_descriptor_builds_argument_vector(tmp_path):
    script_path = tmp_path / "sample_tool.py"
    script_path.write_text(SCRIPT, encoding="utf-8")
    tool = ToolCatalog(tmp_path).read(script_path)

    arguments = tool.build_arguments(
        {
            "input": r"D:\project files\input",
            "dry_run": True,
            "format": "csv",
            "columns": 'Name "Text Value"',
            "set": "chapter=1,engine=renpy",
        },
        ["--verbose"],
    )

    assert arguments == [
        "--input",
        r"D:\project files\input",
        "--dry-run",
        "--format",
        "csv",
        "--columns",
        "Name",
        "Text Value",
        "--set",
        "chapter=1",
        "--set",
        "engine=renpy",
        "--verbose",
    ]


def test_real_tool_catalog_discovers_current_tools():
    repo_root = Path(__file__).resolve().parents[2]
    tools = {tool.name: tool for tool in ToolCatalog(repo_root / "tools").discover()}

    assert "smart_fill" in tools
    assert "run_workflow" in tools
    assert "fill_scenario_index" in tools
    assert tools["smart_fill"].supports_dry_run
    assert any(argument.dest == "config" for argument in tools["smart_fill"].arguments)
    assert tools["smart_fill"].title == "通用表格变更"
    assert tools["run_workflow"].title == "批量工作流执行器"

    smart_arguments = {argument.dest: argument for argument in tools["smart_fill"].arguments}
    workflow_arguments = {argument.dest: argument for argument in tools["run_workflow"].arguments}
    assert smart_arguments["config"].label == "规则文件"
    assert smart_arguments["config"].kind == "file"
    assert smart_arguments["report"].group == "输出"
    assert workflow_arguments["workflow"].required
    assert workflow_arguments["workflow"].kind == "file"
    assert workflow_arguments["python"].hidden is True


def test_invalid_ui_order_falls_back_to_argument_order(tmp_path):
    script = tmp_path / "sample.py"
    script.write_text(
        '''"""Sample tool."""
import argparse

TOOL_UI = {
    "arguments": {
        "value": {"label": "Value", "order": "not-a-number"},
    },
}

parser = argparse.ArgumentParser()
parser.add_argument("--value")
''',
        encoding="utf-8",
    )

    descriptor = ToolCatalog(tmp_path).read(script)

    assert descriptor.parse_error is None
    assert descriptor.arguments[0].label == "Value"
    assert descriptor.arguments[0].order == 100
