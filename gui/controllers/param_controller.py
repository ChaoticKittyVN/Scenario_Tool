"""
参数映射控制器
连接 GUI 和参数映射更新逻辑
"""
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QThread
from core.config_manager import AppConfig
from core.logger import get_logger

logger = get_logger()


class ParamUpdateWorker(QThread):
    """参数更新工作线程"""

    progress = Signal(str)  # 进度信息
    finished = Signal(bool, str)  # 完成信号 (成功, 消息)

    def __init__(
        self,
        config: AppConfig,
        generate_mapping_files: bool = True,
        update_parameter_sheets: bool = True,
    ):
        super().__init__()
        if not generate_mapping_files and not update_parameter_sheets:
            raise ValueError("至少需要选择一项参数更新操作")
        self.config = config
        self.generate_mapping_files = generate_mapping_files
        self.update_parameter_sheets = update_parameter_sheets

    @property
    def operation_name(self) -> str:
        if self.generate_mapping_files and self.update_parameter_sheets:
            return "更新映射并同步参数表"
        if self.generate_mapping_files:
            return "生成参数映射"
        return "同步演出表参数表"

    @property
    def success_message(self) -> str:
        if self.generate_mapping_files and self.update_parameter_sheets:
            return "参数映射与演出表格参数表更新成功"
        return f"{self.operation_name}成功"

    @property
    def failure_message(self) -> str:
        if self.generate_mapping_files and self.update_parameter_sheets:
            return "参数映射或参数表更新失败"
        return f"{self.operation_name}失败"

    def run(self):
        """执行参数映射更新"""
        try:
            from update_param import ParamUpdater

            self.progress.emit(f"开始{self.operation_name}...")

            updater = ParamUpdater(self.config)
            success = updater.update_mappings(
                generate_mapping_files=self.generate_mapping_files,
                update_parameter_sheets=self.update_parameter_sheets,
                dry_run=False,
            )

            if success:
                self.finished.emit(True, self.success_message)
            else:
                self.finished.emit(False, self.failure_message)

        except Exception as e:
            logger.error(f"参数映射更新失败: {e}", exc_info=True)
            self.finished.emit(False, f"更新失败: {str(e)}")


class ParamController(QObject):
    """参数映射控制器"""

    # 定义信号
    worker_progress = Signal(str)
    worker_finished = Signal(bool, str)

    def __init__(self, main_window, config: AppConfig):
        super().__init__()
        self.main_window = main_window
        self.config = config
        self.worker = None

    def update_param_mappings(
        self,
        config=None,
        generate_mapping_files: bool = True,
        update_parameter_sheets: bool = True,
    ):
        """更新参数映射"""
        if self.worker and self.worker.isRunning():
            logger.warning("参数映射更新正在进行中")
            return

        # 添加日志处理器
        logger.addHandler(self.main_window.param_log_handler)

        self.worker = ParamUpdateWorker(
            config or self.config,
            generate_mapping_files=generate_mapping_files,
            update_parameter_sheets=update_parameter_sheets,
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, message: str):
        """处理进度更新"""
        self.worker_progress.emit(message)

    def _on_finished(self, success: bool, message: str):
        """处理完成事件"""
        if success:
            logger.info(message)
        else:
            logger.error(message)
        self.worker_finished.emit(success, message)

        # 移除日志处理器
        logger.removeHandler(self.main_window.param_log_handler)
