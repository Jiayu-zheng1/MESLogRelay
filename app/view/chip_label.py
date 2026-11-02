# -*- coding: utf-8 -*-
from PySide6.QtCore import Qt, QSize, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QFontMetrics
from PySide6.QtWidgets import QWidget
from qfluentwidgets import isDarkTheme

from app.common.enums import ChipType


class ChipLabel(QWidget):
    """
    支持状态圆点与括号状态文本的指示器标签
    展示格式：● 名字 (状态)
    - 在线时：绿色
    - 连接失败：红色
    - 警告：黄色
    - 关闭UOP时：灰色
    """

    def __init__(self, text: str, type_: str = ChipType.ONLINE, parent: QWidget = None):
        super().__init__(parent)
        self._base_text = text
        self._type = type_

        # 状态配置表：[状态文本, 圆点主色, 亮色模式文字色, 暗色模式文字色]
        self._status_meta = {
            ChipType.ONLINE: ("在线", "#10B981", "#047857", "#34D399"),
            ChipType.SUCCESS: ("在线", "#10B981", "#047857", "#34D399"),
            ChipType.CONN_FAILED: ("连接失败", "#EF4444", "#DC2626", "#F87171"),
            ChipType.DANGER: ("连接失败", "#EF4444", "#DC2626", "#F87171"),
            ChipType.WARNING: ("警告", "#F59E0B", "#D97706", "#FBBF24"),
            ChipType.OFFLINE: ("关闭UOP", "#9CA3AF", "#4B5563", "#D1D5DB"),
            ChipType.CLOSE_UOP: ("关闭UOP", "#9CA3AF", "#4B5563", "#D1D5DB"),
            ChipType.INFO: ("信息", "#3B82F6", "#2563EB", "#60A5FA"),
        }

        font = QFont()
        font.setPointSize(10)
        font.setWeight(QFont.DemiBold)
        self.setFont(font)
        self.setFixedHeight(26)

    def _get_current_meta(self):
        """获取当前类型的展示元数据"""
        return self._status_meta.get(
            self._type,
            (str(self._type), "#9CA3AF", "#4B5563", "#D1D5DB")
        )

    def getDisplayText(self) -> str:
        """获取名字加括号状态文本"""
        status_text, _, _, _ = self._get_current_meta()
        if status_text:
            return f"{self._base_text} ({status_text})"
        return self._base_text

    def setText(self, text: str):
        """设置名称"""
        if self._base_text != text:
            self._base_text = text
            self.updateGeometry()
            self.update()

    def setType(self, type_: str):
        """更新状态类型"""
        if self._type != type_:
            self._type = type_
            self.updateGeometry()
            self.update()

    def sizeHint(self) -> QSize:
        fm = QFontMetrics(self.font())
        text_width = fm.horizontalAdvance(self.getDisplayText())
        # 左内边距(10) + 光晕圆点占宽(12) + 间距(6) + 文本宽度 + 右内边距(10)
        total_width = 10 + 12 + 6 + text_width + 10
        return QSize(total_width, 26)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)

        status_text, dot_hex, fg_light_hex, fg_dark_hex = self._get_current_meta()
        dot_color = QColor(dot_hex)
        try:
            dark = isDarkTheme()
        except Exception:
            dark = False

        # 背景色与边框色（带半透明度）
        if dark:
            bg_color = QColor(dot_color.red(), dot_color.green(), dot_color.blue(), 35)
            border_color = QColor(dot_color.red(), dot_color.green(), dot_color.blue(), 100)
            fg_color = QColor(fg_dark_hex)
        else:
            bg_color = QColor(dot_color.red(), dot_color.green(), dot_color.blue(), 25)
            border_color = QColor(dot_color.red(), dot_color.green(), dot_color.blue(), 80)
            fg_color = QColor(fg_light_hex)

        # 1. 绘制胶囊外框背景
        rect = QRectF(0.5, 0.5, self.width() - 1.0, self.height() - 1.0)
        radius = rect.height() / 2.0
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(rect, radius, radius)

        # 2. 绘制圆点（带柔和外光晕）
        center_y = self.height() / 2.0
        center_x = 10.0 + 4.0
        dot_center = QPointF(center_x, center_y)

        # 光晕层
        glow_color = QColor(dot_color.red(), dot_color.green(), dot_color.blue(), 55)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(glow_color))
        painter.drawEllipse(dot_center, 5.5, 5.5)

        # 核心实心圆点
        painter.setBrush(QBrush(dot_color))
        painter.drawEllipse(dot_center, 3.5, 3.5)

        # 3. 绘制文字：名字 (状态)
        text_x = center_x + 8.0
        text_rect = QRectF(text_x, 0, self.width() - text_x - 6.0, self.height())
        painter.setPen(fg_color)
        painter.setFont(self.font())
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, self.getDisplayText())
