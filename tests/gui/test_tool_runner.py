import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QPlainTextEdit

from gui.controllers.tool_controller import ToolProcessController
from gui.tools import ToolCatalog
from gui.ui.tool_runner_page import (
    ExecutionModeControl,
    PathArgumentEdit,
    ToolRunnerPage,
)


def application():
    return QApplication.instance() or QApplication([])


def test_tool_page_builds_dynamic_dry_run_control():
    app = application()
    repo_root = Path(__file__).resolve().parents[2]
    page = ToolRunnerPage(repo_root)
    smart_fill = next(
        tool for tool in page.catalog.discover() if tool.name == "smart_fill"
    )

    page.set_tool(smart_fill)

    dry_run = page.argument_widgets["dry_run"]
    assert isinstance(dry_run, ExecutionModeControl)
    assert dry_run.currentData() == "dry_run"
    assert "--dry-run" in page.command_preview.text()
    assert isinstance(page.argument_widgets["config"], PathArgumentEdit)
    assert set(page.argument_forms) == {"输入", "处理范围", "执行模式", "输出", "高级参数"}
    assert page.run_button.isEnabled()
    page.deleteLater()
    app.processEvents()


def test_workflow_page_uses_grouped_multi_value_inputs():
    app = application()
    repo_root = Path(__file__).resolve().parents[2]
    page = ToolRunnerPage(repo_root)
    workflow = next(
        tool for tool in page.catalog.discover() if tool.name == "run_workflow"
    )

    page.set_tool(workflow)

    assert page.title_label.text() == "批量工作流执行器"
    assert isinstance(page.argument_widgets["workflow"], PathArgumentEdit)
    assert isinstance(page.argument_widgets["step"], QPlainTextEdit)
    assert "python" not in page.argument_widgets
    assert "必填参数" in page.argument_forms
    assert "高级参数" in page.argument_forms
    page.deleteLater()
    app.processEvents()


def test_process_controller_executes_tool_and_streams_output(tmp_path):
    app = application()
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    script_path = tools_dir / "echo_tool.py"
    script_path.write_text(
        '"""Echo tool."""\nprint("tool-output")\n',
        encoding="utf-8",
    )
    descriptor = ToolCatalog(tools_dir).read(script_path)
    controller = ToolProcessController(tmp_path)
    output = []
    result = []
    loop = QEventLoop()
    controller.output_received.connect(output.append)
    controller.process_finished.connect(
        lambda success, code, message: (result.append((success, code, message)), loop.quit())
    )

    assert controller.run(descriptor, [])
    QTimer.singleShot(10000, loop.quit)
    loop.exec()

    assert result == [(True, 0, "执行完成")]
    assert "tool-output" in "".join(output)
    controller.deleteLater()
    app.processEvents()
