"""
pytest 配置文件
提供共享的 fixtures 和测试配置
"""
import pytest
import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def project_root_path():
    """返回项目根目录路径"""
    return Path(__file__).parent.parent


@pytest.fixture
def test_data_dir():
    """返回测试数据目录路径"""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def config_file_path(project_root_path):
    """返回配置文件路径"""
    return project_root_path / "config.yaml"


@pytest.fixture
def param_config_dir(project_root_path):
    """返回参数配置目录路径"""
    return project_root_path / "param_config"
