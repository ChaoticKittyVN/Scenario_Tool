"""
Naninovel Background Generator
生成背景相关命令
"""
from core.base_sentence_generator import BaseSentenceGenerator
from engines.naninovel.param_processor import ParamProcessor


class BackgroundGenerator(BaseSentenceGenerator):
    """背景生成器"""

    param_config = {
        "Back": {
            "translate_type": "Background"
        },
        "BackID": {},
        "BackScale": {},
        "BackPos": {},
        "BackVisible": {},
        "BackWait": {},
        "Dissolve": {},
        "DissolveParam": {},
        "BackTime": {}
    }

    def __init__(self, translator, engine_config):
        super().__init__(translator, engine_config)
        self.param_processor = ParamProcessor()

    @property
    def category(self):
        return "Background"

    @property
    def priority(self) -> int:
        return 200

    def process(self, data):
        """
        处理背景参数

        Args:
            data: 参数字典

        Returns:
            List[str]: 生成的背景命令
        """
        if not self.can_process(data):
            return None

        data = self.do_translate(data)

        background = data.get("Back")
        if not background:
            return []

        # 构建场景命令
        image = background

        # 添加各种参数
        id_param = self.param_processor._process_id_parameter(data.get("BackID"))
        pos = self.param_processor._process_pos_parameter(data.get("BackPos"))
        scale = self.param_processor._process_scale_parameter(data.get("BackScale"))
        visible = self.param_processor._process_visible_parameter(data.get("BackVisible"))
        dissolve = self.param_processor._process_dissolve_parameter(
            data.get("Dissolve"),
            data.get("DissolveParam")
        )
        wait = self.param_processor._process_wait_parameter(data.get("BackWait"))
        time = self.param_processor._process_time_parameter(data.get("BackTime"))

        # 构建最终命令
        result = f"@back {image}{id_param}{pos}{scale}{visible}{dissolve}{wait}{time}"
        return [result]
