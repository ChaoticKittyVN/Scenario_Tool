"""
日志管理模块
提供统一的日志记录功能
"""
import logging
import sys
from pathlib import Path
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""

    # ANSI 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'

    def format(self, record):
        # 获取日志级别对应的颜色
        levelname = record.levelname
        color = self.COLORS.get(levelname, self.RESET)

        # 给日志级别添加颜色和加粗
        record.levelname = f"{self.BOLD}{color}{levelname}{self.RESET}"

        # 格式化消息
        return super().format(record)


class ScenarioToolLogger:
    """统一的日志管理器（单例模式）"""

    _instance: Optional[logging.Logger] = None

    @classmethod
    def get_logger(cls, name: str = "scenario_tool") -> logging.Logger:
        """
        获取日志实例（单例模式）

        Args:
            name: 日志器名称

        Returns:
            logging.Logger: 日志器实例
        """
        if cls._instance is None:
            cls._instance = cls._setup_logger(name)
        return cls._instance

    @classmethod
    def _setup_logger(cls, name: str) -> logging.Logger:
        """
        配置日志器

        Args:
            name: 日志器名称

        Returns:
            logging.Logger: 配置好的日志器
        """
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        # 避免重复添加处理器
        if logger.handlers:
            return logger

        # 控制台处理器（彩色输出）
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = ColoredFormatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)

        # 文件处理器（使用轮转，最大 10MB，保留 5 个备份）
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_dir / "scenario_tool.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger

    @classmethod
    def reset(cls):
        """重置日志器（主要用于测试）"""
        if cls._instance:
            for handler in cls._instance.handlers[:]:
                handler.close()
                cls._instance.removeHandler(handler)
            cls._instance = None


# 便捷函数
def get_logger(name: str = "scenario_tool") -> logging.Logger:
    """获取日志器的便捷函数"""
    return ScenarioToolLogger.get_logger(name)
