import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QCheckBox

from gui.controllers.tool_controller import ToolProcessController
from gui.tools import ToolCatalog
from gui.ui.tool_runner_page import ToolRunnerPage


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
    assert isinstance(dry_run, QCheckBox)
    assert dry_run.isChecked()
    assert "--dry-run" in page.command_preview.text()
    assert page.run_button.isEnabled()
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
