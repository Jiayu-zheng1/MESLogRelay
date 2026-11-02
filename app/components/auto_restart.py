# coding:utf-8
import os
import subprocess
import sys
from datetime import datetime, timedelta

from PySide6.QtCore import QObject, QTimer, Signal, QProcess
from PySide6.QtWidgets import QApplication

from app.common.logger import Logger


class AutoRestartManager(QObject):
    """自动重启管理器"""

    restartRequested = Signal()  # 请求重启信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = Logger("AutoRestartManager")
        self.enabled = False
        self.restart_time = "00:00"  # HH:MM format
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self._checkRestartTime)
        self.check_interval = 60000  # 每60秒检查一次
        self.last_check_date = None

    def start(self, restart_time: str = "00:00"):
        """启动自动重启管理器

        Args:
            restart_time: 重启时间，格式为 HH:MM (24小时制)
        """
        if not self._validateTime(restart_time):
            self.logger.error(f"Invalid restart time format: {restart_time}")
            return False

        self.enabled = True
        self.restart_time = restart_time
        self.last_check_date = None
        self.check_timer.start(self.check_interval)
        self.logger.info(
            f"Auto restart manager started, will restart at {restart_time}"
        )
        return True

    def stop(self):
        """停止自动重启管理器"""
        if self.enabled:
            self.enabled = False
            self.check_timer.stop()
            self.last_check_date = None
            self.logger.info("Auto restart manager stopped")

    def setRestartTime(self, restart_time: str):
        """设置重启时间

        Args:
            restart_time: 重启时间，格式为 HH:MM (24小时制)
        """
        if not self._validateTime(restart_time):
            self.logger.error(f"Invalid restart time format: {restart_time}")
            return False

        self.restart_time = restart_time
        self.last_check_date = None  # 重置检查日期
        self.logger.info(f"Restart time updated to {restart_time}")
        return True

    def _validateTime(self, time_str: str) -> bool:
        """验证时间格式是否正确

        Args:
            time_str: 时间字符串，格式为 HH:MM

        Returns:
            bool: 时间格式是否有效
        """
        try:
            parts = time_str.split(":")
            if len(parts) != 2:
                return False
            hour = int(parts[0])
            minute = int(parts[1])
            return 0 <= hour <= 23 and 0 <= minute <= 59
        except (ValueError, AttributeError):
            return False

    def _checkRestartTime(self):
        """检查是否到达重启时间"""
        if not self.enabled:
            return

        now = datetime.now()
        current_date = now.date()

        # 如果今天已经检查过了，跳过
        if self.last_check_date == current_date:
            return

        # 解析目标重启时间
        try:
            hour, minute = map(int, self.restart_time.split(":"))
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # 检查当前时间是否在目标时间的1分钟范围内
            time_diff = abs((now - target_time).total_seconds())

            if time_diff <= 60:  # 1分钟容差
                self.logger.info(f"Restart time reached: {self.restart_time}")
                self.last_check_date = current_date  # 标记今天已经执行过
                self.restartRequested.emit()
                self.restartApplication()

        except Exception as e:
            self.logger.error(f"Error checking restart time: {e}")

    def restartApplication(self):
        """重启应用程序"""
        try:
            self.logger.info("Restarting application...")

            exe = sys.executable
            args = sys.argv

            if "--silent" not in args:
                args.append("--silent")

            # ok, pid = QProcess.startDetached(exe, args, os.getcwd())
            # if not ok:
            subprocess.Popen(
                [exe] + args,
                cwd=os.getcwd(),
                env={**os.environ, "PYINSTALLER_RESET_ENVIRONMENT": "1"},
            )

            # 稍微延迟退出旧应用
            # QTimer.singleShot(1000, self._exitApplication)
            self._exitApplication()

        except Exception as e:
            self.logger.error(f"Failed to restart application: {e}")

    def _exitApplication(self):
        """退出应用程序"""
        app = QApplication.instance()
        if app:
            app.quit()
        sys.exit(0)  # 确保旧进程退出

    def getNextRestartTime(self) -> str:
        """获取下次重启的时间

        Returns:
            str: 下次重启的日期时间字符串
        """
        if not self.enabled:
            return "未启用"

        try:
            now = datetime.now()
            hour, minute = map(int, self.restart_time.split(":"))
            target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # 如果目标时间已过，则计算明天的时间
            if target_time <= now or self.last_check_date == now.date():
                target_time += timedelta(days=1)

            return target_time.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            self.logger.error(f"Error calculating next restart time: {e}")
            return "计算错误"
