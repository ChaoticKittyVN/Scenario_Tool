"""
资源完整性验证工具
检查 Excel 中引用的资源文件是否存在
"""
import pandas as pd
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
from core.config_manager import AppConfig
from core.param_translator import ParamTranslator
from core.logger import get_logger
from core.constants import SheetName, ColumnName, Marker

logger = get_logger()


class ResourceValidator:
    """资源验证器"""

    def __init__(self, config: AppConfig, translator: ParamTranslator):
        """
        初始化资源验证器

        Args:
            config: 应用配置
            translator: 参数翻译器
        """
        self.config = config
        self.translator = translator
        self.resource_columns = self._get_resource_columns()

    def _get_resource_columns(self) -> Dict[str, List[str]]:
        """
        获取需要检查的资源列配置

        Returns:
            Dict[str, List[str]]: 资源类型到列名的映射
        """
        # 根据引擎类型返回不同的资源列配置
        if self.config.engine.engine_type == "renpy":
            return {
                "图片": ["Character", "Sprite", "Background", "CG"],
                "音频": ["Music", "Sound", "Voice"],
                "视频": ["Video"],
            }
        elif self.config.engine.engine_type == "naninovel":
            return {
                "图片": ["Char", "Background"],
                "音频": ["Music", "Sound"],
                "视频": [],
            }
        else:
            return {
                "图片": ["Character", "Background"],
                "音频": ["Music", "Sound"],
                "视频": [],
            }

    def collect_resources_from_excel(self, excel_path: Path) -> Dict[str, Set[str]]:
        """
        从 Excel 文件中收集所有引用的资源

        Args:
            excel_path: Excel 文件路径

        Returns:
            Dict[str, Set[str]]: 资源类型到文件名集合的映射
        """
        logger.info(f"开始收集资源: {excel_path.name}")
        resources = defaultdict(set)

        try:
            excel_data = pd.read_excel(excel_path, sheet_name=None, dtype=str)

            for sheet_name, sheet_data in excel_data.items():
                # 跳过参数表
                if sheet_name == SheetName.PARAM_SHEET.value:
                    continue

                # 检查是否有 END 标记
                if (ColumnName.NOTE.value not in sheet_data.columns or
                        Marker.END.value not in sheet_data[ColumnName.NOTE.value].tolist()):
                    continue

                # 找到 END 标记位置
                end_index = sheet_data[ColumnName.NOTE.value].tolist().index(Marker.END.value)

                # 遍历有效行
                for idx in range(end_index):
                    row = sheet_data.iloc[idx]

                    # 检查每种资源类型
                    for resource_type, columns in self.resource_columns.items():
                        for column in columns:
                            if column in row.index:
                                value = row[column]
                                if pd.notna(value) and str(value).strip():
                                    # 翻译参数（如果需要）
                                    translated_value = self._translate_resource(column, str(value).strip())
                                    if translated_value:
                                        resources[resource_type].add(translated_value)

            logger.info(f"收集完成: {sum(len(v) for v in resources.values())} 个资源")
            return dict(resources)

        except Exception as e:
            logger.error(f"收集资源时出错: {e}", exc_info=True)
            return {}

    def _translate_resource(self, column: str, value: str) -> str:
        """
        翻译资源参数

        Args:
            column: 列名
            value: 原始值

        Returns:
            str: 翻译后的值
        """
        # 尝试翻译
        try:
            # 根据列名确定参数类型
            param_type_map = {
                "Character": "Character",
                "Sprite": "Sprite",
                "Background": "Background",
                "Music": "Music",
                "Sound": "Sound",
                "Voice": "Voice",
                "Char": "Character",
            }

            param_type = param_type_map.get(column)
            if param_type and self.translator.has_mapping(param_type):
                translated = self.translator.translate(param_type, value)
                return translated if translated else value
            return value
        except Exception:
            return value

    def check_resources_exist(
        self,
        resources: Dict[str, Set[str]],
        project_dirs: Dict[str, Path]
    ) -> Dict[str, Dict[str, bool]]:
        """
        检查资源文件是否存在

        Args:
            resources: 资源类型到文件名集合的映射
            project_dirs: 资源类型到项目目录的映射

        Returns:
            Dict[str, Dict[str, bool]]: 资源类型 -> 文件名 -> 是否存在
        """
        results = {}

        for resource_type, filenames in resources.items():
            results[resource_type] = {}
            project_dir = project_dirs.get(resource_type)

            if not project_dir or not project_dir.exists():
                logger.warning(f"{resource_type}目录不存在: {project_dir}")
                for filename in filenames:
                    results[resource_type][filename] = False
                continue

            # 检查每个文件
            for filename in filenames:
                # 尝试常见的文件扩展名
                extensions = self._get_extensions_for_type(resource_type)
                found = False

                for ext in extensions:
                    file_path = project_dir / f"{filename}{ext}"
                    if file_path.exists():
                        found = True
                        break

                results[resource_type][filename] = found

        return results

    def _get_extensions_for_type(self, resource_type: str) -> List[str]:
        """
        获取资源类型对应的文件扩展名

        Args:
            resource_type: 资源类型

        Returns:
            List[str]: 扩展名列表
        """
        extension_map = {
            "图片": [".png", ".jpg", ".jpeg", ".webp"],
            "音频": [".mp3", ".ogg", ".wav", ".m4a"],
            "视频": [".mp4", ".webm", ".ogv"],
        }
        return extension_map.get(resource_type, [])

    def generate_report(
        self,
        excel_path: Path,
        resources: Dict[str, Set[str]],
        check_results: Dict[str, Dict[str, bool]]
    ) -> Tuple[str, Dict]:
        """
        生成验证报告

        Args:
            excel_path: Excel 文件路径
            resources: 收集的资源
            check_results: 检查结果

        Returns:
            Tuple[str, Dict]: (报告文本, 统计信息)
        """
        lines = []
        lines.append("=" * 60)
        lines.append(f"资源完整性验证报告: {excel_path.name}")
        lines.append("=" * 60)
        lines.append("")

        stats = {
            "total": 0,
            "found": 0,
            "missing": 0,
            "by_type": {}
        }

        for resource_type in sorted(resources.keys()):
            filenames = resources[resource_type]
            results = check_results.get(resource_type, {})

            found_count = sum(1 for v in results.values() if v)
            missing_count = len(filenames) - found_count

            stats["total"] += len(filenames)
            stats["found"] += found_count
            stats["missing"] += missing_count
            stats["by_type"][resource_type] = {
                "total": len(filenames),
                "found": found_count,
                "missing": missing_count
            }

            lines.append(f"{resource_type}文件:")
            lines.append("-" * 30)
            lines.append(f"  总计: {len(filenames)}")
            lines.append(f"  找到: {found_count}")
            lines.append(f"  缺失: {missing_count}")

            if missing_count > 0:
                lines.append(f"  缺失文件列表:")
                for filename in sorted(filenames):
                    if not results.get(filename, False):
                        lines.append(f"    - {filename}")

            lines.append("")

        # 总计
        lines.append("=" * 60)
        lines.append("总计统计:")
        lines.append(f"  总文件数: {stats['total']}")
        lines.append(f"  找到: {stats['found']}")
        lines.append(f"  缺失: {stats['missing']}")
        if stats['total'] > 0:
            completion_rate = (stats['found'] / stats['total']) * 100
            lines.append(f"  完成率: {completion_rate:.1f}%")
        lines.append("=" * 60)

        return "\n".join(lines), stats


