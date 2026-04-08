# coding:utf-8
import sys
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QSystemTrayIcon
from qfluentwidgets import Action, SystemTrayMenu, MenuAnimationType

from app.common.signal_bus import signalBus


class SystemTrayIconMenu(SystemTrayMenu):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.click_type = None

    def exec(self, pos, ani=True, aniType=MenuAnimationType.DROP_DOWN):
        # 只有右键点击时才显示菜单
        if self.click_type == 'right':
            self.click_type = None
            return super().exec(pos, ani, aniType)
        self.click_type = None


class SystemTrayIcon(QSystemTrayIcon):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setIcon(parent.windowIcon())

        self.menu = SystemTrayIconMenu(parent=parent) if sys.platform == "darwin" else SystemTrayMenu(parent=parent)
        self.menu.addActions([
            Action(self.tr('Show Panel'), triggered=lambda: signalBus.appMessageSig.emit("show")),
            Action(self.tr('Exit'), triggered=QApplication.instance().exit),
        ])
        if sys.platform == "darwin":
            self.setContextMenu(None)  # macOS下禁止Qt自动弹出菜单
        else:
            self.setContextMenu(self.menu)
        self.activated.connect(self._onActivated)

    def _onActivated(self, reason):
        """处理托盘点击"""
        if sys.platform == "darwin":
            if reason == QSystemTrayIcon.ActivationReason.Trigger:
                # 左键点击显示主界面
                signalBus.appMessageSig.emit("show")

            elif reason == QSystemTrayIcon.ActivationReason.Context:
                # 右键点击才显示菜单
                self.menu.click_type = 'right'
                self.menu.exec(QCursor.pos())
        else:
            # Windows/Linux
            if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
                signalBus.appMessageSig.emit("show")