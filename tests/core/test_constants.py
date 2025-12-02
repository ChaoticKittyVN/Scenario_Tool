"""
测试 constants 模块
"""
import pytest
from core.constants import (
    WindowMode,
    SpecialName,
    FileType,
    SheetName,
    ColumnName,
    Marker,
    DEFAULT_INDENT_SIZE,
    DEFAULT_BATCH_SIZE,
    DEFAULT_TRANSITION,
    EXCEL_EXTENSIONS,
    RENPY_EXTENSION,
    NANINOVEL_EXTENSION,
    TEMP_FILE_PREFIX
)


class TestEnumValues:
    """测试所有枚举的值和类型"""

    @pytest.mark.parametrize("enum_member,expected_value", [
        # WindowMode
        (WindowMode.SHOW, "显示"),
        (WindowMode.HIDE, "隐藏"),
        (WindowMode.SHOW_AND_HIDE, "显示和隐藏"),
        # SpecialName
        (SpecialName.RENPY_COMMAND, "renpy"),
        (SpecialName.NANINOVEL_COMMAND, "naninovel"),
        # FileType
        (FileType.BACKGROUND, "Background"),
        (FileType.CHARACTER, "Character"),
        (FileType.MUSIC, "Music"),
        (FileType.SOUND, "Sound"),
        (FileType.VOICE, "Voice"),
        (FileType.EVENT, "Event"),
        # SheetName
        (SheetName.PARAM_SHEET, "参数表"),
        # ColumnName
        (ColumnName.NOTE, "Note"),
        (ColumnName.IGNORE, "Ignore"),
        (ColumnName.NAME, "Name"),
        (ColumnName.TEXT, "Text"),
        (ColumnName.CHARACTER, "Character"),
        (ColumnName.BACKGROUND, "Background"),
        # Marker
        (Marker.END, "END"),
    ])
    def test_enum_values_and_types(self, enum_member, expected_value):
        """测试枚举成员的值和类型"""
        assert enum_member == expected_value
        assert isinstance(enum_member, str)


class TestEnumMembers:
    """测试枚举成员完整性"""

    @pytest.mark.parametrize("enum_class,expected_values,expected_count", [
        (WindowMode, ["显示", "隐藏", "显示和隐藏"], 3),
        (SpecialName, ["renpy", "naninovel"], 2),
        (FileType, ["Background", "Character", "Music", "Sound", "Voice", "Event"], 6),
        (SheetName, ["参数表"], 1),
        (ColumnName, ["Note", "Ignore", "Speaker", "Text", "Character", "Background"], 6),
        (Marker, ["END"], 1),
    ])
    def test_enum_members(self, enum_class, expected_values, expected_count):
        """测试枚举包含所有预期成员"""
        members = [member.value for member in enum_class]
        assert len(members) == expected_count
        for expected_value in expected_values:
            assert expected_value in members


class TestDefaultConstants:
    """测试默认常量"""

    @pytest.mark.parametrize("constant,expected_value,expected_type", [
        (DEFAULT_INDENT_SIZE, 4, int),
        (DEFAULT_BATCH_SIZE, 100, int),
        (DEFAULT_TRANSITION, "dissolve", str),
    ])
    def test_default_constants(self, constant, expected_value, expected_type):
        """测试默认常量的值和类型"""
        assert constant == expected_value
        assert isinstance(constant, expected_type)


class TestFileExtensions:
    """测试文件扩展名常量"""

    def test_excel_extensions(self):
        """测试 Excel 文件扩展名"""
        assert EXCEL_EXTENSIONS == ['.xlsx', '.xls']
        assert isinstance(EXCEL_EXTENSIONS, list)
        assert len(EXCEL_EXTENSIONS) == 2
        assert '.xlsx' in EXCEL_EXTENSIONS
        assert '.xls' in EXCEL_EXTENSIONS

    @pytest.mark.parametrize("extension,expected_value", [
        (RENPY_EXTENSION, '.rpy'),
        (NANINOVEL_EXTENSION, '.nani'),
    ])
    def test_engine_extensions(self, extension, expected_value):
        """测试引擎文件扩展名"""
        assert extension == expected_value
        assert isinstance(extension, str)


class TestTempFilePrefix:
    """测试临时文件前缀"""

    def test_temp_file_prefix(self):
        """测试临时文件前缀"""
        assert TEMP_FILE_PREFIX == '~'
        assert isinstance(TEMP_FILE_PREFIX, str)
        assert len(TEMP_FILE_PREFIX) == 1


class TestEnumComparison:
    """测试枚举比较功能"""

    @pytest.mark.parametrize("enum1,enum2,should_equal", [
        # 相等比较
        (WindowMode.SHOW, WindowMode.SHOW, True),
        (FileType.MUSIC, FileType.MUSIC, True),
        # 不相等比较
        (WindowMode.SHOW, WindowMode.HIDE, False),
        (FileType.MUSIC, FileType.SOUND, False),
    ])
    def test_enum_equality(self, enum1, enum2, should_equal):
        """测试枚举相等性比较"""
        if should_equal:
            assert enum1 == enum2
        else:
            assert enum1 != enum2

    @pytest.mark.parametrize("enum_member,string_value", [
        (WindowMode.SHOW, "显示"),
        (SpecialName.RENPY_COMMAND, "renpy"),
        (FileType.MUSIC, "Music"),
    ])
    def test_enum_string_comparison(self, enum_member, string_value):
        """测试枚举与字符串比较"""
        assert enum_member == string_value


class TestEnumIteration:
    """测试枚举迭代功能"""

    @pytest.mark.parametrize("enum_class,expected_members,expected_count", [
        (WindowMode, [WindowMode.SHOW, WindowMode.HIDE, WindowMode.SHOW_AND_HIDE], 3),
        (FileType, [FileType.BACKGROUND, FileType.MUSIC], 6),  # 只检查部分成员
        (ColumnName, [ColumnName.NOTE, ColumnName.NAME], 6),  # 只检查部分成员
    ])
    def test_enum_iteration(self, enum_class, expected_members, expected_count):
        """测试枚举迭代功能"""
        members = list(enum_class)
        assert len(members) == expected_count
        for expected_member in expected_members:
            assert expected_member in members
