"""XML输出器"""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, List, Dict
from core.scenario_output.base import IOutputWriter, OutputFormat, OutputConfig
from core.logger import get_logger

logger = get_logger(__name__)


class XmlScenarioWriter(IOutputWriter):
    """XML输出器 - 用于结构化数据导出"""

    def __init__(self):
        self.supported_formats = [OutputFormat.XML]
    
    def write(self, data: Any, output_path: Path, config: OutputConfig) -> bool:
        """
        写入XML文件
        
        Args:
            data: 字典或字典列表
            output_path: 输出路径
            config: 输出配置
        """
        try:
            # 确保目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 准备数据
            xml_data = self._prepare_data(data, config)
            
            # 创建根元素
            root = ET.Element("scenario")
            
            # 转换数据为XML
            self._dict_to_xml(root, xml_data)
            
            # 创建ElementTree并写入文件
            tree = ET.ElementTree(root)
            ET.indent(tree, space="  ")  # Python 3.9+
            
            tree.write(
                output_path,
                encoding=config.encoding,
                xml_declaration=True
            )
            
            logger.info(f"XML文件已保存: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存XML文件失败: {e}")
            return False
    
    def _prepare_data(self, data: Any, config: OutputConfig) -> Dict[str, Any]:
        """准备数据"""
        if isinstance(data, dict):
            return data
        elif isinstance(data, list):
            # 将列表转换为字典，使用items作为键
            return {"items": data}
        elif hasattr(data, '__dict__'):
            return data.__dict__
        else:
            return {"data": str(data)}
    
    def _dict_to_xml(self, parent: ET.Element, data: Any, tag_name: str = "item") -> None:
        """递归将字典转换为XML元素"""
        if isinstance(data, dict):
            for key, value in data.items():
                # 清理键名，使其符合XML命名规范
                clean_key = str(key).replace(' ', '_').replace('-', '_')
                element = ET.SubElement(parent, clean_key)
                self._dict_to_xml(element, value, clean_key)
        elif isinstance(data, list):
            for item in data:
                element = ET.SubElement(parent, tag_name)
                self._dict_to_xml(element, item, tag_name)
        else:
            # 叶子节点，设置文本内容
            parent.text = str(data) if data is not None else ""
    
    def supports_format(self, format: OutputFormat) -> bool:
        return format in self.supported_formats
    
    def get_extension(self) -> str:
        return ".xml"

