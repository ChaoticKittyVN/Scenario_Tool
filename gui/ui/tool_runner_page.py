"""Dynamic GUI page for discovering and executing scripts from tools/."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStyle,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from gui.controllers.tool_controller import ToolProcessController, format_command
from gui.tools import ToolArgument, ToolCatalog, ToolDescriptor


class PathArgumentEdit(QWidget):
    textChanged = Signal(str)

    def __init__(
        self,
        kind: str,
        file_filter: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.kind = kind
        self.file_filter = file_filter or "All files (*)"
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.edit = QLineEdit()
        self.edit.textChanged.connect(self.textChanged)
        layout.addWidget(self.edit, 1)
        self.browse_button = QPushButton()
        self.browse_button.setObjectName("iconButton")
        self.browse_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.browse_button.setToolTip("选择路径")
        self.browse_button.setFixedSize(32, 32)
        self.browse_button.clicked.connect(self._browse)
        layout.addWidget(self.browse_button)

    def text(self) -> str:
        return self.edit.text()

    def setPlaceholderText(self, text: str) -> None:
        self.edit.setPlaceholderText(text)

    def _browse(self) -> None:
        current = self.edit.text().strip()
        start = current or str(Path.cwd())
        if self.kind == "directory":
            selected = QFileDialog.getExistingDirectory(self, "选择目录", start)
        elif self.kind == "save_file":
            selected, _ = QFileDialog.getSaveFileName(self, "选择输出文件", start, self.file_filter)
        else:
            selected, _ = QFileDialog.getOpenFileName(self, "选择文件", start, self.file_filter)
        if selected:
            self.edit.setText(selected)


class ExecutionModeControl(QComboBox):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.addItem("安全预览（不写入文件）", "dry_run")
        self.addItem("实际执行（会写入文件）", "apply")


class ToolRunnerPage(QWidget):
    status_changed = Signal(str)

    def __init__(
        self,
        repo_root: Path,
        parent: QWidget | None = None,
        python_executable: Path | str | None = None,
    ):
        super().__init__(parent)
        self.repo_root = repo_root.resolve()
        self.catalog = ToolCatalog(self.repo_root / "tools")
        self.controller = ToolProcessController(
            self.repo_root,
            self,
            python_executable=python_executable,
        )
        self.current_tool: ToolDescriptor | None = None
        self.argument_widgets: dict[str, QWidget] = {}
        self.argument_forms: dict[str, QFormLayout] = {}
        self._setup_ui()
        self._connect_signals()
        self.refresh_tools()

    def set_python_executable(self, executable: Path | str | None) -> None:
        self.controller.set_python_executable(executable)
        self._update_command_preview()

    def _setup_ui(self) -> None:
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(12, 12, 12, 12)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        root_layout.addWidget(splitter)

        catalog_panel = QWidget()
        catalog_panel.setObjectName("toolPanel")
        catalog_panel.setMinimumWidth(230)
        catalog_panel.setMaximumWidth(320)
        catalog_layout = QVBoxLayout(catalog_panel)
        catalog_layout.setContentsMargins(0, 0, 8, 0)

        catalog_header = QHBoxLayout()
        catalog_title = QLabel("工具目录")
        catalog_title.setObjectName("sectionTitle")
        catalog_header.addWidget(catalog_title)
        catalog_header.addStretch()
        self.refresh_button = QPushButton()
        self.refresh_button.setObjectName("iconButton")
        self.refresh_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.refresh_button.setToolTip("重新扫描 tools 目录")
        self.refresh_button.setFixedSize(32, 32)
        catalog_header.addWidget(self.refresh_button)
        catalog_layout.addLayout(catalog_header)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("筛选工具")
        self.search_edit.setClearButtonEnabled(True)
        catalog_layout.addWidget(self.search_edit)

        self.tool_list = QListWidget()
        self.tool_list.setSpacing(2)
        catalog_layout.addWidget(self.tool_list, 1)
        splitter.addWidget(catalog_panel)

        detail_panel = QWidget()
        detail_panel.setObjectName("toolPanel")
        detail_layout = QVBoxLayout(detail_panel)
        detail_layout.setContentsMargins(8, 0, 0, 0)
        detail_layout.setSpacing(10)

        self.title_label = QLabel("选择一个工具")
        self.title_label.setObjectName("pageTitle")
        detail_layout.addWidget(self.title_label)

        self.path_label = QLabel()
        self.path_label.setObjectName("mutedLabel")
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        detail_layout.addWidget(self.path_label)

        self.description_view = QTextBrowser()
        self.description_view.setMaximumHeight(92)
        self.description_view.setOpenExternalLinks(False)
        detail_layout.addWidget(self.description_view)

        argument_header = QHBoxLayout()
        argument_title = QLabel("参数")
        argument_title.setObjectName("sectionTitle")
        argument_header.addWidget(argument_title)
        argument_header.addStretch()
        self.preview_badge = QLabel()
        self.preview_badge.setObjectName("statusBadge")
        argument_header.addWidget(self.preview_badge)
        detail_layout.addLayout(argument_header)

        self.argument_container = QWidget()
        self.argument_container.setObjectName("argumentContainer")
        self.argument_layout = QVBoxLayout(self.argument_container)
        self.argument_layout.setContentsMargins(8, 4, 8, 8)
        self.argument_layout.setSpacing(8)
        self.argument_layout.addStretch()
        argument_scroll = QScrollArea()
        argument_scroll.setWidgetResizable(True)
        argument_scroll.setWidget(self.argument_container)
        argument_scroll.setMinimumHeight(150)
        argument_scroll.setMaximumHeight(285)
        detail_layout.addWidget(argument_scroll)

        extra_layout = QHBoxLayout()
        extra_layout.addWidget(QLabel("附加参数:"))
        self.extra_arguments = QPlainTextEdit()
        self.extra_arguments.setPlaceholderText("每行一个参数，例如：\n--verbose")
        self.extra_arguments.setMaximumHeight(66)
        extra_layout.addWidget(self.extra_arguments, 1)
        detail_layout.addLayout(extra_layout)

        preview_layout = QHBoxLayout()
        preview_layout.addWidget(QLabel("命令:"))
        self.command_preview = QLineEdit()
        self.command_preview.setReadOnly(True)
        preview_layout.addWidget(self.command_preview, 1)
        detail_layout.addLayout(preview_layout)

        action_layout = QHBoxLayout()
        self.run_button = QPushButton("执行")
        self.run_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.run_button.setMinimumHeight(36)
        self.run_button.setEnabled(False)
        action_layout.addWidget(self.run_button)
        self.stop_button = QPushButton("停止")
        self.stop_button.setObjectName("secondaryButton")
        self.stop_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.stop_button.setMinimumHeight(36)
        self.stop_button.setEnabled(False)
        action_layout.addWidget(self.stop_button)
        action_layout.addStretch()
        self.clear_button = QPushButton("清空输出")
        self.clear_button.setObjectName("secondaryButton")
        action_layout.addWidget(self.clear_button)
        detail_layout.addLayout(action_layout)

        self.output_edit = QPlainTextEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setPlaceholderText("工具输出会显示在这里")
        self.output_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        detail_layout.addWidget(self.output_edit, 1)

        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("输入:"))
        self.stdin_edit = QLineEdit()
        self.stdin_edit.setPlaceholderText("用于回答工具的 y/N 等交互提示")
        self.stdin_edit.setEnabled(False)
        input_layout.addWidget(self.stdin_edit, 1)
        self.send_button = QPushButton("发送")
        self.send_button.setObjectName("secondaryButton")
        self.send_button.setEnabled(False)
        input_layout.addWidget(self.send_button)
        detail_layout.addLayout(input_layout)

        splitter.addWidget(detail_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 720])

    def _connect_signals(self) -> None:
        self.refresh_button.clicked.connect(self.refresh_tools)
        self.search_edit.textChanged.connect(self._filter_tools)
        self.tool_list.currentItemChanged.connect(self._select_item)
        self.extra_arguments.textChanged.connect(self._update_command_preview)
        self.run_button.clicked.connect(self._run_current_tool)
        self.stop_button.clicked.connect(self.controller.stop)
        self.clear_button.clicked.connect(self.output_edit.clear)
        self.send_button.clicked.connect(self._send_input)
        self.stdin_edit.returnPressed.connect(self._send_input)
        self.controller.output_received.connect(self._append_output)
        self.controller.process_started.connect(self._on_process_started)
        self.controller.process_finished.connect(self._on_process_finished)
        self.controller.running_changed.connect(self._set_running)

    def refresh_tools(self) -> None:
        previous_name = self.current_tool.name if self.current_tool else None
        self.tool_list.clear()
        for descriptor in self.catalog.discover():
            item = QListWidgetItem(descriptor.title)
            item.setToolTip(descriptor.script_path.name)
            item.setData(Qt.ItemDataRole.UserRole, descriptor)
            self.tool_list.addItem(item)
            if descriptor.name == previous_name:
                self.tool_list.setCurrentItem(item)
        self._filter_tools(self.search_edit.text())
        if self.tool_list.currentItem() is None and self.tool_list.count():
            self.tool_list.setCurrentRow(0)
        self.status_changed.emit(f"已发现 {self.tool_list.count()} 个工具")

    def _filter_tools(self, text: str) -> None:
        query = text.strip().lower()
        for index in range(self.tool_list.count()):
            item = self.tool_list.item(index)
            descriptor = item.data(Qt.ItemDataRole.UserRole)
            haystack = f"{descriptor.name} {descriptor.title} {descriptor.description}".lower()
            item.setHidden(bool(query and query not in haystack))

    def _select_item(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        descriptor = current.data(Qt.ItemDataRole.UserRole) if current else None
        self.set_tool(descriptor)

    def set_tool(self, descriptor: ToolDescriptor | None) -> None:
        self.current_tool = descriptor
        self._clear_form()
        if descriptor is None:
            self.title_label.setText("选择一个工具")
            self.path_label.clear()
            self.description_view.clear()
            self.run_button.setEnabled(False)
            self.command_preview.clear()
            return
        self.title_label.setText(descriptor.title)
        self.path_label.setText(str(descriptor.script_path.relative_to(self.repo_root)))
        description = descriptor.description or "该脚本没有模块说明。"
        if descriptor.parse_error:
            description += f"\n\n参数解析失败：{descriptor.parse_error}"
        self.description_view.setPlainText(description)
        visible_arguments = [argument for argument in descriptor.arguments if not argument.hidden]
        mode_arguments = {argument.dest: argument for argument in visible_arguments}
        mode_added = False
        for argument in visible_arguments:
            if argument.dest in ("dry_run", "apply") and {"dry_run", "apply"} <= mode_arguments.keys():
                if not mode_added:
                    self._add_execution_mode_control(
                        mode_arguments["dry_run"],
                        mode_arguments["apply"],
                    )
                    mode_added = True
                continue
            self._add_argument_control(argument)
        if not visible_arguments:
            empty_label = QLabel("该工具未声明命令行参数，可直接执行或使用下方附加参数。")
            empty_label.setObjectName("mutedLabel")
            self.argument_layout.insertWidget(0, empty_label)
        self.preview_badge.setText("支持安全预览" if descriptor.supports_dry_run else "执行前确认")
        self.run_button.setEnabled(not descriptor.parse_error and not self.controller.is_running)
        self._update_command_preview()

    def _clear_form(self) -> None:
        while self.argument_layout.count():
            item = self.argument_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.argument_widgets.clear()
        self.argument_forms.clear()

    def _form_for_group(self, group_name: str) -> QFormLayout:
        if group_name in self.argument_forms:
            return self.argument_forms[group_name]
        group = QGroupBox(group_name)
        form = QFormLayout(group)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)
        self.argument_layout.addWidget(group)
        self.argument_forms[group_name] = form
        return form

    @staticmethod
    def _label_text(argument: ToolArgument) -> str:
        required = " *" if argument.required else ""
        return f"{argument.display_label}{required}  [{argument.display_type}]"

    def _add_execution_mode_control(
        self,
        dry_run: ToolArgument,
        apply: ToolArgument,
    ) -> None:
        control = ExecutionModeControl()
        control.setToolTip(f"{dry_run.help}\n{apply.help}".strip())
        control.currentIndexChanged.connect(self._update_command_preview)
        self.argument_widgets["dry_run"] = control
        self.argument_widgets["apply"] = control
        self._form_for_group(dry_run.group).addRow("执行方式  [模式]", control)

    def _add_argument_control(self, argument: ToolArgument) -> None:
        label_text = self._label_text(argument)
        placeholder = argument.placeholder or argument.help
        if argument.is_boolean:
            widget: QWidget = QCheckBox("启用")
        elif argument.choices:
            combo = QComboBox()
            combo.addItem("使用脚本默认值", None)
            for choice in argument.choices:
                combo.addItem(str(choice), str(choice))
            widget = combo
        elif argument.kind in ("file", "save_file", "directory"):
            path_edit = PathArgumentEdit(argument.kind, argument.file_filter)
            path_edit.setPlaceholderText(placeholder)
            widget = path_edit
        elif argument.takes_multiple or argument.action == "append":
            values_edit = QPlainTextEdit()
            values_edit.setPlaceholderText(placeholder or "每行一个值")
            values_edit.setFixedHeight(62)
            widget = values_edit
        else:
            edit = QLineEdit()
            if argument.default not in (None, "", False):
                placeholder = f"默认: {argument.default}" + (f" | {placeholder}" if placeholder else "")
            edit.setPlaceholderText(placeholder)
            widget = edit
        tooltip = f"命令行参数: {argument.option}"
        if argument.help:
            tooltip += f"\n{argument.help}"
        widget.setToolTip(tooltip)
        self.argument_widgets[argument.dest] = widget
        self._form_for_group(argument.group).addRow(label_text, widget)
        if isinstance(widget, QCheckBox):
            widget.toggled.connect(self._update_command_preview)
        elif isinstance(widget, QComboBox):
            widget.currentIndexChanged.connect(self._update_command_preview)
        elif isinstance(widget, QLineEdit):
            widget.textChanged.connect(self._update_command_preview)
        elif isinstance(widget, PathArgumentEdit):
            widget.textChanged.connect(self._update_command_preview)
        elif isinstance(widget, QPlainTextEdit):
            widget.textChanged.connect(self._update_command_preview)

    def _collect_values(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for dest, widget in self.argument_widgets.items():
            if isinstance(widget, ExecutionModeControl):
                values[dest] = widget.currentData() == dest
            elif isinstance(widget, QCheckBox):
                values[dest] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                values[dest] = widget.currentData()
            elif isinstance(widget, QLineEdit):
                values[dest] = widget.text().strip()
            elif isinstance(widget, PathArgumentEdit):
                values[dest] = widget.text().strip()
            elif isinstance(widget, QPlainTextEdit):
                values[dest] = [
                    line.strip()
                    for line in widget.toPlainText().splitlines()
                    if line.strip()
                ]
        return values

    def _extra_arguments(self) -> list[str]:
        return [line.strip() for line in self.extra_arguments.toPlainText().splitlines() if line.strip()]

    def _arguments(self) -> list[str]:
        if not self.current_tool:
            return []
        return self.current_tool.build_arguments(self._collect_values(), self._extra_arguments())

    def _update_command_preview(self, *_args) -> None:
        if not self.current_tool:
            self.command_preview.clear()
            return
        arguments = ["-B", str(self.current_tool.script_path), *self._arguments()]
        self.command_preview.setText(
            format_command(str(self.controller.python_executable), arguments)
        )

    def _run_current_tool(self) -> None:
        if not self.current_tool:
            return
        values = self._collect_values()
        missing = [
            argument.option
            for argument in self.current_tool.arguments
            if argument.required and values.get(argument.dest) in (None, "", False)
        ]
        if missing:
            QMessageBox.warning(self, "缺少参数", "请填写必需参数：" + ", ".join(missing))
            return
        dry_run = bool(values.get("dry_run"))
        if not dry_run:
            reply = QMessageBox.question(
                self,
                "确认执行",
                "当前命令不是预览模式，工具可能写入文件或生成输出。是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self.output_edit.clear()
        if not self.controller.run(self.current_tool, self._arguments()):
            QMessageBox.warning(self, "工具运行中", "请先等待当前工具结束或停止它。")

    def _set_running(self, running: bool) -> None:
        self.run_button.setEnabled(not running and self.current_tool is not None)
        self.stop_button.setEnabled(running)
        self.refresh_button.setEnabled(not running)
        self.tool_list.setEnabled(not running)
        self.stdin_edit.setEnabled(running)
        self.send_button.setEnabled(running)

    def _on_process_started(self, command: str) -> None:
        self._append_output(f"> {command}\n\n")
        self.status_changed.emit("工具正在运行")

    def _on_process_finished(self, success: bool, exit_code: int, message: str) -> None:
        status = "成功" if success else "失败"
        self._append_output(f"\n[{status}] {message} (exit {exit_code})\n")
        self.status_changed.emit(message)

    def _append_output(self, text: str) -> None:
        cursor = self.output_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        self.output_edit.setTextCursor(cursor)
        self.output_edit.ensureCursorVisible()

    def _send_input(self) -> None:
        value = self.stdin_edit.text()
        if value and self.controller.send_input(value):
            self._append_output(f"> {value}\n")
            self.stdin_edit.clear()

    def stop(self) -> None:
        self.controller.stop()

    def shutdown(self) -> None:
        self.controller.shutdown()
