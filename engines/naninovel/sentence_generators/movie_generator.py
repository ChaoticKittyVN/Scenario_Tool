from core.base_sentence_generator import BaseSentenceGenerator

class MovieGenerator(BaseSentenceGenerator):
    """视频生成器"""

    param_config = {
        "Movie": {
            "translate_type": "Movie",
            "format": "@movie {value} wait:true"
        }
    }

    @property
    def category(self):
        return "Movie"

    @property
    def priority(self) -> int:
        return 800

    def process(self, data):
        """
        处理视频参数

        Args:
            data: 参数字典

        Returns:
            List[str]: 生成的视频播放命令
        """
        if not self.can_process(data):
            return
        
        data = self.do_translate(data)

        movie = self.get_value("Movie", data)

        line = f"@movie {movie} wait:true"

        return [line]