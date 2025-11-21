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

    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config

    def run(self):
        """执行参数映射更新"""
        try:
            from update_param import ParamUpdater

            self.progress.emit("开始更新参数映射...")

            updater = ParamUpdater(self.config)
            success = updater.update_mappings()

            if success:
                self.finished.emit(True, "参数映射更新成功")
            else:
                self.finished.emit(False, "参数映射更新失败")

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

    def update_param_mappings(self, config=None):
        """更新参数映射"""
        if self.worker and self.worker.isRunning():
            logger.warning("参数映射更新正在进行中")
            return

        # 添加日志处理器
        logger.addHandler(self.main_window.param_log_handler)

        self.worker = ParamUpdateWorker(config or self.config)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, message: str):
        """处理进度更新"""
        logger.info(message)
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
