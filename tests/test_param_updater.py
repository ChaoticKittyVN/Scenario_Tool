"""
测试 ParamUpdater 类
"""
import os

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import Mock, patch
from update_param import ParamUpdater, parse_args
from core.config_manager import AppConfig


class TestParamUpdater:
    """测试 ParamUpdater 类"""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """创建模拟的配置对象"""
        config = Mock(spec=AppConfig)
        config.engine = Mock()
        config.engine.engine_type = "renpy"
        config.paths = Mock()
        config.paths.param_config_dir = tmp_path / "param_config"
        config.paths.input_dir = tmp_path / "input"

        # 创建必要的目录
        config.paths.param_config_dir.mkdir(parents=True, exist_ok=True)
        config.paths.input_dir.mkdir(parents=True, exist_ok=True)

        return config

    @pytest.fixture
    def mock_param_excel(self, tmp_path):
        """创建模拟的参数 Excel 文件"""
        param_file = tmp_path / "param_config" / "param_data_renpy.xlsx"
        param_file.parent.mkdir(parents=True, exist_ok=True)

        # 创建多个工作表
        with pd.ExcelWriter(param_file, engine='openpyxl') as writer:
            # Music 工作表
            df_music = pd.DataFrame({
                'ExcelParam': ['音乐1', '音乐2', '背景音乐'],
                'ScenarioParam': ['music1', 'music2', 'bgm_main']
            })
            df_music.to_excel(writer, sheet_name='Music', index=False)

            # Speaker 工作表
            df_speaker = pd.DataFrame({
                'ExcelParam': ['角色A', '角色B'],
                'ScenarioParam': ['character_a', 'character_b']
            })
            df_speaker.to_excel(writer, sheet_name='Speaker', index=False)

            # Background 工作表
            df_bg = pd.DataFrame({
                'ExcelParam': ['背景1', '背景2'],
                'ScenarioParam': ['bg_1', 'bg_2']
            })
            df_bg.to_excel(writer, sheet_name='Background', index=False)

            # Variant 工作表
            df_variant = pd.DataFrame({
                'ExcelParam': ['差分1', '差分2'],
                'ScenarioParam': ['variant_1', 'variant_2']
            })
            df_variant.to_excel(writer, sheet_name='Variant', index=False)

        return param_file

    @pytest.fixture
    def mock_variant_excel(self, tmp_path):
        """创建模拟的差分参数 Excel 文件"""
        variant_file = tmp_path / "param_config" / "variant_data.xlsx"

        with pd.ExcelWriter(variant_file, engine='openpyxl') as writer:
            # 角色A 工作表
            df_role_a = pd.DataFrame({
                'ExcelParam': ['开心', '难过'],
                'ScenarioParam': ['happy', 'sad']
            })
            df_role_a.to_excel(writer, sheet_name='角色A', index=False)

            # 角色B 工作表
            df_role_b = pd.DataFrame({
                'ExcelParam': ['生气', '惊讶'],
                'ScenarioParam': ['angry', 'surprised']
            })
            df_role_b.to_excel(writer, sheet_name='角色B', index=False)

            # 模板工作表（应该被处理但可能是空的）
            df_template = pd.DataFrame({
                'ExcelParam': [],
                'ScenarioParam': []
            })
            df_template.to_excel(writer, sheet_name='参数表模板', index=False)

        return variant_file

    @pytest.fixture
    def updater(self, mock_config):
        """创建 ParamUpdater 实例"""
        return ParamUpdater(mock_config)

    def test_init(self, updater, mock_config):
        """测试初始化"""
        assert updater.config == mock_config
        assert updater.engine_type == "renpy"

    def test_read_param_file_success(self, updater, mock_param_excel):
        """测试成功读取参数文件"""
        mappings = updater.read_param_file(mock_param_excel)

        # 验证读取到的映射
        assert 'Music' in mappings
        assert 'Speaker' in mappings
        assert 'Background' in mappings
        assert 'Variant' in mappings

        # 验证映射内容
        assert mappings['Music']['音乐1'] == 'music1'
        assert mappings['Speaker']['角色A'] == 'character_a'
        assert mappings['Background']['背景1'] == 'bg_1'

    def test_read_param_file_not_exist(self, updater, tmp_path):
        """测试读取不存在的文件"""
        non_existent = tmp_path / "nonexistent.xlsx"
        mappings = updater.read_param_file(non_existent)

        assert mappings == {}

    def test_read_param_file_skip_template(self, updater, tmp_path):
        """测试跳过模板工作表"""
        param_file = tmp_path / "test_param.xlsx"

        with pd.ExcelWriter(param_file, engine='openpyxl') as writer:
            # 正常工作表
            df_normal = pd.DataFrame({
                'ExcelParam': ['参数1'],
                'ScenarioParam': ['param1']
            })
            df_normal.to_excel(writer, sheet_name='Normal', index=False)

            # 模板工作表
            df_template = pd.DataFrame({
                'ExcelParam': ['模板参数'],
                'ScenarioParam': ['template_param']
            })
            df_template.to_excel(writer, sheet_name='参数表模板', index=False)

        # skip_template=True 时应该跳过模板
        mappings = updater.read_param_file(param_file, skip_template=True)
        assert 'Normal' in mappings
        assert '参数表模板' not in mappings

        # skip_template=False 时应该包含模板
        mappings = updater.read_param_file(param_file, skip_template=False)
        assert 'Normal' in mappings
        assert '参数表模板' in mappings

    def test_read_param_file_missing_columns(self, updater, tmp_path):
        """测试缺少必需列的工作表"""
        param_file = tmp_path / "test_param.xlsx"

        with pd.ExcelWriter(param_file, engine='openpyxl') as writer:
            # 缺少 ScenarioParam 列
            df_missing = pd.DataFrame({
                'ExcelParam': ['参数1'],
                'WrongColumn': ['wrong']
            })
            df_missing.to_excel(writer, sheet_name='MissingColumn', index=False)

        mappings = updater.read_param_file(param_file)

        # 应该跳过缺少必需列的工作表
        assert 'MissingColumn' not in mappings

    def test_collect_validation_data(self, updater, mock_param_excel):
        """测试收集验证数据"""
        validation_data = updater.collect_validation_data(mock_param_excel)

        # 验证收集到的数据
        assert 'Music' in validation_data
        assert 'Speaker' in validation_data
        assert 'Background' in validation_data
        assert 'Variant' in validation_data

        # 验证数据内容
        assert '音乐1' in validation_data['Music']
        assert '音乐2' in validation_data['Music']
        assert '角色A' in validation_data['Speaker']
        assert '背景1' in validation_data['Background']

    def test_collect_validation_data_with_variant(self, updater, mock_param_excel, mock_variant_excel):
        """测试收集验证数据（包含差分参数）"""
        validation_data = updater.collect_validation_data(mock_param_excel, mock_variant_excel)

        # 验证差分参数被合并到 Variant 列
        assert 'Variant' in validation_data

        # 应该包含基础差分参数
        assert '差分1' in validation_data['Variant']
        assert '差分2' in validation_data['Variant']

        # 应该包含角色特定的差分参数
        assert '开心' in validation_data['Variant']
        assert '难过' in validation_data['Variant']
        assert '生气' in validation_data['Variant']
        assert '惊讶' in validation_data['Variant']

        # 验证去重和排序
        variant_list = validation_data['Variant']
        assert len(variant_list) == len(set(variant_list))  # 无重复
        assert variant_list == sorted(variant_list)  # 已排序

    def test_collect_validation_data_file_not_exist(self, updater, tmp_path):
        """测试文件不存在时的行为"""
        non_existent = tmp_path / "nonexistent.xlsx"
        validation_data = updater.collect_validation_data(non_existent)

        assert validation_data == {}

    def test_collect_validation_data_empty_values(self, updater, tmp_path):
        """测试处理空值和空字符串"""
        param_file = tmp_path / "test_param.xlsx"

        with pd.ExcelWriter(param_file, engine='openpyxl') as writer:
            df = pd.DataFrame({
                'ExcelParam': ['参数1', '', None, '  ', '参数2'],
                'ScenarioParam': ['param1', 'empty', 'none', 'spaces', 'param2']
            })
            df.to_excel(writer, sheet_name='Test', index=False)

        validation_data = updater.collect_validation_data(param_file)

        # 空值会被排除，但仅含空格的 ExcelParam 需要原样保留。
        assert 'Test' in validation_data
        assert '参数1' in validation_data['Test']
        assert '参数2' in validation_data['Test']
        assert '' not in validation_data['Test']
        assert '  ' in validation_data['Test']

    def test_generate_mappings_file(self, updater, tmp_path):
        """测试生成映射文件"""
        mappings = {
            'Music': {'音乐1': 'music1', '音乐2': 'music2'},
            'Speaker': {'角色A': 'character_a'}
        }

        output_file = tmp_path / "param_mappings.py"
        updater.generate_mappings_file(mappings, output_file)

        # 验证文件被创建
        assert output_file.exists()

        # 验证文件内容
        content = output_file.read_text(encoding='utf-8')
        assert 'PARAM_MAPPINGS' in content
        assert 'Music' in content
        assert 'Speaker' in content
        assert 'music1' in content
        assert 'character_a' in content

    def test_generate_mappings_file_variant(self, updater, tmp_path):
        """测试生成差分映射文件"""
        variant_mappings = {
            '角色A': {'开心': 'happy'},
            '角色B': {'生气': 'angry'}
        }

        output_file = tmp_path / "variant_mappings.py"
        updater.generate_mappings_file(variant_mappings, output_file)

        # 验证文件被创建
        assert output_file.exists()

        # 验证文件内容
        content = output_file.read_text(encoding='utf-8')
        assert 'VARIANT_MAPPINGS' in content
        assert '角色A' in content
        assert 'happy' in content

    def test_update_scenario_param_sheets_no_validation_data(self, updater):
        """测试没有验证数据时的行为"""
        result = updater.update_scenario_param_sheets({})
        assert result is False

    def test_update_scenario_param_sheets_input_dir_not_exist(self, updater, tmp_path):
        """测试输入目录不存在时的行为"""
        updater.config.paths.input_dir = tmp_path / "nonexistent"
        validation_data = {'Music': ['音乐1']}

        result = updater.update_scenario_param_sheets(validation_data)
        assert result is False

    def test_update_scenario_param_sheets_no_excel_files(self, updater):
        """测试没有 Excel 文件时的行为"""
        validation_data = {'Music': ['音乐1']}

        result = updater.update_scenario_param_sheets(validation_data)
        # 没有文件时应该返回 True（不算错误）
        assert result is True

    def test_update_scenario_param_sheets_with_param_sheet(self, updater):
        """测试更新包含参数表的 Excel 文件"""
        from openpyxl import Workbook

        # 创建一个包含"参数表"的 Excel 文件
        excel_file = updater.config.paths.input_dir / "test_scenario.xlsx"

        wb = Workbook()
        ws = wb.active
        ws.title = "参数表"

        # 添加表头和旧数据
        ws['A1'] = 'Music'
        ws['B1'] = 'Speaker'
        ws['A2'] = '旧音乐1'
        ws['A3'] = '旧音乐2'
        ws['B2'] = '旧角色A'

        wb.save(excel_file)
        wb.close()

        # 准备新的验证数据
        validation_data = {
            'Music': ['音乐1', '音乐2', '音乐3'],
            'Speaker': ['角色A', '角色B']
        }

        # 执行更新
        result = updater.update_scenario_param_sheets(validation_data)

        # 验证结果
        assert result is True

        # 验证文件已更新
        from openpyxl import load_workbook
        wb = load_workbook(excel_file)
        ws = wb['参数表']

        # 验证 Music 列已更新（列顺序由当前生成器契约决定）
        music_column = next(cell.column for cell in ws[1] if cell.value == 'Music')
        music_values = []
        for row in range(2, ws.max_row + 1):
            value = ws.cell(row=row, column=music_column).value
            if value:
                music_values.append(value)

        assert len(music_values) == 3
        assert '音乐1' in music_values
        assert '音乐3' in music_values

        wb.close()

    def test_update_scenario_param_sheets_without_param_sheet(self, updater):
        """测试处理没有参数表的 Excel 文件"""
        # 创建一个没有"参数表"的 Excel 文件
        excel_file = updater.config.paths.input_dir / "no_param_sheet.xlsx"

        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            df = pd.DataFrame({'Data': [1, 2, 3]})
            df.to_excel(writer, sheet_name='Sheet1', index=False)

        validation_data = {'Music': ['音乐1']}

        # 缺少参数表时应自动创建。
        result = updater.update_scenario_param_sheets(validation_data)
        assert result is True

        from openpyxl import load_workbook
        wb = load_workbook(excel_file)
        assert '参数表' in wb.sheetnames
        ws = wb['参数表']
        music_column = next(cell.column for cell in ws[1] if cell.value == 'Music')
        assert ws.cell(row=2, column=music_column).value == '音乐1'
        wb.close()

    def test_update_scenario_param_sheets_skip_temp_files(self, updater):
        """测试跳过临时文件（以 ~ 开头）"""
        from openpyxl import Workbook

        # 创建临时文件
        temp_file = updater.config.paths.input_dir / "~temp.xlsx"

        wb = Workbook()
        ws = wb.active
        ws.title = "参数表"
        ws['A1'] = 'Music'
        wb.save(temp_file)
        wb.close()

        validation_data = {'Music': ['音乐1']}

        # 应该跳过临时文件
        result = updater.update_scenario_param_sheets(validation_data)
        assert result is True  # 没有找到非临时文件，返回 True

    def test_update_scenario_param_sheets_no_changes_needed(self, updater):
        """测试当参数表已经是最新时的行为"""
        from openpyxl import Workbook

        # 创建一个已经包含正确数据的 Excel 文件
        excel_file = updater.config.paths.input_dir / "up_to_date.xlsx"

        wb = Workbook()
        ws = wb.active
        ws.title = "参数表"

        # 添加表头和数据（与验证数据相同）
        ws['A1'] = 'Music'
        ws['B1'] = 'Speaker'
        ws['A2'] = '音乐1'
        ws['A3'] = '音乐2'
        ws['B2'] = '角色A'

        wb.save(excel_file)
        wb.close()

        # 使用相同的数据
        validation_data = {
            'Music': ['音乐1', '音乐2'],
            'Speaker': ['角色A']
        }

        # 执行更新
        result = updater.update_scenario_param_sheets(validation_data)

        # 应该检测到需要创建命名区域，所以返回 True
        assert result is True

    def test_update_scenario_param_sheets_with_named_ranges(self, updater):
        """测试创建命名区域"""
        from openpyxl import Workbook, load_workbook

        # 创建 Excel 文件
        excel_file = updater.config.paths.input_dir / "with_ranges.xlsx"

        wb = Workbook()
        ws = wb.active
        ws.title = "参数表"
        ws['A1'] = 'Music'
        ws['B1'] = 'Speaker'
        ws['A2'] = '音乐1'
        ws['B2'] = '角色A'

        wb.save(excel_file)
        wb.close()

        validation_data = {
            'Music': ['音乐1', '音乐2'],
            'Speaker': ['角色A', '角色B']
        }

        # 执行更新
        result = updater.update_scenario_param_sheets(validation_data)
        assert result is True

        # 验证命名区域已创建
        wb = load_workbook(excel_file)

        # 检查 MusicList 命名区域
        assert 'MusicList' in wb.defined_names
        music_range = wb.defined_names['MusicList']
        assert 'OFFSET' in music_range.attr_text
        assert 'COUNTA' in music_range.attr_text

        wb.close()

    def test_update_scenario_param_sheets_multiple_files(self, updater):
        """测试同时处理多个 Excel 文件"""
        from openpyxl import Workbook, load_workbook

        # 创建多个 Excel 文件
        for i in range(3):
            excel_file = updater.config.paths.input_dir / f"scenario_{i}.xlsx"

            wb = Workbook()
            ws = wb.active
            ws.title = "参数表"
            ws['A1'] = 'Music'
            ws['A2'] = '旧音乐'

            wb.save(excel_file)
            wb.close()

        validation_data = {
            'Music': ['音乐1', '音乐2']
        }

        # 执行更新
        result = updater.update_scenario_param_sheets(validation_data)
        assert result is True

        # 验证所有文件都已更新
        for i in range(3):
            excel_file = updater.config.paths.input_dir / f"scenario_{i}.xlsx"
            wb = load_workbook(excel_file)
            ws = wb['参数表']

            # 验证数据已更新
            music_column = next(cell.column for cell in ws[1] if cell.value == 'Music')
            music_col_values = []
            for row in range(2, ws.max_row + 1):
                value = ws.cell(row=row, column=music_column).value
                if value:
                    music_col_values.append(value)

            assert len(music_col_values) == 2
            assert '音乐1' in music_col_values
            wb.close()

    def test_update_scenario_param_sheets_with_explicit_workbooks(self, updater, tmp_path):
        """显式工作簿列表应绕过 input_dir，只更新指定文件。"""
        from openpyxl import Workbook, load_workbook

        explicit_file = tmp_path / "explicit.xlsx"
        untouched_file = updater.config.paths.input_dir / "untouched.xlsx"
        for excel_file in (explicit_file, untouched_file):
            wb = Workbook()
            ws = wb.active
            ws.title = "参数表"
            ws["A1"] = "Music"
            ws["A2"] = "旧音乐"
            wb.save(excel_file)
            wb.close()

        validation_data = {"Music": ["音乐1", "音乐2"]}
        result = updater.update_scenario_param_sheets(validation_data, [explicit_file])

        assert result is True
        explicit_wb = load_workbook(explicit_file)
        untouched_wb = load_workbook(untouched_file)
        explicit_sheet = explicit_wb["参数表"]
        music_column = next(
            cell.column for cell in explicit_sheet[1] if cell.value == "Music"
        )
        assert explicit_sheet.cell(row=2, column=music_column).value == "音乐1"
        assert untouched_wb["参数表"]["A2"].value == "旧音乐"
        explicit_wb.close()
        untouched_wb.close()

    def test_update_scenario_param_sheets_missing_explicit_workbook(self, updater, tmp_path):
        """显式目标不存在时不应回退处理 input_dir。"""
        validation_data = {"Music": ["音乐1"]}

        result = updater.update_scenario_param_sheets(
            validation_data,
            [tmp_path / "missing.xlsx"],
        )

        assert result is True


