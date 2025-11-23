"""
测试 ParamTranslator 类
"""
import pytest
import tempfile
from pathlib import Path
from core.param_translator import ParamTranslator


class TestParamTranslator:
    """测试 ParamTranslator 类"""

    @pytest.fixture
    def mock_param_mappings_file(self, tmp_path):
        """创建模拟的参数映射文件"""
        mappings_file = tmp_path / "param_mappings.py"
        mappings_content = """
PARAM_MAPPINGS = {
    "Music": {
        "音乐1": "music1",
        "音乐2": "music2",
        "背景音乐": "bgm_main"
    },
    "Speaker": {
        "角色A": "character_a",
        "角色B": "character_b"
    },
    "Background": {
        "背景1": "bg_1",
        "背景2": "bg_2"
    },
    "Varient": {
        "差分1": "variant_1",
        "差分2": "variant_2"
    }
}
"""
        mappings_file.write_text(mappings_content, encoding="utf-8")
        return mappings_file

    @pytest.fixture
    def mock_varient_mappings_file(self, tmp_path):
        """创建模拟的差分参数映射文件"""
        varient_file = tmp_path / "varient_mappings.py"
        varient_content = """
VARIENT_MAPPINGS = {
    "角色A": {
        "开心": "happy",
        "难过": "sad"
    },
    "角色B": {
        "生气": "angry",
        "惊讶": "surprised"
    }
}
"""
        varient_file.write_text(varient_content, encoding="utf-8")
        return varient_file

    @pytest.fixture
    def translator(self, mock_param_mappings_file, mock_varient_mappings_file):
        """创建 ParamTranslator 实例"""
        return ParamTranslator(
            module_file=str(mock_param_mappings_file),
            varient_module_file=str(mock_varient_mappings_file)
        )

    def test_init_success(self, translator):
        """测试成功初始化"""
        assert translator is not None
        assert len(translator.mappings) == 4
        assert len(translator.varient_mappings) == 2

    def test_init_with_missing_files(self, tmp_path):
        """测试文件不存在时的初始化"""
        translator = ParamTranslator(
            module_file=str(tmp_path / "nonexistent.py"),
            varient_module_file=str(tmp_path / "nonexistent2.py")
        )
        assert translator.mappings == {}
        assert translator.varient_mappings == {}

    @pytest.mark.parametrize("param_type,param_value,expected", [
        # 正常翻译
        ("Music", "音乐1", "music1"),
        ("Music", "音乐2", "music2"),
        ("Speaker", "角色A", "character_a"),
        ("Background", "背景1", "bg_1"),
        # 参数不存在，返回原值
        ("Music", "不存在的音乐", "不存在的音乐"),
        ("Speaker", "不存在的角色", "不存在的角色"),
        # 参数类型不存在，返回原值
        ("NotExistType", "任意值", "任意值"),
        # 空字符串
        ("Music", "", ""),
    ])
    def test_translate(self, translator, param_type, param_value, expected):
        """测试参数翻译"""
        assert translator.translate(param_type, param_value) == expected

    @pytest.mark.parametrize("param_value,role,expected", [
        # 不提供角色名，从基础映射中查找
        ("差分1", None, "variant_1"),
        ("差分2", None, "variant_2"),
        ("不存在的差分", None, "不存在的差分"),
        # 提供角色名，使用角色特定映射
        ("开心", "角色A", "happy"),
        ("难过", "角色A", "sad"),
        ("生气", "角色B", "angry"),
        ("惊讶", "角色B", "surprised"),
        # 角色不存在，返回原值
        ("开心", "不存在的角色", "开心"),
        # 角色存在但参数不存在，返回原值
        ("不存在的表情", "角色A", "不存在的表情"),
    ])
    def test_translate_varient(self, translator, param_value, role, expected):
        """测试差分参数翻译"""
        assert translator.translate_varient(param_value, role=role) == expected

    def test_translate_batch(self, translator):
        """测试批量翻译"""
        params = ["音乐1", "音乐2", "背景音乐"]
        expected = ["music1", "music2", "bgm_main"]
        assert translator.translate_batch("Music", params) == expected

    def test_translate_batch_with_missing_params(self, translator):
        """测试批量翻译包含不存在的参数"""
        params = ["音乐1", "不存在的音乐", "音乐2"]
        expected = ["music1", "不存在的音乐", "music2"]
        assert translator.translate_batch("Music", params) == expected

    def test_get_available_types(self, translator):
        """测试获取可用参数类型"""
        types = translator.get_available_types()
        assert "Music" in types
        assert "Speaker" in types
        assert "Background" in types
        assert "Varient" in types
        assert len(types) == 4

    @pytest.mark.parametrize("param_type,expected_result", [
        ("Music", ["音乐1", "音乐2", "背景音乐"]),
        ("NotExist", []),
    ])
    def test_get_params_for_type(self, translator, param_type, expected_result):
        """测试获取指定类型的所有原始参数"""
        params = translator.get_params_for_type(param_type)
        if expected_result:
            for expected_param in expected_result:
                assert expected_param in params
            assert len(params) == len(expected_result)
        else:
            assert params == []

    @pytest.mark.parametrize("param_type,expected_result", [
        ("Music", ["music1", "music2", "bgm_main"]),
        ("NotExist", []),
    ])
    def test_get_translations_for_type(self, translator, param_type, expected_result):
        """测试获取指定类型的所有翻译后参数"""
        translations = translator.get_translations_for_type(param_type)
        if expected_result:
            for expected_translation in expected_result:
                assert expected_translation in translations
            assert len(translations) == len(expected_result)
        else:
            assert translations == []

    @pytest.mark.parametrize("param_type,param_value,expected", [
        # 存在的映射
        ("Music", "音乐1", True),
        ("Speaker", "角色A", True),
        # 不存在的映射
        ("Music", "不存在", False),
        ("NotExist", "任意值", False),
    ])
    def test_has_mapping(self, translator, param_type, param_value, expected):
        """测试检查映射是否存在"""
        assert translator.has_mapping(param_type, param_value) is expected

    def test_special_characters_in_param(self, tmp_path):
        """测试包含特殊字符的参数"""
        # 创建包含特殊字符的映射
        mappings_file = tmp_path / "special_mappings.py"
        mappings_content = """
PARAM_MAPPINGS = {
    "Test": {
        "参数-1": "param_1",
        "参数_2": "param_2",
        "参数(3)": "param_3"
    }
}
"""
        mappings_file.write_text(mappings_content, encoding="utf-8")

        translator = ParamTranslator(
            module_file=str(mappings_file),
            varient_module_file=str(tmp_path / "nonexistent.py")
        )

        assert translator.translate("Test", "参数-1") == "param_1"
        assert translator.translate("Test", "参数_2") == "param_2"
        assert translator.translate("Test", "参数(3)") == "param_3"
