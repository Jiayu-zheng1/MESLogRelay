from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget
from qfluentwidgets import FluentLabelBase, getFont

from app.common.enums import ChipType


class ChipLabel(FluentLabelBase):
    """支持动态颜色与动态状态文本的 Chip 标签"""

    def __init__(self, text: str, type_: str = ChipType.INFO, parent: QWidget = None):
        super().__init__(parent)
        self._base_text = text  # 原始文本
        self._type = type_

        self._type_map = {
            ChipType.INFO: ["#2B85E4", "white", "信息"],
            ChipType.SUCCESS: ["#19BE6B", "white", "成功"],
            ChipType.WARNING: ["#FF9900", "black", "警告"],
            ChipType.DANGER: ["#ED3F14", "white", "错误"],
            ChipType.ONLINE: ["#19BE6B", "white", "在线"],
            ChipType.OFFLINE: ["#C0C4CC", "black", "离线"],
            ChipType.CONN_FAILED: ["#D7581D", "white", "连接失败"],
        }

        self.setAlignment(Qt.AlignCenter)
        self._updateText()
        self.updateStyle()

    def getFont(self):
        return getFont(12, QFont.DemiBold)

    def _updateText(self):
        """根据 base_text + 状态生成最终文本"""
        _, _, t = self._type_map.get(self._type, ["", "", ""])
        if t:
            super().setText(f"{self._base_text} ({t})")
        else:
            super().setText(self._base_text)

    def setText(self, text: str):
        """修改原始文本后自动拼接状态"""
        self._base_text = text
        self._updateText()
        self.updateStyle()

    def setType(self, type_: str):
        """修改状态 + 文本 + 样式"""
        if type_ != self._type:
            self._type = type_
            self._updateText()
            self.updateStyle()

    def updateStyle(self):
        bg, fg, _ = self._type_map.get(self._type, ["#2B85E4", "white", "信息"])

        self.setStyleSheet(f"""
            ChipLabel {{
                background: {bg};         /* 背景颜色 */
                color: {fg};              /* 字体颜色 */
                padding: 4px 12px;        /* 内边距 */
                /* border-radius: 8px; */ /* 圆角 */
            }}
        """)