class TestParamUpdaterIntegration:
    """集成测试：测试完整的参数更新流程"""

    @pytest.fixture
    def full_setup(self, tmp_path):
        """创建完整的测试环境"""
        # 创建配置
        config = Mock(spec=AppConfig)
        config.engine = Mock()
        config.engine.engine_type = "renpy"
        config.paths = Mock()
        config.paths.param_config_dir = tmp_path / "param_config"
        config.paths.input_dir = tmp_path / "input"

        # 创建目录
        config.paths.param_config_dir.mkdir(parents=True)
        config.paths.input_dir.mkdir(parents=True)

        # 创建参数文件
        param_file = config.paths.param_config_dir / "param_data_renpy.xlsx"
        with pd.ExcelWriter(param_file, engine='openpyxl') as writer:
            df_music = pd.DataFrame({
                'ExcelParam': ['音乐1', '音乐2'],
                'ScenarioParam': ['music1', 'music2']
            })
            df_music.to_excel(writer, sheet_name='Music', index=False)

        return config, param_file

    def test_full_workflow(self, full_setup):
        """测试完整的工作流程"""
        config, param_file = full_setup
        updater = ParamUpdater(config)

        # 1. 读取参数文件
        mappings = updater.read_param_file(param_file)
        assert 'Music' in mappings

        # 2. 生成映射文件
        output_file = config.paths.param_config_dir / "param_mappings.py"
        updater.generate_mappings_file(mappings, output_file)
        assert output_file.exists()

        # 3. 收集验证数据
        validation_data = updater.collect_validation_data(param_file)
        assert 'Music' in validation_data
        assert '音乐1' in validation_data['Music']


