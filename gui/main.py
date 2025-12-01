"""
GUI 应用主入口
"""
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from gui.ui.main_window import MainWindowUI
from gui.controllers.scenario_controller import ScenarioController
from gui.controllers.param_controller import ParamController
from gui.controllers.resource_controller import ResourceController
from gui.utils.log_handler import QTextEditLogger
from gui.utils.styles import MODERN_STYLE
from core.config_manager import AppConfig
from core.logger import get_logger
import logging

logger = get_logger()


class MainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        super().__init__()

        # 设置窗口图标
        icon_path = Path(__file__).parent / "assets" / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # 设置 UI
        self.ui = MainWindowUI()
        self.ui.setup_ui(self)

        # 加载配置
        self.config = self._load_config()

        # 初始化控制器
        self.scenario_controller = ScenarioController(self, self.config)
        self.param_controller = ParamController(self, self.config)
        self.resource_controller = ResourceController(self, self.config)

        # 配置修改标记
        self.config_modified = False
        self._last_tab_index = 0

        # 设置日志处理器
        self._setup_log_handler()

        # 初始化 UI 状态
        self._init_ui_state()

        # 连接信号和槽
        self._connect_signals()

        logger.info("GUI 应用已启动")

    def _load_config(self) -> AppConfig:
        """加载配置文件"""
        config_path = Path("config.yaml")
        if not config_path.exists():
            logger.warning("配置文件不存在，使用默认配置")
            return AppConfig.from_dict({})
        return AppConfig.from_file(config_path)

    def _setup_log_handler(self):
        """设置日志处理器，将日志输出到GUI"""
        from core.logger import ColoredFormatter

        formatter = ColoredFormatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 为每个任务创建独立的日志处理器
        self.scenario_log_handler = QTextEditLogger()
        self.scenario_log_handler.setLevel(logging.INFO)
        self.scenario_log_handler.setFormatter(formatter)
        self.scenario_log_handler.log_signal.connect(self.ui.scenario_log.append)

        self.param_log_handler = QTextEditLogger()
        self.param_log_handler.setLevel(logging.INFO)
        self.param_log_handler.setFormatter(formatter)
        self.param_log_handler.log_signal.connect(self.ui.param_log.append)

        self.resource_log_handler = QTextEditLogger()
        self.resource_log_handler.setLevel(logging.INFO)
        self.resource_log_handler.setFormatter(formatter)
        self.resource_log_handler.log_signal.connect(self.ui.resource_log.append)

    def _init_ui_state(self):
        """初始化 UI 状态"""
        # 初始化引擎下拉框（从注册表获取）
        from core.engine_registry import EngineRegistry
        engines = EngineRegistry.list_engines()
        engine_names = [meta.display_name for meta in engines.values()]
        self.ui.param_engine_combo.clear()
        self.ui.param_engine_combo.addItems(engine_names)

        # 设置引擎类型（从engine_name查找display_name）
        engine_type = self.config.engine.engine_type
        engine_display_name = None
        for name, meta in engines.items():
            if name == engine_type:
                engine_display_name = meta.display_name
                break

        if engine_display_name:
            self.ui.scenario_engine_combo.setCurrentText(engine_display_name)
            self.ui.param_engine_combo.setCurrentText(engine_display_name)
            self.ui.config_engine_combo.setCurrentText(engine_display_name)

        # 设置路径
        self.ui.scenario_input_edit.setText(str(self.config.paths.input_dir))
        self.ui.scenario_output_edit.setText(str(self.config.paths.output_dir))

        # 设置参数映射页面的值
        self.ui.param_config_dir_edit.setText(str(self.config.paths.param_config_dir))
        self._update_param_file_labels()

        # 设置资源管理页面的值
        self.ui.resource_excel_edit.setText(str(self.config.paths.input_dir))
        self.ui.resource_project_edit.setText(str(self.config.resources.project_root))
        self.ui.resource_library_edit.setText(str(self.config.resources.source_root))

        # 设置配置页面的值
        self.ui.config_input_edit.setText(str(self.config.paths.input_dir))
        self.ui.config_output_edit.setText(str(self.config.paths.output_dir))
        self.ui.config_param_edit.setText(str(self.config.paths.param_config_dir))
        self.ui.config_log_edit.setText(str(self.config.paths.log_dir))
        self.ui.config_project_root_edit.setText(str(self.config.resources.project_root))
        self.ui.config_source_root_edit.setText(str(self.config.resources.source_root))
        self.ui.config_ignore_check.setChecked(self.config.processing.ignore_mode)
        self.ui.config_ignore_edit.setText(", ".join(self.config.processing.ignore_words))

    def _connect_signals(self):
        """连接信号和槽"""
        # === 脚本生成页面 ===
        # 忽略模式复选框
        self.ui.scenario_ignore_check.stateChanged.connect(
            lambda state: self.ui.scenario_ignore_edit.setEnabled(state == Qt.CheckState.Checked.value)
        )

        # 浏览按钮
        self.ui.scenario_input_btn.clicked.connect(self._browse_input_dir)
        self.ui.scenario_output_btn.clicked.connect(self._browse_output_dir)

        # 按钮
        self.ui.scenario_reset_btn.clicked.connect(self._on_reset_scenario)
        self.ui.scenario_generate_btn.clicked.connect(self._on_generate_scenario)

        # 控制器信号
        self.scenario_controller.worker_progress.connect(self._on_scenario_progress)
        self.scenario_controller.worker_finished.connect(self._on_scenario_finished)

        # === 参数映射页面 ===
        self.ui.param_engine_combo.currentTextChanged.connect(self._update_param_file_labels)
        self.ui.param_config_dir_edit.textChanged.connect(self._update_param_file_labels)
        self.ui.param_config_dir_btn.clicked.connect(self._browse_param_config_dir)
        self.ui.param_reset_btn.clicked.connect(self._on_reset_param)
        self.ui.param_update_btn.clicked.connect(self._on_update_param)

        # 控制器信号
        self.param_controller.worker_progress.connect(self._on_param_progress)
        self.param_controller.worker_finished.connect(self._on_param_finished)

        # === 资源管理页面 ===
        self.ui.resource_excel_btn.clicked.connect(self._browse_resource_excel)
        self.ui.resource_project_btn.clicked.connect(self._browse_resource_project)
        self.ui.resource_library_btn.clicked.connect(self._browse_resource_library)
        self.ui.resource_reset_btn.clicked.connect(self._on_reset_resource)
        self.ui.resource_validate_btn.clicked.connect(self._on_validate_resources)
        self.ui.resource_sync_btn.clicked.connect(self._on_sync_resources)

        # 控制器信号
        self.resource_controller.validate_progress.connect(self._on_resource_validate_progress)
        self.resource_controller.validate_finished.connect(self._on_resource_validate_finished)
        self.resource_controller.sync_progress.connect(self._on_resource_sync_progress)
        self.resource_controller.sync_finished.connect(self._on_resource_sync_finished)

        # === 配置页面 ===
        # 忽略模式复选框
        self.ui.config_ignore_check.stateChanged.connect(
            lambda state: self.ui.config_ignore_edit.setEnabled(state == Qt.CheckState.Checked.value)
        )

        self.ui.config_input_btn.clicked.connect(self._browse_config_input)
        self.ui.config_output_btn.clicked.connect(self._browse_config_output)
        self.ui.config_param_btn.clicked.connect(self._browse_config_param)
        self.ui.config_log_btn.clicked.connect(self._browse_config_log)
        self.ui.config_project_root_btn.clicked.connect(self._browse_config_project_root)
        self.ui.config_source_root_btn.clicked.connect(self._browse_config_source_root)
        self.ui.config_save_btn.clicked.connect(self._on_save_config)

        # 监听配置修改
        self.ui.config_input_edit.textChanged.connect(self._mark_config_modified)
        self.ui.config_output_edit.textChanged.connect(self._mark_config_modified)
        self.ui.config_param_edit.textChanged.connect(self._mark_config_modified)
        self.ui.config_log_edit.textChanged.connect(self._mark_config_modified)
        self.ui.config_project_root_edit.textChanged.connect(self._mark_config_modified)
        self.ui.config_source_root_edit.textChanged.connect(self._mark_config_modified)
        self.ui.config_ignore_edit.textChanged.connect(self._mark_config_modified)
        self.ui.config_ignore_check.stateChanged.connect(self._mark_config_modified)
        self.ui.config_engine_combo.currentTextChanged.connect(self._mark_config_modified)

        # 监听选项卡切换
        self.ui.tab_widget.currentChanged.connect(self._on_tab_changed)

    # === 脚本生成相关方法 ===
    def _on_reset_scenario(self):
        """恢复脚本生成选项卡的默认配置"""
        from core.engine_registry import EngineRegistry

        engines = EngineRegistry.list_engines()
        for name, meta in engines.items():
            if name == self.config.engine.engine_type:
                self.ui.scenario_engine_combo.setCurrentText(meta.display_name)
                break

        self.ui.scenario_input_edit.setText(str(self.config.paths.input_dir))
        self.ui.scenario_output_edit.setText(str(self.config.paths.output_dir))

    def _browse_input_dir(self):
        """浏览输入目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择输入目录", self.ui.scenario_input_edit.text())
        if dir_path:
            self.ui.scenario_input_edit.setText(dir_path)

    def _browse_output_dir(self):
        """浏览输出目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录", self.ui.scenario_output_edit.text())
        if dir_path:
            self.ui.scenario_output_edit.setText(dir_path)

    def _on_generate_scenario(self):
        """生成脚本"""
        from core.engine_registry import EngineRegistry
        from copy import deepcopy

        # 创建配置副本
        temp_config = deepcopy(self.config)

        # 更新临时配置的引擎
        engine_display_name = self.ui.scenario_engine_combo.currentText()
        engines = EngineRegistry.list_engines()
        for name, meta in engines.items():
            if meta.display_name == engine_display_name:
                temp_config.engine = meta.config_class(engine_type=name)
                break

        temp_config.paths.input_dir = Path(self.ui.scenario_input_edit.text())
        temp_config.paths.output_dir = Path(self.ui.scenario_output_edit.text())

        # 清空日志
        self.ui.scenario_log.clear()
        self.ui.scenario_progress.setValue(0)

        # 禁用按钮
        self.ui.scenario_generate_btn.setEnabled(False)

        # 使用临时配置开始生成
        self.scenario_controller.generate_scripts(temp_config)

    def _on_scenario_progress(self, message: str):
        """脚本生成进度更新"""
        self.ui.scenario_log.append(message)
        self.ui.status_bar.showMessage(message)

    def _on_scenario_finished(self, success: bool, message: str):
        """脚本生成完成"""
        self.ui.scenario_progress.setValue(100 if success else 0)
        self.ui.scenario_log.append(f"\n{'成功' if success else '失败'}: {message}")
        self.ui.scenario_generate_btn.setEnabled(True)

        # 显示消息框
        if success:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.critical(self, "失败", message)

    # === 参数映射相关方法 ===
    def _on_reset_param(self):
        """恢复参数映射选项卡的默认配置"""
        from core.engine_registry import EngineRegistry

        engines = EngineRegistry.list_engines()
        for name, meta in engines.items():
            if name == self.config.engine.engine_type:
                self.ui.param_engine_combo.setCurrentText(meta.display_name)
                break

        self.ui.param_config_dir_edit.setText(str(self.config.paths.param_config_dir))

    def _browse_param_config_dir(self):
        """浏览参数配置目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择参数配置目录", self.ui.param_config_dir_edit.text())
        if dir_path:
            self.ui.param_config_dir_edit.setText(dir_path)

    def _update_param_file_labels(self):
        """实时更新参数文件和差分文件的label"""
        from core.engine_registry import EngineRegistry

        # 获取当前引擎和参数配置目录
        engine_display_name = self.ui.param_engine_combo.currentText()
        param_dir = self.ui.param_config_dir_edit.text()

        # 从注册表查找引擎名称
        engines = EngineRegistry.list_engines()
        engine_name = None
        for name, meta in engines.items():
            if meta.display_name == engine_display_name:
                engine_name = name
                break

        # 根据引擎名称确定参数文件名
        if engine_name:
            param_file = f"param_data_{engine_name}.xlsx"
        else:
            param_file = "param_data.xlsx"

        # 更新label显示
        self.ui.param_file_label.setText(f"{param_dir}/{param_file}")
        self.ui.param_varient_label.setText(f"{param_dir}/varient_data.xlsx")

    def _on_update_param(self):
        """更新参数映射"""
        from core.engine_registry import EngineRegistry
        from copy import deepcopy

        # 创建配置副本
        temp_config = deepcopy(self.config)

        # 从UI更新临时配置
        temp_config.paths.param_config_dir = Path(self.ui.param_config_dir_edit.text())

        # 更新引擎配置（从display_name转换为engine_name）
        engine_display_name = self.ui.param_engine_combo.currentText()
        engines = EngineRegistry.list_engines()
        for name, meta in engines.items():
            if meta.display_name == engine_display_name:
                temp_config.engine = meta.config_class(engine_type=name)
                break

        # 清空日志
        self.ui.param_log.clear()
        self.ui.param_progress.setValue(0)

        # 禁用按钮
        self.ui.param_update_btn.setEnabled(False)

        # 使用临时配置开始更新
        self.param_controller.update_param_mappings(temp_config)

    def _on_param_progress(self, message: str):
        """参数映射进度更新"""
        self.ui.param_log.append(message)
        self.ui.status_bar.showMessage(message)

    def _on_param_finished(self, success: bool, message: str):
        """参数映射完成"""
        self.ui.param_progress.setValue(100 if success else 0)
        self.ui.param_log.append(f"\n{'成功' if success else '失败'}: {message}")
        self.ui.param_update_btn.setEnabled(True)

        # 显示消息框
        if success:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.critical(self, "失败", message)

    # === 资源管理相关方法 ===
    def _on_reset_resource(self):
        """恢复资源管理选项卡的默认配置"""
        self.ui.resource_excel_edit.setText(str(self.config.paths.input_dir))
        self.ui.resource_project_edit.setText(str(self.config.resources.project_root))
        self.ui.resource_library_edit.setText(str(self.config.resources.source_root))

    def _browse_resource_excel(self):
        """浏览 Excel 目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择 Excel 目录", self.ui.resource_excel_edit.text())
        if dir_path:
            self.ui.resource_excel_edit.setText(dir_path)

    def _browse_resource_project(self):
        """浏览项目库目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择项目库目录", self.ui.resource_project_edit.text())
        if dir_path:
            self.ui.resource_project_edit.setText(dir_path)

    def _browse_resource_library(self):
        """浏览资源库目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择资源库目录", self.ui.resource_library_edit.text())
        if dir_path:
            self.ui.resource_library_edit.setText(dir_path)

    def _on_validate_resources(self):
        """验证资源"""
        from copy import deepcopy

        # 创建配置副本
        temp_config = deepcopy(self.config)

        # 从UI更新临时配置
        temp_config.paths.input_dir = Path(self.ui.resource_excel_edit.text())
        temp_config.resources.project_root = Path(self.ui.resource_project_edit.text())
        temp_config.resources.source_root = Path(self.ui.resource_library_edit.text())

        # 清空日志
        self.ui.resource_log.clear()
        self.ui.resource_progress.setValue(0)

        # 禁用按钮
        self.ui.resource_validate_btn.setEnabled(False)

        # 使用临时配置开始验证
        self.resource_controller.validate_resources(temp_config)

    def _on_resource_validate_progress(self, message: str):
        """资源验证进度更新"""
        self.ui.resource_log.append(message)
        self.ui.status_bar.showMessage(message)

    def _on_resource_validate_finished(self, success: bool, message: str, missing_files: dict):
        """资源验证完成"""
        self.ui.resource_progress.setValue(100 if success else 0)
        self.ui.resource_log.append(f"\n{message}")
        self.ui.resource_validate_btn.setEnabled(True)

        # 验证成功后启用同步按钮
        if success:
            self.ui.resource_sync_btn.setEnabled(True)
            self.ui.resource_log.append(f"\n验证完成，可以点击'同步资源'按钮进行资源同步")
        else:
            self.ui.resource_sync_btn.setEnabled(False)

    def _on_sync_resources(self):
        """同步资源"""
        # 清空日志
        self.ui.resource_log.clear()
        self.ui.resource_progress.setValue(0)

        # 禁用按钮
        self.ui.resource_sync_btn.setEnabled(False)

        # 获取干跑模式状态
        dry_run = self.ui.resource_dry_run_check.isChecked()

        # 开始同步（从 JSON 报告读取数据）
        self.resource_controller.sync_resources(dry_run)

    def _on_resource_sync_progress(self, message: str):
        """资源同步进度更新"""
        self.ui.resource_log.append(message)
        self.ui.status_bar.showMessage(message)

    def _on_resource_sync_finished(self, success: bool, message: str):
        """资源同步完成"""
        self.ui.resource_progress.setValue(100 if success else 0)
        self.ui.resource_log.append(f"\n{'成功' if success else '失败'}: {message}")
        self.ui.resource_sync_btn.setEnabled(True)

        # 显示消息框
        if success:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.critical(self, "失败", message)

    # === 配置相关方法 ===
    def _reload_config_tab_ui(self):
        """重新加载配置选项卡的UI"""
        self.ui.config_input_edit.setText(str(self.config.paths.input_dir))
        self.ui.config_output_edit.setText(str(self.config.paths.output_dir))
        self.ui.config_param_edit.setText(str(self.config.paths.param_config_dir))
        self.ui.config_log_edit.setText(str(self.config.paths.log_dir))
        self.ui.config_project_root_edit.setText(str(self.config.resources.project_root))
        self.ui.config_source_root_edit.setText(str(self.config.resources.source_root))
        self.ui.config_ignore_check.setChecked(self.config.processing.ignore_mode)
        self.ui.config_ignore_edit.setText(", ".join(self.config.processing.ignore_words))

        from core.engine_registry import EngineRegistry
        engines = EngineRegistry.list_engines()
        for name, meta in engines.items():
            if name == self.config.engine.engine_type:
                self.ui.config_engine_combo.setCurrentText(meta.display_name)
                break

    def _browse_config_input(self):
        """浏览配置输入目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择输入目录", self.ui.config_input_edit.text())
        if dir_path:
            self.ui.config_input_edit.setText(dir_path)

    def _browse_config_output(self):
        """浏览配置输出目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择输出目录", self.ui.config_output_edit.text())
        if dir_path:
            self.ui.config_output_edit.setText(dir_path)

    def _browse_config_param(self):
        """浏览参数配置目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择参数配置目录", self.ui.config_param_edit.text())
        if dir_path:
            self.ui.config_param_edit.setText(dir_path)

    def _browse_config_log(self):
        """浏览日志目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择日志目录", self.ui.config_log_edit.text())
        if dir_path:
            self.ui.config_log_edit.setText(dir_path)

    def _browse_config_project_root(self):
        """浏览项目库目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择项目库目录", self.ui.config_project_root_edit.text())
        if dir_path:
            self.ui.config_project_root_edit.setText(dir_path)

    def _browse_config_source_root(self):
        """浏览资源库目录"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择资源库目录", self.ui.config_source_root_edit.text())
        if dir_path:
            self.ui.config_source_root_edit.setText(dir_path)

    def _on_save_config(self):
        """保存配置"""
        try:
            import yaml
            from core.engine_registry import EngineRegistry

            # 从UI读取配置
            engine_display_name = self.ui.config_engine_combo.currentText()
            ignore_words = [w.strip() for w in self.ui.config_ignore_edit.text().split(",")]

            # 从display_name转换为engine_name
            engines = EngineRegistry.list_engines()
            engine_name = None
            for name, meta in engines.items():
                if meta.display_name == engine_display_name:
                    engine_name = name
                    break

            config_dict = {
                "paths": {
                    "input_dir": self.ui.config_input_edit.text(),
                    "output_dir": self.ui.config_output_edit.text(),
                    "param_config_dir": self.ui.config_param_edit.text(),
                    "log_dir": self.ui.config_log_edit.text(),
                },
                "processing": {
                    "ignore_mode": self.ui.config_ignore_check.isChecked(),
                    "ignore_words": ignore_words,
                    "batch_size": 100,
                    "enable_progress_bar": True,
                },
                "engine": {
                    "engine_type": engine_name if engine_name else "renpy",
                },
                "resources": {
                    "project_root": self.ui.config_project_root_edit.text(),
                    "source_root": self.ui.config_source_root_edit.text(),
                    "extensions": self.config.resources.extensions,
                }
            }

            # 保存到文件
            with open("config.yaml", "w", encoding="utf-8") as f:
                yaml.dump(config_dict, f, allow_unicode=True, default_flow_style=False)

            # 重新加载配置
            self.config = self._load_config()
            self._init_ui_state()

            QMessageBox.information(self, "成功", "配置已保存")
            self.config_modified = False
        except Exception as e:
            QMessageBox.critical(self, "失败", f"保存配置失败: {str(e)}")

    def _mark_config_modified(self):
        """标记配置已修改"""
        self.config_modified = True

    def _on_tab_changed(self, index):
        """选项卡切换时检查配置是否保存"""
        # 如果从配置选项卡切换到其他选项卡，且配置已修改
        if self.config_modified and hasattr(self, '_last_tab_index') and self._last_tab_index == 3 and index != 3:
            # 先切回配置选项卡，阻止信号避免递归
            self.ui.tab_widget.blockSignals(True)
            self.ui.tab_widget.setCurrentIndex(3)
            self.ui.tab_widget.blockSignals(False)

            # 弹出对话框
            reply = QMessageBox.question(
                self,
                "未保存的配置",
                "当前配置未保存，是否保存？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )

            if reply == QMessageBox.StandardButton.Yes:
                self._on_save_config()
                # 保存后切换到目标选项卡
                self.ui.tab_widget.blockSignals(True)
                self.ui.tab_widget.setCurrentIndex(index)
                self.ui.tab_widget.blockSignals(False)
                self._last_tab_index = index
            elif reply == QMessageBox.StandardButton.No:
                # 不保存，重新加载配置并切换
                self.config_modified = False
                self._init_ui_state()
                self.ui.tab_widget.blockSignals(True)
                self.ui.tab_widget.setCurrentIndex(index)
                self.ui.tab_widget.blockSignals(False)
                self._last_tab_index = index
            # Cancel: 什么都不做，已经在配置选项卡了
            return

        # 进入配置选项卡时，只重新加载配置选项卡的UI
        if index == 3:
            self._reload_config_tab_ui()
            self.config_modified = False

        # 记录当前选项卡索引
        self._last_tab_index = index


def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 设置应用样式
    app.setStyle("Fusion")
    app.setStyleSheet(MODERN_STYLE)

    # 创建并显示主窗口
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
