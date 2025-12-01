"""
资源管理控制器
连接 GUI 和资源验证/同步逻辑
"""
import json
import time
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QThread
from core.config_manager import AppConfig
from core.logger import get_logger
from core.param_translator import ParamTranslator
from core.resource_extractor import ResourceExtractor
from core.resource_validator import ResourceValidator
from core.resource_syncer import ResourceSyncer
from core.sentence_generator_manager import SentenceGeneratorManager
import pandas as pd

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

            # 创建翻译器
            translator = ParamTranslator(
                module_file=str(self.config.paths.param_config_dir / "param_mappings.py"),
                varient_module_file=str(self.config.paths.param_config_dir / "varient_mappings.py")
            )

            # 创建生成器管理器
            generator_manager = SentenceGeneratorManager(self.config.engine.engine_type)
            generator_manager.load()

            # 创建资源提取器
            extractor = ResourceExtractor(generator_manager, translator, self.config.engine)
            extractor.setup()

            # 获取资源文件夹映射
            resource_folders = {}
            for generator in extractor.generators:
                configs = extractor._get_resource_configs(generator)
                for config in configs:
                    resource_type = config["resource_type"]
                    folder = config.get("folder", "")
                    if folder:
                        resource_folders[resource_type] = folder

            # 创建资源验证器
            validator = ResourceValidator(
                self.config.resources.project_root,
                self.config.resources.source_root,
                self.config.resources.extensions
            )

            # 获取所有 Excel 文件
            input_dir = Path(self.config.paths.input_dir)
            if not input_dir.exists():
                self.finished.emit(False, f"输入目录不存在: {input_dir}", {})
                return

            excel_files = [
                f for f in input_dir.iterdir()
                if f.suffix in ['.xlsx', '.xls'] and not f.name.startswith('~')
            ]

            if not excel_files:
                self.finished.emit(False, "未找到 Excel 文件", {})
                return

            self.progress.emit(f"找到 {len(excel_files)} 个 Excel 文件")

            # 处理每个文件
            for excel_file in excel_files:
                self.progress.emit(f"验证文件: {excel_file.name}")

                # 读取 Excel
                excel_data = pd.read_excel(excel_file, sheet_name=None, dtype=str)

                # 提取资源
                resources = extractor.extract_from_excel(excel_data)

                if not resources:
                    self.progress.emit(f"  未找到任何资源引用")
                    continue

                # 验证资源
                validation_results = validator.validate_resources(resources, resource_folders)

                # 生成文本报告
                report_text = self._generate_report(resources, validation_results, excel_file.name)

                # 保存报告
                report_dir = self.config.paths.output_dir / "validation_reports"
                report_dir.mkdir(parents=True, exist_ok=True)

                # 保存文本报告（供用户查看）
                text_report_file = report_dir / f"{excel_file.stem}_validation.txt"
                with open(text_report_file, "w", encoding="utf-8") as f:
                    f.write(report_text)
                self.progress.emit(f"  文本报告已保存: {text_report_file.name}")

                # 保存 JSON 报告（供程序读取）
                json_report_file = report_dir / f"{excel_file.stem}_validation.json"
                json_data = {
                    "timestamp": time.time(),
                    "excel_file": str(excel_file),
                    "excel_name": excel_file.name,
                    "resources": {
                        category: {
                            rtype: list(names)  # 转换 Set 为 List
                            for rtype, names in types.items()
                        }
                        for category, types in resources.items()
                    },
                    "validation_results": validation_results,
                    "resource_folders": resource_folders
                }

                with open(json_report_file, "w", encoding="utf-8") as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)
                self.progress.emit(f"  JSON 报告已保存: {json_report_file.name}")

            self.finished.emit(True, "资源验证完成", {})

        except Exception as e:
            logger.error(f"资源验证失败: {e}", exc_info=True)
            self.finished.emit(False, f"验证失败: {str(e)}", {})

    def _generate_report(self, resources: dict, validation_results: dict, excel_name: str) -> str:
        """生成验证报告文本"""
        lines = []
        lines.append("=" * 60)
        lines.append(f"资源完整性验证报告: {excel_name}")
        lines.append("=" * 60)
        lines.append("")

        comparison = validation_results.get("comparison", {})

        total_files = 0
        total_project_found = 0
        total_source_found = 0

        for category, types in resources.items():
            lines.append(f"{category}资源:")
            lines.append("-" * 30)

            for resource_type, resource_names in types.items():
                comp_data = comparison.get(resource_type, {})

                project_found = len(comp_data.get("project_found", []))
                project_missing = len(comp_data.get("project_missing", []))
                source_found = len(comp_data.get("source_found", []))
                source_missing = len(comp_data.get("source_missing", []))

                total_files += len(resource_names)
                total_project_found += project_found
                total_source_found += source_found

                lines.append(f"  {resource_type}:")
                lines.append(f"    总计: {len(resource_names)}")
                lines.append(f"    项目库: 找到 {project_found} / 缺失 {project_missing}")
                lines.append(f"    资源库: 找到 {source_found} / 缺失 {source_missing}")

                # 显示缺失文件
                missing_in_both = comp_data.get("missing_in_both", [])
                if missing_in_both:
                    lines.append(f"    两个库都缺失 ({len(missing_in_both)}):")
                    for name in sorted(missing_in_both)[:5]:  # 只显示前5个
                        lines.append(f"      - {name}")
                    if len(missing_in_both) > 5:
                        lines.append(f"      ... 还有 {len(missing_in_both) - 5} 个")

                missing_in_project = comp_data.get("missing_in_project_but_in_source", [])
                if missing_in_project:
                    lines.append(f"    项目库缺失但资源库存在 ({len(missing_in_project)}):")
                    for name in sorted(missing_in_project)[:5]:  # 只显示前5个
                        lines.append(f"      - {name}")
                    if len(missing_in_project) > 5:
                        lines.append(f"      ... 还有 {len(missing_in_project) - 5} 个")

            lines.append("")

        # 总计统计
        lines.append("=" * 60)
        lines.append("总计统计:")
        lines.append(f"  总文件数: {total_files}")
        lines.append(f"  项目库: 找到 {total_project_found} / 缺失 {total_files - total_project_found}")
        if total_files > 0:
            lines.append(f"  项目库完成率: {(total_project_found / total_files * 100):.1f}%")
        lines.append(f"  资源库: 找到 {total_source_found} / 缺失 {total_files - total_source_found}")
        if total_files > 0:
            lines.append(f"  资源库完成率: {(total_source_found / total_files * 100):.1f}%")
        lines.append("=" * 60)

        return "\n".join(lines)