class TestExceptionHandling:
    """测试异常处理"""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """创建模拟配置"""
        config = Mock(spec=AppConfig)
        config.engine = Mock()
        config.engine.engine_type = "renpy"
        config.paths = Mock()
        config.paths.param_config_dir = tmp_path / "param_config"
        config.paths.input_dir = tmp_path / "input"
        config.paths.param_config_dir.mkdir(parents=True, exist_ok=True)
        config.paths.input_dir.mkdir(parents=True, exist_ok=True)
        return config

    @pytest.fixture
    def updater(self, mock_config):
        """创建更新器实例"""
        return ParamUpdater(mock_config)

    def test_read_param_file_with_exception(self, updater, tmp_path):
        """测试读取参数文件时发生异常"""
        # 创建一个损坏的 Excel 文件（实际上是文本文件）
        bad_file = tmp_path / "bad.xlsx"
        bad_file.write_text("This is not an Excel file")

        result = updater.read_param_file(bad_file)

        # 应该返回空字典
        assert result == {}

    def test_generate_mappings_file_with_io_error(self, updater, tmp_path):
        """测试生成映射文件时发生 IO 错误"""
        mappings = {'Music': {'音乐1': 'music1'}}

        # 使用一个不存在的目录（不创建）
        bad_dir = tmp_path / "nonexistent" / "subdir"
        output_file = bad_dir / "mappings.py"

        # 应该捕获异常，不抛出
        updater.generate_mappings_file(mappings, output_file)

        # 文件不应该被创建
        assert not output_file.exists()

    def test_collect_validation_data_with_read_error(self, updater, tmp_path):
        """测试收集验证数据时读取失败"""
        # 创建一个损坏的文件
        bad_file = tmp_path / "bad.xlsx"
        bad_file.write_text("Not an Excel file")

        result = updater.collect_validation_data(bad_file)

        # 应该返回空字典
        assert result == {}

    def test_collect_validation_data_with_variant_read_error(self, updater, tmp_path):
        """测试收集验证数据时差分文件读取失败"""
        # 创建正常的参数文件
        param_file = tmp_path / "param.xlsx"
        with pd.ExcelWriter(param_file, engine='openpyxl') as writer:
            df = pd.DataFrame({
                'ExcelParam': ['音乐1'],
                'ScenarioParam': ['music1']
            })
            df.to_excel(writer, sheet_name='Music', index=False)

        # 创建损坏的差分文件
        variant_file = tmp_path / "variant.xlsx"
        variant_file.write_text("Not an Excel file")

        # 应该只返回基础参数，忽略差分文件错误
        result = updater.collect_validation_data(param_file, variant_file)

        assert 'Music' in result
        assert '音乐1' in result['Music']


