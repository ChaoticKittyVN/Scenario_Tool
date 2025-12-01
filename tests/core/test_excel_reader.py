# tests/core/test_excel_reader.py
"""
ExcelReader模块的单元测试
"""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch

from core.excel_manager import ExcelFileManager, DataFrameProcessor
from core.config_manager import AppConfig


class TestExcelFileManager:
    """ExcelFileManager的测试类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.manager = ExcelFileManager(cache_enabled=False)
        
    def test_load_excel_file_not_found(self):
        """测试文件不存在的情况"""
        with pytest.raises(FileNotFoundError):
            self.manager.load_excel(Path("nonexistent_file.xlsx"))
    
    def test_get_sheet_names(self, sample_excel_file):
        """测试获取工作表名称"""
        sheet_names = self.manager.get_sheet_names(sample_excel_file)
        # 根据实际测试文件的工作表名称调整断言
        assert len(sheet_names) > 0
        # 如果有特定工作表名称，可以添加具体断言
        # assert "Sheet1" in sheet_names
    
    def test_get_sheet(self, sample_excel_file):
        """测试获取指定工作表"""
        # 获取第一个工作表名称
        sheet_names = self.manager.get_sheet_names(sample_excel_file)
        if sheet_names:
            first_sheet = sheet_names[0]
            df = self.manager.get_sheet(sample_excel_file, first_sheet)
            assert isinstance(df, pd.DataFrame)
            # 不检查是否为空，因为测试文件可能为空
    
    def test_cache_functionality(self, sample_excel_file):
        """测试缓存功能"""
        # 创建启用缓存的manager
        cached_manager = ExcelFileManager(cache_enabled=True)
        
        # 第一次加载
        data1 = cached_manager.load_excel(sample_excel_file)
        
        # 第二次加载应该从缓存获取
        with patch('pandas.read_excel') as mock_read:
            data2 = cached_manager.load_excel(sample_excel_file)
            mock_read.assert_not_called()  # 不应该调用read_excel
        
        assert data1 is data2  # 应该是同一个对象


class TestDataFrameProcessor:
    """DataFrameProcessor的测试类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.config = Mock()
        self.config.processing.ignore_mode = True
        self.config.processing.ignore_words = ["IGNORE", "SKIP"]
        
        self.processor = DataFrameProcessor(self.config)
    
    def test_extract_valid_rows_with_end_marker(self, sample_dataframe):
        """测试提取带END标记的有效行"""
        result = self.processor.extract_valid_rows(sample_dataframe, "test_sheet")
        
        # 应该只返回END标记之前的行
        assert len(result) == 3
        assert "END" not in result["Note"].values
    
    def test_extract_valid_rows_no_end_marker(self):
        """测试没有END标记的情况"""
        df = pd.DataFrame({
            "Note": ["A", "B", "C"],
            "Text": ["Text1", "Text2", "Text3"]
        })
        
        result = self.processor.extract_valid_rows(df, "test_sheet")
        assert result.empty
    
    def test_apply_ignore_rules(self, sample_dataframe):
        """测试应用忽略规则"""
        # 添加Ignore列
        df = sample_dataframe.copy()
        df["Ignore"] = ["", "IGNORE", "", "SKIP", ""]
        
        result = self.processor._apply_ignore_rules(df)
        
        # 应该过滤掉标记为IGNORE和SKIP的行
        assert len(result) == 3
        assert "IGNORE" not in result["Ignore"].values
        assert "SKIP" not in result["Ignore"].values
    
    def test_find_marker_position(self, sample_dataframe):
        """测试查找标记位置"""
        position = self.processor.find_marker_position(
            sample_dataframe, "Note", "END"
        )
        assert position == 3
    
    def test_get_column_data_existing(self, sample_dataframe):
        """测试获取存在的列数据"""
        series = self.processor.get_column_data(sample_dataframe, "Text")
        assert len(series) == len(sample_dataframe)
        assert series.iloc[0] == "Hello"
    
    def test_get_column_data_missing(self, sample_dataframe):
        """测试获取不存在的列数据"""
        series = self.processor.get_column_data(sample_dataframe, "NonExistent")
        assert len(series) == len(sample_dataframe)
        assert series.iloc[0] == ""  # 默认值


# 测试固件（Fixtures）
@pytest.fixture
def sample_excel_file():
    """使用项目中已有的测试Excel文件"""
    test_file_path = Path("tests/excel/test_sample_excel.xlsx")
    
    if not test_file_path.exists():
        pytest.skip(f"测试文件不存在: {test_file_path}")
    
    return test_file_path


@pytest.fixture
def sample_dataframe():
    """创建示例DataFrame用于测试（不依赖外部文件）"""
    return pd.DataFrame({
        "Name": ["Alice", "Bob", "Charlie", "END", "Extra"],
        "Text": ["Hello", "Hi", "Hey", "Goodbye", "ShouldNotBeHere"],
        "Note": ["", "", "", "END", ""]
    })