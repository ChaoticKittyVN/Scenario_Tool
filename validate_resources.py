"""
资源完整性验证工具
检查 Excel 中引用的资源文件是否存在
"""
import pandas as pd
import json
import time
from pathlib import Path
from typing import Dict
from core.config_manager import AppConfig
from core.param_translator import ParamTranslator
from core.resource_extractor import ResourceExtractor
from core.resource_validator import ResourceValidator
from core.sentence_generator_manager import SentenceGeneratorManager
from core.logger import get_logger
from core.excel_management import (
    ExcelFileNotFoundError,
    ExcelFormatError,
    ExcelFileManager,
)

logger = get_logger()


def get_resource_folders(extractor: ResourceExtractor) -> Dict[str, str]:
    """
    从生成器的 resource_config 中提取文件夹映射

    Returns:
        Dict[str, str]: {资源类型: 文件夹路径}
    """
    folders = {}

    for generator in extractor.generators:
        configs = extractor.get_resource_configs(generator)
        for config in configs:
            resource_type = config["resource_type"]
            folder = config.get("folder", "")
            if folder:
                folders[resource_type] = folder

    return folders


def generate_report(
    resources: Dict,
    validation_results: Dict,
    excel_name: str
) -> str:
    """
    生成验证报告

    Returns:
        str: 报告文本
    """
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
                for name in sorted(missing_in_both):
                    lines.append(f"      - {name}")

            missing_in_project = comp_data.get("missing_in_project_but_in_source", [])
            if missing_in_project:
                lines.append(f"    项目库缺失但资源库存在 ({len(missing_in_project)}):")
                for name in sorted(missing_in_project):
                    lines.append(f"      - {name}")

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

        logger.info("=" * 60)
        logger.info("资源完整性验证工具")
        logger.info("=" * 60)

        # 创建翻译器
        translator = ParamTranslator(
            module_file=str(config.paths.param_config_dir / "param_mappings.py"),
            varient_module_file=str(config.paths.param_config_dir / "varient_mappings.py")
        )

        # 创建生成器管理器
        generator_manager = SentenceGeneratorManager(config.engine.engine_type)
        generator_manager.load()

        # 创建资源提取器
        extractor = ResourceExtractor(generator_manager, translator, config.engine)
        extractor.setup()

        # 获取资源文件夹映射
        resource_folders = get_resource_folders(extractor)
        logger.info(f"资源文件夹映射: {resource_folders}")

        # 创建资源验证器
        validator = ResourceValidator(
            config.resources.project_root,
            config.resources.source_root,
            config.resources.extensions
        )

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

        # 创建Excel文件管理器
        excel_manager = ExcelFileManager(cache_enabled=True)

        # 处理每个文件
        for excel_file in excel_files:
            logger.info(f"\n处理文件: {excel_file.name}")
            
            try:
                # 读取 Excel
                excel_data = excel_manager.load_excel(excel_file)
                
            except ExcelFileNotFoundError as e:
                logger.error(f"文件不存在，跳过: {excel_file}")
                continue
            except ExcelFormatError as e:
                logger.error(f"Excel格式错误，跳过: {excel_file} - {e}")
                continue
            except Exception as e:
                logger.error(f"读取Excel失败，跳过: {excel_file} - {e}")
                continue

            # 提取资源
            try:
                resources = extractor.extract_from_excel(excel_data)
            except Exception as e:
                logger.error(f"提取资源失败，跳过: {excel_file} - {e}")
                continue

            if not resources:
                logger.warning("未找到任何资源引用")
                continue

            # 显示提取的资源统计
            total_resources = sum(len(names) for types in resources.values() for names in types.values())
            logger.info(f"提取到 {total_resources} 个资源引用")

            # 验证资源
            try:
                validation_results = validator.validate_resources(resources, resource_folders)
            except Exception as e:
                logger.error(f"验证资源失败，跳过: {excel_file} - {e}")
                continue

            # 生成文本报告
            report_text = generate_report(resources, validation_results, excel_file.name)
            print(report_text)

            # 保存报告到文件
            report_dir = config.paths.output_dir / "validation_reports"
            report_dir.mkdir(parents=True, exist_ok=True)

            try:
                # 保存文本报告（供用户查看）
                text_report_file = report_dir / f"{excel_file.stem}_validation.txt"
                with open(text_report_file, "w", encoding="utf-8") as f:
                    f.write(report_text)
                logger.info(f"文本报告已保存: {text_report_file}")
                
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
                logger.info(f"JSON 报告已保存: {json_report_file}")
                
            except Exception as e:
                logger.error(f"保存报告失败: {excel_file} - {e}")

        logger.info("所有文件验证完成")

    except Exception as e:
        logger.critical(f"验证过程失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
