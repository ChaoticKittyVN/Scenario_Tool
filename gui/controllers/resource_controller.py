"""
资源管理控制器
连接 GUI 和资源验证/同步逻辑
"""
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QThread
from core.config_manager import AppConfig
from core.logger import get_logger

# 直接导入 CLI 工具的函数
from validate_resources import validate_excel_file

logger = get_logger()


class ResourceValidateWorker(QThread):
    """资源验证工作线程"""

    progress = Signal(str)  # 进度信息
    finished = Signal(bool, str, dict)  # 完成信号 (成功, 消息, 结果)

    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config

    def run(self):
        """执行资源验证"""
        try:
            self.progress.emit("开始验证资源...")

            # 获取所有 Excel 文件
            input_dir = Path(self.config.paths.input_dir)
            excel_files = [
                f for f in input_dir.iterdir()
                if f.suffix in ['.xlsx', '.xls'] and not f.name.startswith('~')
            ]

            if not excel_files:
                self.finished.emit(False, "未找到 Excel 文件", {})
                return

            # 配置项目资源目录
            project_dirs = {
                "图片": self.config.paths.input_dir / "images",
                "音频": self.config.paths.input_dir / "audio",
                "视频": self.config.paths.input_dir / "video",
            }

            # 验证每个文件
            for excel_file in excel_files:
                self.progress.emit(f"验证文件: {excel_file.name}")
                try:
                    validate_excel_file(excel_file, self.config, project_dirs)
                except Exception as e:
                    logger.error(f"验证文件 {excel_file.name} 失败: {e}")

            self.finished.emit(True, "资源验证完成，请查看报告", {})

        except Exception as e:
            logger.error(f"资源验证失败: {e}", exc_info=True)
            self.finished.emit(False, f"验证失败: {str(e)}", {})


class ResourceSyncWorker(QThread):
    """资源同步工作线程"""

    progress = Signal(str)  # 进度信息
    finished = Signal(bool, str)  # 完成信号 (成功, 消息)

    def __init__(self, config: AppConfig, library_path: Path, dry_run: bool = False):
        super().__init__()
        self.config = config
        self.library_path = library_path
        self.dry_run = dry_run

    def run(self):
        """执行资源同步"""
        try:
            from sync_resources import ResourceSyncer

            self.progress.emit("开始同步资源...")

            # 配置项目资源目录
            project_dirs = {
                "图片": self.config.paths.input_dir / "images",
                "音频": self.config.paths.input_dir / "audio",
                "视频": self.config.paths.input_dir / "video",
            }

            # 配置资源库目录
            source_dirs = {
                "图片": self.library_path / "images",
                "音频": self.library_path / "audio",
                "视频": self.library_path / "video",
            }

            # 创建同步器
            syncer = ResourceSyncer(self.config, project_dirs, source_dirs)

            # 这里需要找到最新的验证报告
            report_dir = self.config.paths.output_dir / "validation_reports"
            if not report_dir.exists():
                self.finished.emit(False, "未找到验证报告，请先运行资源验证")
                return

            # 获取最新的报告文件
            report_files = list(report_dir.glob("*_validation.txt"))
            if not report_files:
                self.finished.emit(False, "未找到验证报告文件")
                return

            latest_report = max(report_files, key=lambda p: p.stat().st_mtime)
            self.progress.emit(f"使用报告: {latest_report.name}")

            # 读取缺失文件列表
            missing_files = syncer.read_validation_report(latest_report)

            if not missing_files or sum(len(v) for v in missing_files.values()) == 0:
                self.finished.emit(True, "没有缺失的文件需要同步")
                return

            # 创建同步计划
            self.progress.emit("创建同步计划...")
            sync_plan, not_found = syncer.create_sync_plan(missing_files)

            total_to_sync = sum(len(v) for v in sync_plan.values())
            total_not_found = sum(len(v) for v in not_found.values())

            if total_to_sync == 0:
                self.finished.emit(False, f"所有 {total_not_found} 个文件都未在资源库中找到")
                return

            # 执行同步
            mode_text = "（干跑模式）" if self.dry_run else ""
            self.progress.emit(f"开始同步 {total_to_sync} 个文件{mode_text}...")
            stats = syncer.execute_sync(sync_plan, dry_run=self.dry_run)

            copied = stats.get('copied', 0)
            failed = stats.get('failed', 0)

            if self.dry_run:
                message = f"干跑模式预览完成: 将复制 {copied} 个文件"
            else:
                message = f"同步完成: 成功复制 {copied} 个文件"

            if failed > 0:
                message += f", {failed} 个文件复制失败"
            if total_not_found > 0:
                message += f", {total_not_found} 个文件未找到"

            if self.dry_run:
                message += "\n注意: 当前为干跑模式，未实际执行复制操作"

            self.finished.emit(True, message)

        except Exception as e:
            logger.error(f"资源同步失败: {e}", exc_info=True)
            self.finished.emit(False, f"同步失败: {str(e)}")


class ResourceController(QObject):
    """资源管理控制器"""

    # 定义信号
    validate_progress = Signal(str)
    validate_finished = Signal(bool, str, dict)
    sync_progress = Signal(str)
    sync_finished = Signal(bool, str)

    def __init__(self, main_window, config: AppConfig):
        super().__init__()
        self.main_window = main_window
        self.config = config
        self.validate_worker = None
        self.sync_worker = None
        self.last_report_path = None

    def validate_resources(self, config=None):
        """验证资源"""
        if self.validate_worker and self.validate_worker.isRunning():
            logger.warning("资源验证正在进行中")
            return

        # 添加日志处理器
        logger.addHandler(self.main_window.resource_log_handler)

        self.validate_worker = ResourceValidateWorker(config or self.config)
        self.validate_worker.progress.connect(self._on_validate_progress)
        self.validate_worker.finished.connect(self._on_validate_finished)
        self.validate_worker.start()

    def sync_resources(self, library_path: Path, dry_run: bool = False):
        """同步资源"""
        if self.sync_worker and self.sync_worker.isRunning():
            logger.warning("资源同步正在进行中")
            return

        # 添加日志处理器
        logger.addHandler(self.main_window.resource_log_handler)

        self.sync_worker = ResourceSyncWorker(self.config, library_path, dry_run)
        self.sync_worker.progress.connect(self._on_sync_progress)
        self.sync_worker.finished.connect(self._on_sync_finished)
        self.sync_worker.start()

    def _on_validate_progress(self, message: str):
        """处理验证进度更新"""
        logger.info(message)
        self.validate_progress.emit(message)

    def _on_validate_finished(self, success: bool, message: str, missing_files: dict):
        """处理验证完成事件"""
        if success:
            logger.info(message)
        else:
            logger.error(message)
        self.validate_finished.emit(success, message, missing_files)

        # 移除日志处理器
        logger.removeHandler(self.main_window.resource_log_handler)

    def _on_sync_progress(self, message: str):
        """处理同步进度更新"""
        logger.info(message)
        self.sync_progress.emit(message)

    def _on_sync_finished(self, success: bool, message: str):
        """处理同步完成事件"""
        if success:
            logger.info(message)
        else:
            logger.error(message)
        self.sync_finished.emit(success, message)

        # 移除日志处理器
        logger.removeHandler(self.main_window.resource_log_handler)
