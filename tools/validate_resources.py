"""
资源完整性验证工具
检查 Excel 中引用的资源文件是否存在
"""
import pandas as pd
import json
import sys
import time
from pathlib import Path
from typing import Dict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config_manager import AppConfig
from core.engine_loader import load_engine
from core.param_process.param_translator import ParamTranslator
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


def get_resource_resolvers(config: AppConfig):
    """Create optional resource resolvers registered by the active engine."""
    engine_metadata = load_engine(config.engine.engine_type)
    if engine_metadata.validator_factory is None:
        return []
    resolver = engine_metadata.validator_factory(
        config.resources.project_root,
        config.engine,
    )
    return [resolver] if resolver is not None else []


def generate_report(
    resources: Dict,
    validation_results: Dict,
    excel_name: str,
    references: Dict = None,
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
    source_enabled = validation_results.get("source_enabled", True)
    references = references or {}

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
            if source_enabled:
                lines.append(f"    资源库: 找到 {source_found} / 缺失 {source_missing}")

            # 显示缺失文件
            missing_resources = (
                comp_data.get("missing_in_both", [])
                if source_enabled
                else comp_data.get("project_missing", [])
            )
            if missing_resources:
                label = "两个库都缺失" if source_enabled else "项目库缺失"
                lines.append(f"    {label} ({len(missing_resources)}):")
                for name in sorted(missing_resources):
                    lines.append(f"      - {name}")
                    append_reference_locations(
                        lines, references, category, resource_type, name
                    )

            missing_in_project = comp_data.get("missing_in_project_but_in_source", [])
            if missing_in_project:
                lines.append(f"    项目库缺失但资源库存在 ({len(missing_in_project)}):")
                for name in sorted(missing_in_project):
                    lines.append(f"      - {name}")
                    append_reference_locations(
                        lines, references, category, resource_type, name
                    )

            normalized_matches = comp_data.get("project_normalized_matches", [])
            if normalized_matches:
                lines.append(f"    文件名归一化命中 ({len(normalized_matches)}):")
                for item in sorted(
                    normalized_matches,
                    key=lambda value: value["resource_name"],
                ):
                    lines.append(
                        f"      - {item['resource_name']} -> {item['found_file']}"
                    )

            resolver_matches = comp_data.get("project_resolver_matches", [])
            if resolver_matches:
                lines.append(f"    扩展验证命中 ({len(resolver_matches)}):")
                for item in sorted(
                    resolver_matches,
                    key=lambda value: value["resource_name"],
                ):
                    match_label = item.get("match_label") or item["match_type"]
                    lines.append(
                        f"      - [{match_label}] {item['resource_name']} -> "
                        f"{item['found_file']}"
                    )

        lines.append("")

    # 总计统计
    lines.append("=" * 60)
    lines.append("总计统计:")
    lines.append(f"  总文件数: {total_files}")
    lines.append(f"  项目库: 找到 {total_project_found} / 缺失 {total_files - total_project_found}")
    if total_files > 0:
        lines.append(f"  项目库完成率: {(total_project_found / total_files * 100):.1f}%")
    if source_enabled:
        lines.append(f"  资源库: 找到 {total_source_found} / 缺失 {total_files - total_source_found}")
        if total_files > 0:
            lines.append(f"  资源库完成率: {(total_source_found / total_files * 100):.1f}%")
    lines.append("=" * 60)

    return "\n".join(lines)


def append_reference_locations(
    lines: list,
    references: Dict,
    category: str,
    resource_type: str,
    resource_name: str,
) -> None:
    summary = (
        references.get(category, {})
        .get(resource_type, {})
        .get(resource_name)
    )
    if not summary:
        return

    reference_count = summary.get("reference_count", 0)
    locations = summary.get("locations", [])
    lines.append(
        f"        引用 {reference_count} 次，显示 {len(locations)} 处："
    )
    for location in locations:
        index_value = location.get("index", "")
        index_text = f" / Index={index_value}" if index_value else ""
        lines.append(
            f"        - {location.get('workbook', '')} / "
            f"{location.get('sheet', '')} / "
            f"Excel 第 {location.get('excel_row', '')} 行{index_text}"
        )
        params = location.get("params", {})
        if params:
            param_text = ", ".join(
                f"{key}={value}" for key, value in params.items()
            )
            lines.append(f"          {param_text}")
    hidden_count = max(0, reference_count - len(locations))
    if hidden_count:
        lines.append(f"        - ...其余 {hidden_count} 处未显示")


def merge_resources(target: Dict, resources: Dict) -> None:
    """Merge extracted resources into a combined de-duplicated mapping."""
    for category, types in resources.items():
        category_target = target.setdefault(category, {})
        for resource_type, names in types.items():
            category_target.setdefault(resource_type, set()).update(names)


def merge_references(target: Dict, references: Dict, sample_limit: int) -> None:
    """Merge exact counts while retaining only bounded location samples."""
    sample_limit = max(0, int(sample_limit))
    for category, types in references.items():
        category_target = target.setdefault(category, {})
        for resource_type, resource_summaries in types.items():
            type_target = category_target.setdefault(resource_type, {})
            for resource_name, source_summary in resource_summaries.items():
                target_summary = type_target.setdefault(resource_name, {
                    "reference_count": 0,
                    "locations": [],
                    "locations_truncated": False,
                })
                target_summary["reference_count"] += source_summary.get(
                    "reference_count", 0
                )
                for location in source_summary.get("locations", []):
                    if len(target_summary["locations"]) >= sample_limit:
                        break
                    if location not in target_summary["locations"]:
                        target_summary["locations"].append(location)
                target_summary["locations_truncated"] = (
                    target_summary["reference_count"]
                    > len(target_summary["locations"])
                )


def get_missing_references(references: Dict, validation_results: Dict) -> Dict:
    """Return only reference summaries for resources missing in the project."""
    missing_references = {}
    comparison = validation_results.get("comparison", {})
    for category, types in references.items():
        for resource_type, resource_summaries in types.items():
            missing_names = set(
                comparison.get(resource_type, {}).get("project_missing", [])
            )
            selected = {
                name: summary
                for name, summary in resource_summaries.items()
                if name in missing_names
            }
            if selected:
                missing_references.setdefault(category, {})[resource_type] = selected
    return missing_references


def save_report(
    report_dir: Path,
    report_stem: str,
    excel_name: str,
    resources: Dict,
    validation_results: Dict,
    resource_folders: Dict,
    project_root: Path,
    references: Dict = None,
) -> None:
    """Write the human-readable and machine-readable validation reports."""
    references = references or {}
    report_text = generate_report(
        resources, validation_results, excel_name, references
    )
    text_report_file = report_dir / f"{report_stem}_validation.txt"
    text_report_file.write_text(report_text, encoding="utf-8")

    json_report_file = report_dir / f"{report_stem}_validation.json"
    json_data = {
        "timestamp": time.time(),
        "excel_name": excel_name,
        "project_root": str(project_root),
        "resources": {
            category: {
                resource_type: sorted(names)
                for resource_type, names in types.items()
            }
            for category, types in resources.items()
        },
        "validation_results": validation_results,
        "missing_references": get_missing_references(
            references, validation_results
        ),
        "resource_folders": resource_folders,
    }
    json_report_file.write_text(
        json.dumps(json_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info(f"文本报告已保存: {text_report_file}")
    logger.info(f"JSON 报告已保存: {json_report_file}")


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
            variant_module_file=str(config.paths.param_config_dir / "variant_mappings.py")
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
            config.resources.extensions,
            validate_source=config.resources.validate_source,
            filename_normalization=config.resources.filename_normalization,
            resource_resolvers=get_resource_resolvers(config),
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
        combined_resources = {}
        combined_references = {}
        report_dir = config.paths.output_dir / "validation_reports"
        report_dir.mkdir(parents=True, exist_ok=True)

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
                resources, references = extractor.extract_from_excel_with_references(
                    excel_data,
                    excel_file.name,
                    config=config,
                    sample_limit=config.resources.reference_sample_limit,
                )
            except Exception as e:
                logger.error(f"提取资源失败，跳过: {excel_file} - {e}")
                continue

            if not resources:
                logger.warning("未找到任何资源引用")
                continue

            # 显示提取的资源统计
            total_resources = sum(len(names) for types in resources.values() for names in types.values())
            logger.info(f"提取到 {total_resources} 个资源引用")
            merge_resources(combined_resources, resources)
            merge_references(
                combined_references,
                references,
                config.resources.reference_sample_limit,
            )

            # 验证资源
            try:
                validation_results = validator.validate_resources(resources, resource_folders)
            except Exception as e:
                logger.error(f"验证资源失败，跳过: {excel_file} - {e}")
                continue

            try:
                save_report(
                    report_dir,
                    excel_file.stem,
                    excel_file.name,
                    resources,
                    validation_results,
                    resource_folders,
                    config.resources.project_root,
                    references,
                )
            except Exception as e:
                logger.error(f"保存报告失败: {excel_file} - {e}")

        # Always refresh the aggregate report so an empty run cannot leave
        # stale validation data for the sync tool.
        combined_results = validator.validate_resources(
            combined_resources,
            resource_folders,
        )
        save_report(
            report_dir,
            "all_workbooks",
            "全部演出表格",
            combined_resources,
            combined_results,
            resource_folders,
            config.resources.project_root,
            combined_references,
        )

        logger.info("所有文件验证完成")

    except Exception as e:
        logger.critical(f"验证过程失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
