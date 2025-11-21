"""
GUI 应用启动脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from gui.main import main

if __name__ == "__main__":
    main()
