import os
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QStandardPaths

from app.common.logger import Logger

app_logger = Logger("Application")  # 初始化主日志记录器并保持引用

from app.view.main_window import FluentMainWindow
from app.common.application import SingletonApplication

# 注册 Qt 资源（模块名不能叫 resource，否则在 Unix 上会被标准库同名内置模块遮蔽）
import app_resources  # noqa: F401

from app.view.crash_handler import CrashHandler
from app.common.const import LOG_PATH

# 启用高DPI缩放
QApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

crash_handler = CrashHandler(LOG_PATH)
crash_handler.setup()


app = SingletonApplication(sys.argv, "MESLogRelay")
app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)
app.setApplicationName("MESLogRelay")

app.setStyleSheet("""
SettingCard[hasError="true"],
PushSettingCard[hasError="true"],
ExpandSettingCard[hasError="true"] {
    border: 2px solid #e74c3c;
    border-radius: 6px;
}
""")

window = FluentMainWindow()
app.aboutToQuit.connect(window.onExit)

app._sendMessage("READY")
sys.exit(app.exec())