class TestUpdateMappingsMethod:
    """测试 update_mappings 方法"""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """创建模拟配置"""
        config = Mock(spec=AppConfig)
        config.engine = Mock()
        config.engine.engine_type = "renpy"
        config.paths = Mock()
        config.paths.param_config_dir = tmp_path / "param_config"
        config.paths.input_dir = tmp_path / "input"
        config.paths.param_config_dir.mkdir(parents=True, exist_ok=True)
        config.paths.input_dir.mkdir(parents=True, exist_ok=True)
        return config

    @pytest.fixture
    def updater(self, mock_config):
        """创建更新器实例"""
        return ParamUpdater(mock_config)

    def test_update_mappings_param_file_not_exist(self, updater):
        """测试参数文件不存在时的行为"""
        result = updater.update_mappings()

        # 应该返回 False
        assert result is False

    def test_update_mappings_runs_three_stages_in_order(self, updater):
        """默认完整流程应依次执行基础映射、差分映射和参数表同步。"""
        updater._default_param_file().touch()
        calls = []

        with (
            patch.object(
                updater,
                "generate_param_mappings",
                side_effect=lambda dry_run=False: calls.append("param") or True,
            ),
            patch.object(
                updater,
                "generate_variant_mappings",
                side_effect=lambda dry_run=False: calls.append("variant") or (True, None),
            ),
            patch.object(
                updater,
                "sync_parameter_sheets",
                side_effect=lambda scenario_workbooks=None, dry_run=False: calls.append("sync") or True,
            ),
        ):
            result = updater.update_mappings()

        assert result is True
        assert calls == ["param", "variant", "sync"]

    def test_update_mappings_success_without_variant(self, updater, tmp_path):
        """测试成功更新映射（没有差分文件）"""
        # 创建参数文件
        param_file = updater.config.paths.param_config_dir / "param_data_renpy.xlsx"
        with pd.ExcelWriter(param_file, engine='openpyxl') as writer:
            df = pd.DataFrame({
                'ExcelParam': ['音乐1', '音乐2'],
                'ScenarioParam': ['music1', 'music2']
            })
            df.to_excel(writer, sheet_name='Music', index=False)

        result = updater.update_mappings()

        # 应该成功
        assert result is True

        # 验证映射文件已创建
        mapping_file = updater.config.paths.param_config_dir / "param_mappings.py"
        assert mapping_file.exists()

    def test_update_mappings_success_with_variant(self, updater, tmp_path):
        """测试成功更新映射（有差分文件）"""
        # 创建参数文件
        param_file = updater.config.paths.param_config_dir / "param_data_renpy.xlsx"
        with pd.ExcelWriter(param_file, engine='openpyxl') as writer:
            df = pd.DataFrame({
                'ExcelParam': ['音乐1'],
                'ScenarioParam': ['music1']
            })
            df.to_excel(writer, sheet_name='Music', index=False)

        # 创建差分文件
        variant_file = updater.config.paths.param_config_dir / "variant_data.xlsx"
        with pd.ExcelWriter(variant_file, engine='openpyxl') as writer:
            df = pd.DataFrame({
                'ExcelParam': ['开心', '难过'],
                'ScenarioParam': ['happy', 'sad']
            })
            df.to_excel(writer, sheet_name='角色A', index=False)

        result = updater.update_mappings()

        # 应该成功
        assert result is True

        # 验证两个映射文件都已创建
        mapping_file = updater.config.paths.param_config_dir / "param_mappings.py"
        variant_mapping_file = updater.config.paths.param_config_dir / "variant_mappings.py"
        assert mapping_file.exists()
        assert variant_mapping_file.exists()

    def test_update_mappings_empty_mappings(self, updater, tmp_path):
        """测试参数文件为空时的行为"""
        # 创建一个空的参数文件
        param_file = updater.config.paths.param_config_dir / "param_data_renpy.xlsx"
        with pd.ExcelWriter(param_file, engine='openpyxl') as writer:
            df = pd.DataFrame({'A': []})
            df.to_excel(writer, sheet_name='Sheet1', index=False)

        result = updater.update_mappings()

        # 应该返回 False（没有读取到映射）
        assert result is False

    def test_update_mappings_with_scenario_param_sheets(self, updater, tmp_path):
        """测试更新映射并更新演出表格"""
        from openpyxl import Workbook

        # 创建参数文件
        param_file = updater.config.paths.param_config_dir / "param_data_renpy.xlsx"
        with pd.ExcelWriter(param_file, engine='openpyxl') as writer:
            df = pd.DataFrame({
                'ExcelParam': ['音乐1', '音乐2'],
                'ScenarioParam': ['music1', 'music2']
            })
            df.to_excel(writer, sheet_name='Music', index=False)

        # 创建演出表格文件
        scenario_file = updater.config.paths.input_dir / "scenario.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.title = "参数表"
        ws['A1'] = 'Music'
        wb.save(scenario_file)
        wb.close()

        result = updater.update_mappings()

        # 应该成功
        assert result is True

    def test_update_mappings_mappings_only(self, updater):
        """仅映射模式不应更新任何演出表格。"""
        param_file = updater.config.paths.param_config_dir / "param_data_renpy.xlsx"
        with pd.ExcelWriter(param_file, engine="openpyxl") as writer:
            pd.DataFrame(
                {"ExcelParam": ["音乐1"], "ScenarioParam": ["music1"]}
            ).to_excel(writer, sheet_name="Music", index=False)

        with patch.object(updater, "sync_parameter_sheets") as update_sheets:
            result = updater.update_mappings(update_parameter_sheets=False)

        assert result is True
        assert (updater.config.paths.param_config_dir / "param_mappings.py").exists()
        update_sheets.assert_not_called()

    def test_update_mappings_parameter_sheet_only(self, updater):
        """仅参数表模式不应重新生成映射模块。"""
        param_file = updater.config.paths.param_config_dir / "param_data_renpy.xlsx"
        with pd.ExcelWriter(param_file, engine="openpyxl") as writer:
            pd.DataFrame(
                {"ExcelParam": ["音乐1"], "ScenarioParam": ["music1"]}
            ).to_excel(writer, sheet_name="Music", index=False)

        with (
            patch.object(updater, "generate_param_mappings") as generate_param,
            patch.object(updater, "generate_variant_mappings") as generate_variant,
            patch.object(updater, "sync_parameter_sheets", return_value=True) as update_sheets,
        ):
            result = updater.update_mappings(generate_mapping_files=False)

        assert result is True
        generate_param.assert_not_called()
        generate_variant.assert_not_called()
        update_sheets.assert_called_once()

    def test_update_mappings_dry_run_does_not_write(self, updater):
        """dry-run 应完成读取和预览，但不能写文件或 Excel。"""
        param_file = updater.config.paths.param_config_dir / "param_data_renpy.xlsx"
        with pd.ExcelWriter(param_file, engine="openpyxl") as writer:
            pd.DataFrame(
                {"ExcelParam": ["音乐1"], "ScenarioParam": ["music1"]}
            ).to_excel(writer, sheet_name="Music", index=False)

        with (
            patch.object(updater, "generate_mappings_file") as generate_file,
            patch.object(updater, "update_scenario_param_sheets") as update_sheets,
            patch.object(updater, "preview_scenario_param_sheets", return_value=True) as preview,
        ):
            result = updater.update_mappings(dry_run=True)

        assert result is True
        generate_file.assert_not_called()
        update_sheets.assert_not_called()
        preview.assert_called_once()
        assert not (updater.config.paths.param_config_dir / "param_mappings.py").exists()

    def test_variant_mapping_failure_does_not_fail_full_update(self, updater):
        """差分映射失败应保持原容错策略并继续参数表阶段。"""
        updater._default_param_file().touch()

        with (
            patch.object(updater, "generate_param_mappings", return_value=True),
            patch.object(
                updater,
                "generate_variant_mappings",
                return_value=(False, None),
            ),
            patch.object(updater, "sync_parameter_sheets", return_value=True) as sync,
        ):
            result = updater.update_mappings()

        assert result is True
        sync.assert_called_once_with(scenario_workbooks=None, dry_run=False)


