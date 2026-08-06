"""Run dynamically discovered tools in an isolated child process."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, Signal

from gui.tools import ToolDescriptor


ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def format_command(program: str, arguments: Sequence[str]) -> str:
    return subprocess.list2cmdline([program, *arguments])


def resolve_python_executable() -> Path:
    executable = Path(sys.executable).resolve()
    if executable.stem.lower() == "pythonw":
        console_executable = executable.with_name("python.exe")
        if console_executable.exists():
            return console_executable
    return executable


class ToolProcessController(QObject):
    output_received = Signal(str)
    process_started = Signal(str)
    process_finished = Signal(bool, int, str)
    running_changed = Signal(bool)

    def __init__(self, repo_root: Path, parent: QObject | None = None):
        super().__init__(parent)
        self.repo_root = repo_root.resolve()
        self.python_executable = resolve_python_executable()
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._read_output)
        self.process.started.connect(self._on_started)
        self.process.finished.connect(self._on_finished)
        self.process.errorOccurred.connect(self._on_error)
        self._command = ""

    @property
    def is_running(self) -> bool:
        return self.process.state() != QProcess.ProcessState.NotRunning

    def run(self, tool: ToolDescriptor, arguments: Sequence[str]) -> bool:
        if self.is_running:
            return False
        program = str(self.python_executable)
        process_arguments = ["-B", str(tool.script_path), *arguments]
        self._command = format_command(program, process_arguments)
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("PYTHONIOENCODING", "utf-8")
        environment.insert("PYTHONUNBUFFERED", "1")
        self.process.setProcessEnvironment(environment)
        self.process.setWorkingDirectory(str(self.repo_root))
        self.process.setProgram(program)
        self.process.setArguments(process_arguments)
        self.process.start()
        return True

    def stop(self) -> None:
        if not self.is_running:
            return
        self.process.terminate()
        QTimer.singleShot(2500, self._kill_if_running)

    def shutdown(self, timeout_ms: int = 3000) -> None:
        if not self.is_running:
            return
        self.process.terminate()
        if not self.process.waitForFinished(timeout_ms):
            self.process.kill()
            self.process.waitForFinished(1000)

    def send_input(self, value: str) -> bool:
        if not self.is_running:
            return False
        self.process.write((value + "\n").encode("utf-8"))
        return True

    def _kill_if_running(self) -> None:
        if self.is_running:
            self.process.kill()

    def _read_output(self) -> None:
        raw = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if raw:
            self.output_received.emit(ANSI_ESCAPE.sub("", raw))

    def _on_started(self) -> None:
        self.running_changed.emit(True)
        self.process_started.emit(self._command)

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        self._read_output()
        success = (
            exit_status == QProcess.ExitStatus.NormalExit and exit_code == 0
        )
        if exit_status == QProcess.ExitStatus.CrashExit:
            message = "工具进程异常终止"
        elif success:
            message = "执行完成"
        else:
            message = f"工具返回退出码 {exit_code}"
        self.running_changed.emit(False)
        self.process_finished.emit(success, exit_code, message)

    def _on_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            message = f"无法启动工具进程: {self.process.errorString()}"
            self.output_received.emit(message + "\n")
            self.running_changed.emit(False)
            self.process_finished.emit(False, -1, message)
