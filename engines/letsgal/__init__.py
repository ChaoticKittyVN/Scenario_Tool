"""LetsGal Studio Ren'Py-style code engine."""

from typing import List, Optional

from core.engine_processor import EngineProcessor
from core.engine_registry import register_engine

from .config import LetsGalConfig


@register_engine(
    name="letsgal",
    display_name="LetsGal Studio (Code)",
    file_extension=".txt",
    config_class=LetsGalConfig,
    description="LetsGal Studio Ren'Py 风格代码层",
)
def create_letsgal_processor(
    config: LetsGalConfig,
    translator,
    generator_categories: Optional[List[str]] = None,
):
    """Create a text-code processor for LetsGal Studio."""
    processor = EngineProcessor(
        "letsgal",
        translator,
        config,
        generator_categories or [],
    )
    processor.setup()
    return processor


__all__ = ["LetsGalConfig", "create_letsgal_processor"]
