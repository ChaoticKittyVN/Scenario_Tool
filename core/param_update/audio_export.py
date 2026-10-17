"""Export project-scoped audio records without inferring listening facts."""

import json
from pathlib import Path
from typing import Any, Dict

from core.logger import get_logger

logger = get_logger()


class AudioDocExportMixin:
    """Build indexes into the same records used by parameter mappings."""

    def build_audio_document(self) -> Dict[str, Any]:
        if not self.audio_data_enabled:
            raise ValueError("音频资料导出需要显式启用 audio_data.enabled")
        sources = self._load_audio_sources()
        document = {
            "schema_version": 1,
            "engine": self.engine_type,
            "default": None,
            "projects": {},
        }
        for project, source in self._effective_audio_sources(sources).items():
            types = {}
            for audio_type, records in source.sheets.items():
                scenario_index = {}
                for excel_param, record in records.items():
                    scenario_index.setdefault(record["scenario_param"], []).append(
                        excel_param
                    )
                types[audio_type] = {
                    "records": records,
                    "scenario_index": scenario_index,
                }
            scope = {
                "source_file": str(source.path),
                "source_files": [str(path) for path in source.source_files],
                "types": types,
            }
            if project is None:
                document["default"] = scope
            else:
                document["projects"][project] = scope
        return document

    def export_audio_document(self, dry_run: bool = False) -> bool:
        try:
            document = self.build_audio_document()
            output_file = Path(self.config.audio_doc_export.output_file)
            if output_file.suffix.lower() != ".json":
                raise ValueError(
                    "audio_doc_export.output_file 必须是 .json 文件，不能覆盖音频工作簿或映射模块"
                )
            if not output_file.is_absolute():
                output_file = Path(self.config.paths.param_config_dir) / output_file
            content = (
                json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False)
                + "\n"
            )
            logger.info(f"{'将生成' if dry_run else '生成'}音频资料文档: {output_file}")
            if dry_run:
                return True
            output_file.parent.mkdir(parents=True, exist_ok=True)
            if (
                output_file.exists()
                and output_file.read_text(encoding="utf-8") == content
            ):
                logger.info("音频资料文档内容未变化，跳过保存")
                return True
            output_file.write_text(content, encoding="utf-8")
            return True
        except Exception as exc:
            logger.error(f"生成音频资料文档失败: {exc}", exc_info=True)
            return False
