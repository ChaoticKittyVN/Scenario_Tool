"""
主窗口 UI 设计
使用代码方式创建 UI，便于维护和修改
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QLineEdit, QPushButton,
    QComboBox, QCheckBox, QTextEdit, QProgressBar,
    QGroupBox, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt
from gui.utils.drag_drop_widgets import DragDropLineEdit


class MainWindowUI:
    """主窗口 UI 类"""

    def setup_ui(self, main_window: QMainWindow):
        """设置 UI"""
        main_window.setWindowTitle("Scenario Tool - 视觉小说脚本工具")
        main_window.resize(900, 700)

        # 中央部件
        central_widget = QWidget()
        main_window.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)

        # 创建标签页
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # 添加各个标签页
        self._create_scenario_tab()
        self._create_param_tab()
        self._create_resource_tab()
        self._create_config_tab()

        # 状态栏
        self.status_bar = main_window.statusBar()
        self.status_bar.showMessage("就绪")

    def _create_scenario_tab(self):
        """创建脚本生成标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 配置组
        config_group = QGroupBox("脚本生成配置")
        config_layout = QVBoxLayout()

        # 引擎类型
        engine_layout = QHBoxLayout()
        engine_layout.addWidget(QLabel("引擎类型:"))
        self.scenario_engine_combo = QComboBox()
        self.scenario_engine_combo.addItems(["Ren'Py", "Naninovel"])
        engine_layout.addWidget(self.scenario_engine_combo)
        engine_layout.addStretch()
        config_layout.addLayout(engine_layout)

        # 输入目录
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("输入目录:"))
        self.scenario_input_edit = DragDropLineEdit("input/")
        input_layout.addWidget(self.scenario_input_edit)
        self.scenario_input_btn = QPushButton("浏览...")
        input_layout.addWidget(self.scenario_input_btn)
        config_layout.addLayout(input_layout)

        # 输出目录
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("输出目录:"))
        self.scenario_output_edit = DragDropLineEdit("output/")
        output_layout.addWidget(self.scenario_output_edit)
        self.scenario_output_btn = QPushButton("浏览...")
        output_layout.addWidget(self.scenario_output_btn)
        config_layout.addLayout(output_layout)

        # 忽略模式
        ignore_layout = QHBoxLayout()
        self.scenario_ignore_check = QCheckBox("启用忽略模式")
        ignore_layout.addWidget(self.scenario_ignore_check)
        ignore_layout.addWidget(QLabel("忽略词:"))
        self.scenario_ignore_edit = QLineEdit("忽略,")
        self.scenario_ignore_edit.setEnabled(False)
        ignore_layout.addWidget(self.scenario_ignore_edit)
        config_layout.addLayout(ignore_layout)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # 操作按钮
        btn_layout = QHBoxLayout()
        self.scenario_generate_btn = QPushButton("生成脚本")
        self.scenario_generate_btn.setMinimumHeight(40)
        btn_layout.addWidget(self.scenario_generate_btn)
        layout.addLayout(btn_layout)

        # 进度条
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("进度:"))
        self.scenario_progress = QProgressBar()
        self.scenario_progress.setValue(0)
        progress_layout.addWidget(self.scenario_progress)
        layout.addLayout(progress_layout)

        # 日志输出
        log_group = QGroupBox("日志输出")
        log_layout = QVBoxLayout()
        self.scenario_log = QTextEdit()
        self.scenario_log.setReadOnly(True)
        log_layout.addWidget(self.scenario_log)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # 恢复按钮（放在日志下方靠右）
        reset_layout = QHBoxLayout()
        reset_layout.addStretch()
        self.scenario_reset_btn = QPushButton("恢复默认")
        self.scenario_reset_btn.setMaximumWidth(80)
        reset_layout.addWidget(self.scenario_reset_btn)
        layout.addLayout(reset_layout)

        self.tab_widget.addTab(tab, "脚本生成")

    def _create_param_tab(self):
        """创建参数映射标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 配置组
        config_group = QGroupBox("参数映射配置")
        config_layout = QVBoxLayout()

        # 引擎类型
        engine_layout = QHBoxLayout()
        engine_layout.addWidget(QLabel("引擎类型:"))
        self.param_engine_combo = QComboBox()
        engine_layout.addWidget(self.param_engine_combo)
        engine_layout.addStretch()
        config_layout.addLayout(engine_layout)

        # 参数配置目录
        param_dir_layout = QHBoxLayout()
        param_dir_layout.addWidget(QLabel("参数配置目录:"))
        self.param_config_dir_edit = DragDropLineEdit()
        param_dir_layout.addWidget(self.param_config_dir_edit)
        self.param_config_dir_btn = QPushButton("浏览...")
        param_dir_layout.addWidget(self.param_config_dir_btn)
        config_layout.addLayout(param_dir_layout)

        # 参数文件路径（只读提示）
        param_layout = QHBoxLayout()
        param_layout.addWidget(QLabel("参数文件:"))
        self.param_file_label = QLabel("param_config/param_data_renpy.xlsx")
        param_layout.addWidget(self.param_file_label)
        param_layout.addStretch()
        config_layout.addLayout(param_layout)

        # 差分参数文件（只读提示）
        varient_layout = QHBoxLayout()
        varient_layout.addWidget(QLabel("差分文件:"))
        self.param_varient_label = QLabel("param_config/varient_data.xlsx")
        varient_layout.addWidget(self.param_varient_label)
        varient_layout.addStretch()
        config_layout.addLayout(varient_layout)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # 操作按钮
        btn_layout = QHBoxLayout()
        self.param_update_btn = QPushButton("更新参数映射")
        self.param_update_btn.setMinimumHeight(40)
        btn_layout.addWidget(self.param_update_btn)
        layout.addLayout(btn_layout)

        # 进度条
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("进度:"))
        self.param_progress = QProgressBar()
        self.param_progress.setValue(0)
        progress_layout.addWidget(self.param_progress)
        layout.addLayout(progress_layout)

        # 日志输出
        log_group = QGroupBox("日志输出")
        log_layout = QVBoxLayout()
        self.param_log = QTextEdit()
        self.param_log.setReadOnly(True)
        log_layout.addWidget(self.param_log)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # 恢复按钮（放在日志下方靠右）
        reset_layout = QHBoxLayout()
        reset_layout.addStretch()
        self.param_reset_btn = QPushButton("恢复默认")
        self.param_reset_btn.setMaximumWidth(80)
        reset_layout.addWidget(self.param_reset_btn)
        layout.addLayout(reset_layout)

        self.tab_widget.addTab(tab, "参数映射")

    def _create_resource_tab(self):
        """创建资源管理标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 配置组
        config_group = QGroupBox("资源管理配置")
        config_layout = QVBoxLayout()

        # 演出表格目录
        excel_layout = QHBoxLayout()
        excel_label = QLabel("演出表格目录:")
        excel_label.setMinimumWidth(80)
        excel_layout.addWidget(excel_label)
        self.resource_excel_edit = DragDropLineEdit()
        excel_layout.addWidget(self.resource_excel_edit)
        self.resource_excel_btn = QPushButton("浏览...")
        excel_layout.addWidget(self.resource_excel_btn)
        config_layout.addLayout(excel_layout)

        # 项目库目录
        project_layout = QHBoxLayout()
        project_label = QLabel("项目库:")
        project_label.setMinimumWidth(80)
        project_layout.addWidget(project_label)
        self.resource_project_edit = DragDropLineEdit()
        project_layout.addWidget(self.resource_project_edit)
        self.resource_project_btn = QPushButton("浏览...")
        project_layout.addWidget(self.resource_project_btn)
        config_layout.addLayout(project_layout)

        # 资源库目录
        library_layout = QHBoxLayout()
        library_label = QLabel("资源库:")
        library_label.setMinimumWidth(80)
        library_layout.addWidget(library_label)
        self.resource_library_edit = DragDropLineEdit()
        library_layout.addWidget(self.resource_library_edit)
        self.resource_library_btn = QPushButton("浏览...")
        library_layout.addWidget(self.resource_library_btn)
        config_layout.addLayout(library_layout)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # 干跑模式选项
        dry_run_layout = QHBoxLayout()
        self.resource_dry_run_check = QCheckBox("干跑模式（仅预览，不实际复制）")
        dry_run_layout.addWidget(self.resource_dry_run_check)
        dry_run_layout.addStretch()
        layout.addLayout(dry_run_layout)

        # 操作按钮
        btn_layout = QHBoxLayout()
        self.resource_validate_btn = QPushButton("验证资源")
        self.resource_validate_btn.setMinimumHeight(40)
        btn_layout.addWidget(self.resource_validate_btn)

        self.resource_sync_btn = QPushButton("同步资源")
        self.resource_sync_btn.setMinimumHeight(40)
        self.resource_sync_btn.setEnabled(False)
        btn_layout.addWidget(self.resource_sync_btn)
        layout.addLayout(btn_layout)

        # 进度条
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("进度:"))
        self.resource_progress = QProgressBar()
        self.resource_progress.setValue(0)
        progress_layout.addWidget(self.resource_progress)
        layout.addLayout(progress_layout)

        # 日志输出
        log_group = QGroupBox("日志输出")
        log_layout = QVBoxLayout()
        self.resource_log = QTextEdit()
        self.resource_log.setReadOnly(True)
        log_layout.addWidget(self.resource_log)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # 恢复按钮（放在日志下方靠右）
        reset_layout = QHBoxLayout()
        reset_layout.addStretch()
        self.resource_reset_btn = QPushButton("恢复默认")
        self.resource_reset_btn.setMaximumWidth(80)
        reset_layout.addWidget(self.resource_reset_btn)
        layout.addLayout(reset_layout)

        self.tab_widget.addTab(tab, "资源管理")

    def _create_config_tab(self):
        """创建配置标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 路径配置组
        path_group = QGroupBox("路径配置")
        path_layout = QVBoxLayout()

        # 输入目录
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("输入目录:"))
        self.config_input_edit = DragDropLineEdit()
        input_layout.addWidget(self.config_input_edit)
        self.config_input_btn = QPushButton("浏览...")
        input_layout.addWidget(self.config_input_btn)
        path_layout.addLayout(input_layout)

        # 输出目录
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("输出目录:"))
        self.config_output_edit = DragDropLineEdit()
        output_layout.addWidget(self.config_output_edit)
        self.config_output_btn = QPushButton("浏览...")
        output_layout.addWidget(self.config_output_btn)
        path_layout.addLayout(output_layout)

        # 参数配置目录
        param_layout = QHBoxLayout()
        param_layout.addWidget(QLabel("参数配置目录:"))
        self.config_param_edit = DragDropLineEdit()
        param_layout.addWidget(self.config_param_edit)
        self.config_param_btn = QPushButton("浏览...")
        param_layout.addWidget(self.config_param_btn)
        path_layout.addLayout(param_layout)

        # 日志目录
        log_layout = QHBoxLayout()
        log_layout.addWidget(QLabel("日志目录:"))
        self.config_log_edit = DragDropLineEdit()
        log_layout.addWidget(self.config_log_edit)
        self.config_log_btn = QPushButton("浏览...")
        log_layout.addWidget(self.config_log_btn)
        path_layout.addLayout(log_layout)

        # 项目库目录
        project_root_layout = QHBoxLayout()
        project_root_layout.addWidget(QLabel("项目库目录:"))
        self.config_project_root_edit = DragDropLineEdit()
        project_root_layout.addWidget(self.config_project_root_edit)
        self.config_project_root_btn = QPushButton("浏览...")
        project_root_layout.addWidget(self.config_project_root_btn)
        path_layout.addLayout(project_root_layout)

        # 资源库目录
        source_root_layout = QHBoxLayout()
        source_root_layout.addWidget(QLabel("资源库目录:"))
        self.config_source_root_edit = DragDropLineEdit()
        source_root_layout.addWidget(self.config_source_root_edit)
        self.config_source_root_btn = QPushButton("浏览...")
        source_root_layout.addWidget(self.config_source_root_btn)
        path_layout.addLayout(source_root_layout)

        path_group.setLayout(path_layout)
        layout.addWidget(path_group)

        # 处理配置组
        process_group = QGroupBox("处理配置")
        process_layout = QVBoxLayout()

        # 忽略模式
        ignore_layout = QHBoxLayout()
        self.config_ignore_check = QCheckBox("启用忽略模式")
        ignore_layout.addWidget(self.config_ignore_check)
        ignore_layout.addWidget(QLabel("忽略词:"))
        self.config_ignore_edit = QLineEdit()
        ignore_layout.addWidget(self.config_ignore_edit)
        process_layout.addLayout(ignore_layout)

        process_group.setLayout(process_layout)
        layout.addWidget(process_group)

        # 引擎配置组
        engine_group = QGroupBox("引擎配置")
        engine_layout = QHBoxLayout()
        engine_layout.addWidget(QLabel("引擎类型:"))
        self.config_engine_combo = QComboBox()
        self.config_engine_combo.addItems(["Ren'Py", "Naninovel"])
        engine_layout.addWidget(self.config_engine_combo)
        engine_layout.addStretch()
        engine_group.setLayout(engine_layout)
        layout.addWidget(engine_group)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.config_save_btn = QPushButton("保存配置")
        self.config_save_btn.setMinimumHeight(40)
        btn_layout.addWidget(self.config_save_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()

        self.tab_widget.addTab(tab, "默认配置")