class TestParamUpdaterCli:
    def test_default_arguments_preserve_full_apply(self, monkeypatch):
        """无参数执行必须保持生成映射并同步 input 的旧流程。"""
        monkeypatch.setattr("sys.argv", ["update_param.py"])

        args = parse_args()

        assert args.config == "config.yaml"
        assert args.engine is None
        assert args.workbook is None
        assert args.dry_run is False
        assert args.apply is False
        assert args.mappings_only is False
        assert args.parameter_sheet_only is False

    def test_cli_modes(self, monkeypatch):
        monkeypatch.setattr(
            "sys.argv",
            [
                "update_param.py",
                "--engine",
                "naninovel",
                "--dry-run",
                "--parameter-sheet-only",
                "--workbook",
                "chapter.xlsx",
            ],
        )

        args = parse_args()

        assert args.engine == "naninovel"
        assert args.dry_run is True
        assert args.parameter_sheet_only is True
        assert args.workbook == ["chapter.xlsx"]


class TestMultiProjectParamUpdater:
    @pytest.fixture
    def updater(self, tmp_path):
        config = Mock(spec=AppConfig)
        config.engine = Mock()
        config.engine.engine_type = "renpy"
        config.paths = Mock()
        config.paths.param_config_dir = tmp_path / "param_config"
        config.paths.input_dir = tmp_path / "input"
        config.paths.param_config_dir.mkdir()
        config.paths.input_dir.mkdir()
        config.processing = Mock()
        config.processing.multi_project_mode = True
        config.projects = {
            "chapter_a": "第一篇",
            "chapter_b": "第二篇",
        }
        return ParamUpdater(config)

    @staticmethod
    def _write_param_file(path, values):
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            pd.DataFrame(
                {
                    "ExcelParam": list(values),
                    "ScenarioParam": [value.lower() for value in values],
                }
            ).to_excel(writer, sheet_name="Music", index=False)

    def test_disabled_mode_ignores_project_param_files(self, updater):
        base_file = updater.config.paths.param_config_dir / "param_data_renpy.xlsx"
        project_file = updater.config.paths.param_config_dir / "param_data_chapter_a.xlsx"
        self._write_param_file(base_file, ["BaseMusic"])
        self._write_param_file(project_file, ["ProjectMusic"])
        updater.config.processing.multi_project_mode = False

        assert updater.update_mappings(update_parameter_sheets=False) is True

        namespace = {}
        exec(
            (updater.config.paths.param_config_dir / "param_mappings.py").read_text(
                encoding="utf-8"
            ),
            namespace,
        )
        assert namespace["PARAM_MAPPINGS"]["Music"] == {
            "BaseMusic": "basemusic"
        }

    def test_enabled_mode_merges_project_mapping_files(self, updater):
        param_dir = updater.config.paths.param_config_dir
        self._write_param_file(param_dir / "param_data_renpy.xlsx", ["BaseMusic"])
        self._write_param_file(param_dir / "param_data_chapter_a.xlsx", ["ChapterMusic"])

        assert updater.update_mappings(update_parameter_sheets=False) is True

        namespace = {}
        exec(
            (param_dir / "param_mappings.py").read_text(encoding="utf-8"),
            namespace,
        )
        assert namespace["PARAM_MAPPINGS"]["Music"] == {
            "BaseMusic": "basemusic",
            "ChapterMusic": "chaptermusic",
        }

    def test_workbook_receives_only_matching_project_values(self, updater):
        project_file = updater.config.paths.param_config_dir / "param_data_chapter_a.xlsx"
        self._write_param_file(project_file, ["ChapterMusic"])
        base_data = {"Music": ["BaseMusic"]}
        cache = {}

        matched = updater._validation_data_for_workbook(
            Path("第一篇_演出表.xlsx"), base_data, cache
        )
        unmatched = updater._validation_data_for_workbook(
            Path("公共演出表.xlsx"), base_data, cache
        )

        assert matched == {"Music": ["BaseMusic", "ChapterMusic"]}
        assert unmatched == base_data

    def test_sync_parameter_sheets_applies_project_values_only_to_match(self, updater):
        """参数表同步应只向匹配篇章的工作簿合并篇章参数。"""
        from openpyxl import Workbook, load_workbook

        param_dir = updater.config.paths.param_config_dir
        self._write_param_file(param_dir / "param_data_renpy.xlsx", ["BaseMusic"])
        self._write_param_file(
            param_dir / "param_data_chapter_a.xlsx",
            ["ChapterMusic"],
        )

        matched_file = updater.config.paths.input_dir / "第一篇_演出表.xlsx"
        unmatched_file = updater.config.paths.input_dir / "公共演出表.xlsx"
        for excel_file in (matched_file, unmatched_file):
            workbook = Workbook()
            workbook.active.title = "场景"
            workbook.save(excel_file)
            workbook.close()

        with patch.object(
            updater,
            "get_all_validate_params",
            return_value={"translate_types": ["Music"], "validate_types": []},
        ):
            assert updater.sync_parameter_sheets() is True

        matched_workbook = load_workbook(matched_file)
        unmatched_workbook = load_workbook(unmatched_file)
        matched_values = [
            matched_workbook["参数表"].cell(row=row, column=1).value
            for row in range(2, matched_workbook["参数表"].max_row + 1)
        ]
        unmatched_values = [
            unmatched_workbook["参数表"].cell(row=row, column=1).value
            for row in range(2, unmatched_workbook["参数表"].max_row + 1)
        ]
        matched_workbook.close()
        unmatched_workbook.close()

        assert matched_values == ["BaseMusic", "ChapterMusic"]
        assert unmatched_values == ["BaseMusic"]


