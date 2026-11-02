from qfluentwidgets import (
    InfoBadge,InfoLevel, InfoBadgePosition,
    InfoBadgeManager
)
from app.common.enums import UploadStatus
from PySide6.QtWidgets import QTableWidgetItem
from PySide6.QtGui import QColor

def apply_status_color(item: QTableWidgetItem, status: UploadStatus):
    """为状态项应用颜色
    
    Args:
        item: 表格项
        status: 上传状态
    """
    if status == UploadStatus.UPLOADED:
        item.setForeground(QColor(16, 124, 16))  # 绿色
    elif status in [UploadStatus.UPLOAD_FAILED, UploadStatus.UOP]:
        item.setForeground(QColor(196, 43, 28))  # 红色
    elif status in [UploadStatus.PENDING, UploadStatus.UPLOADING, UploadStatus.CHECK_UOP]:
        item.setForeground(QColor(157, 93, 0))   # 橙色
    elif status in [UploadStatus.SKIP, UploadStatus.UNTEST]:
        item.setForeground(QColor(128, 128, 128))  # 灰色


def setInfoBadge(target, text: str, level=InfoLevel.INFOAMTION, position=InfoBadgePosition.TOP_RIGHT):

    # 初始化徽章
    if not hasattr(target, "_info_badge"):
        target._info_badge = InfoBadge(
            text=text,
            parent=target.parent(),    # ⚠ 必须是按钮的父控件
            level=level
        )
        target._info_badge.manager = InfoBadgeManager.make(position, target, target._info_badge)
        target._info_badge.move(target._info_badge.manager.position())
    target._info_badge.setText(text)
    target._info_badge.adjustSize()

    target._info_badge.setLevel(level)
    target._info_badge.show()

def clearInfoBadge(self):
    if hasattr(self, "_info_badge"):
        self._info_badge.hide()