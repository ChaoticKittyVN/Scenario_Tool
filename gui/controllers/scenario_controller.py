"""
脚本生成控制器
连接 GUI 和脚本生成核心逻辑
"""
from PySide6.QtCore import QObject, Signal, QThread
from core.config_manager import AppConfig
from core.logger import get_logger

from generate_scenario import generate_scenarios

logger = get_logger()


class ScenarioGeneratorWorker(QThread):
    """脚本生成工作线程"""

    progress = Signal(str)  # 进度信息
    finished = Signal(bool, str)  # 完成信号 (成功, 消息)

    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config

    def run(self):
        """执行脚本生成"""
        try:
            summary = generate_scenarios(self.config, self.progress.emit)
            if summary.error:
                self.finished.emit(False, summary.error)
            elif summary.success:
                message = f"成功生成 {summary.succeeded_files} 个脚本"
                if summary.untranslatable_count:
                    message += f"，发现 {summary.untranslatable_count} 个无法翻译的参数"
                self.finished.emit(True, message)
            elif summary.succeeded_files:
                self.finished.emit(
                    False,
                    f"部分成功: {summary.succeeded_files}/{summary.total_files} 个文件生成成功",
                )
            else:
                self.finished.emit(False, "所有文件处理失败")

        except Exception as e:
            logger.error(f"脚本生成失败: {e}", exc_info=True)
            self.finished.emit(False, f"生成失败: {str(e)}")


class ScenarioController(QObject):
    """脚本生成控制器"""

    # 定义信号
    worker_progress = Signal(str)
    worker_finished = Signal(bool, str)

    def __init__(self, main_window, config: AppConfig):
        super().__init__()
        self.main_window = main_window
        self.config = config
        self.worker = None

    def generate_scripts(self, config=None):
        """生成脚本"""
        if self.worker and self.worker.isRunning():
            logger.warning("脚本生成正在进行中")
            return

        # 添加日志处理器
        logger.addHandler(self.main_window.scenario_log_handler)

        self.worker = ScenarioGeneratorWorker(config or self.config)
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
        logger.removeHandler(self.main_window.scenario_log_handler)