class TestEdgeCases:
    """测试边界情况"""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """创建模拟配置"""
        config = Mock(spec=AppConfig)
        config.engine = Mock()
        config.engine.engine_type = "renpy"
        config.paths = Mock()
        config.paths.param_config_dir = tmp_path / "param_config"
        config.paths.input_dir = tmp_path / "input"
        config.paths.param_config_dir.mkdir(parents=True, exist_ok=True)
        config.paths.input_dir.mkdir(parents=True, exist_ok=True)
        return config

    @pytest.fixture
    def updater(self, mock_config):
        """创建更新器实例"""
        return ParamUpdater(mock_config)

    def test_update_scenario_param_sheets_named_range_already_correct(self, updater):
        """参数表和命名区域完全一致时应跳过保存。"""
        from openpyxl import Workbook

        # 创建 Excel 文件
        excel_file = updater.config.paths.input_dir / "test.xlsx"
        wb = Workbook()
        wb.active.title = "场景"

        wb.save(excel_file)
        wb.close()

        validation_data = {'Music': ['音乐1']}

        # 第一次执行创建完整参数表，第二次执行应命中幂等判断。
        assert updater.update_scenario_param_sheets(validation_data) is True
        fixed_timestamp = 1_700_000_000
        os.utime(excel_file, (fixed_timestamp, fixed_timestamp))
        modified_before = excel_file.stat().st_mtime_ns

        result = updater.update_scenario_param_sheets(validation_data)

        assert result is True
        assert excel_file.stat().st_mtime_ns == modified_before

    def test_collect_validation_data_merge_variant(self, updater, tmp_path):
        """测试合并差分参数到 Variant 列"""
        # 创建基础参数文件（包含 Variant）
        param_file = tmp_path / "param.xlsx"
        with pd.ExcelWriter(param_file, engine='openpyxl') as writer:
            df_music = pd.DataFrame({
                'ExcelParam': ['音乐1'],
                'ScenarioParam': ['music1']
            })
            df_music.to_excel(writer, sheet_name='Music', index=False)

            df_variant = pd.DataFrame({
                'ExcelParam': ['差分A', '差分B'],
                'ScenarioParam': ['var_a', 'var_b']
            })
            df_variant.to_excel(writer, sheet_name='Variant', index=False)

        # 创建差分文件
        variant_file = tmp_path / "variant.xlsx"
        with pd.ExcelWriter(variant_file, engine='openpyxl') as writer:
            df = pd.DataFrame({
                'ExcelParam': ['差分C', '差分A'],  # 差分A 重复
                'ScenarioParam': ['var_c', 'var_a']
            })
            df.to_excel(writer, sheet_name='角色A', index=False)

        result = updater.collect_validation_data(param_file, variant_file)

        # 验证 Variant 列合并且去重
        assert 'Variant' in result
        variant_list = result['Variant']
        assert '差分A' in variant_list
        assert '差分B' in variant_list
        assert '差分C' in variant_list
        # 应该去重，所以只有 3 个
        assert len(variant_list) == 3

    def test_generate_mappings_file_variant_variable_name(self, updater, tmp_path):
        """测试生成差分映射文件时使用正确的变量名"""
        mappings = {'角色A': {'开心': 'happy'}}
        output_file = tmp_path / "variant_mappings.py"

        updater.generate_mappings_file(mappings, output_file)

        # 读取文件内容
        content = output_file.read_text(encoding='utf-8')

        # 应该使用 VARIANT_MAPPINGS 变量名
        assert 'VARIANT_MAPPINGS' in content
        assert 'PARAM_MAPPINGS' not in content

    def test_generate_mappings_file_param_variable_name(self, updater, tmp_path):
        """测试生成参数映射文件时使用正确的变量名"""
        mappings = {'Music': {'音乐1': 'music1'}}
        output_file = tmp_path / "param_mappings.py"

        updater.generate_mappings_file(mappings, output_file)

        # 读取文件内容
        content = output_file.read_text(encoding='utf-8')

        # 应该使用 PARAM_MAPPINGS 变量名
        assert 'PARAM_MAPPINGS' in content
        assert 'VARIANT_MAPPINGS' not in content