class ResourceSyncWorker(QThread):
    """资源同步工作线程"""

    progress = Signal(str)  # 进度信息
    finished = Signal(bool, str)  # 完成信号 (成功, 消息)

    def __init__(self, config: AppConfig, dry_run: bool = False):
        super().__init__()
        self.config = config
        self.dry_run = dry_run

    def run(self):
        """执行资源同步"""
        try:
            self.progress.emit("开始同步资源...")

            # 检查验证报告目录
            report_dir = self.config.paths.output_dir / "validation_reports"
            if not report_dir.exists():
                self.finished.emit(False, "验证报告目录不存在，请先运行资源验证")
                return

            # 获取所有 JSON 验证报告
            json_reports = list(report_dir.glob("*_validation.json"))
            if not json_reports:
                self.finished.emit(False, "未找到验证报告，请先运行资源验证")
                return

            self.progress.emit(f"找到 {len(json_reports)} 个验证报告")

            # 创建资源同步器
            syncer = ResourceSyncer(
                self.config.resources.project_root,
                self.config.resources.source_root
            )

            total_synced = 0
            total_failed = 0
            total_skipped = 0

            # 处理每个验证报告
            for json_report in json_reports:
                self.progress.emit(f"处理报告: {json_report.name}")

                # 加载验证报告
                try:
                    with open(json_report, "r", encoding="utf-8") as f:
                        report_data = json.load(f)
                except Exception as e:
                    self.progress.emit(f"  读取报告失败: {e}")
                    continue

                # 提取数据
                validation_results = report_data.get("validation_results", {})
                resource_folders = report_data.get("resource_folders", {})
                excel_name = report_data.get("excel_name", "未知")

                self.progress.emit(f"  Excel 文件: {excel_name}")

                # 创建同步计划
                sync_plan = syncer.create_sync_plan(validation_results, resource_folders)

                if not sync_plan:
                    self.progress.emit(f"  没有需要同步的文件")
                    continue

                self.progress.emit(f"  需要同步 {len(sync_plan)} 个文件")

                # 执行同步
                mode_text = "（干跑模式）" if self.dry_run else ""
                self.progress.emit(f"  开始同步{mode_text}...")
                stats = syncer.execute_sync(sync_plan, self.dry_run)

                total_synced += stats['success']
                total_failed += stats['failed']
                total_skipped += stats['skipped']

                self.progress.emit(f"  成功: {stats['success']}, 失败: {stats['failed']}, 跳过: {stats['skipped']}")

            # 生成最终消息
            if self.dry_run:
                message = f"干跑模式预览完成: 将同步 {total_synced} 个文件"
            else:
                message = f"同步完成: 成功 {total_synced} 个文件"

            if total_failed > 0:
                message += f", 失败 {total_failed} 个"
            if total_skipped > 0:
                message += f", 跳过 {total_skipped} 个"

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

    def sync_resources(self, dry_run: bool = False):
        """同步资源"""
        if self.sync_worker and self.sync_worker.isRunning():
            logger.warning("资源同步正在进行中")
            return

        # 添加日志处理器
        logger.addHandler(self.main_window.resource_log_handler)

        self.sync_worker = ResourceSyncWorker(self.config, dry_run)
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