def validate_excel_file(excel_path: Path, config: AppConfig, project_dirs: Dict[str, Path]):
    """
    验证单个 Excel 文件的资源完整性

    Args:
        excel_path: Excel 文件路径
        config: 应用配置
        project_dirs: 项目资源目录配置
    """
    translator = ParamTranslator()
    validator = ResourceValidator(config, translator)

    # 收集资源
    resources = validator.collect_resources_from_excel(excel_path)

    if not resources:
        logger.warning(f"未找到任何资源引用: {excel_path.name}")
        return

    # 检查资源是否存在
    check_results = validator.check_resources_exist(resources, project_dirs)

    # 生成报告
    report_text, stats = validator.generate_report(excel_path, resources, check_results)

    # 打印报告
    print(report_text)

    # 保存报告到文件
    report_dir = config.paths.output_dir / "validation_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / f"{excel_path.stem}_validation.txt"

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_text)

    logger.info(f"验证报告已保存: {report_file}")

    # 如果有缺失文件，记录警告
    if stats["missing"] > 0:
        logger.warning(f"发现 {stats['missing']} 个缺失的资源文件")


def main():
    """主函数"""
    try:
        # 加载配置
        config_path = Path("config.yaml")
        if config_path.exists():
            config = AppConfig.from_file(config_path)
        else:
            logger.error("配置文件不存在: config.yaml")
            return

        # 配置项目资源目录（需要根据实际项目调整）
        project_dirs = {
            "图片": Path("project/images"),  # 示例路径
            "音频": Path("project/audio"),   # 示例路径
            "视频": Path("project/video"),   # 示例路径
        }

        logger.info("=" * 60)
        logger.info("资源完整性验证工具")
        logger.info("=" * 60)

        # 获取所有 Excel 文件
        if not config.paths.input_dir.exists():
            logger.error(f"输入目录不存在: {config.paths.input_dir}")
            return

        excel_files = [
            f for f in config.paths.input_dir.iterdir()
            if f.suffix in ['.xlsx', '.xls'] and not f.name.startswith('~')
        ]

        if not excel_files:
            logger.warning(f"在 {config.paths.input_dir} 中没有找到 Excel 文件")
            return

        logger.info(f"找到 {len(excel_files)} 个 Excel 文件")
        logger.info("")

        # 验证每个文件
        for excel_file in excel_files:
            validate_excel_file(excel_file, config, project_dirs)
            print("")

        logger.info("所有文件验证完成")

    except Exception as e:
        logger.critical(f"验证过程失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
