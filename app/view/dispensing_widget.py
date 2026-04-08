from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTableWidgetItem, QAbstractItemView
from qfluentwidgets import TableWidget
from dataclasses import dataclass
from typing import Optional

from app.common.enums import UploadStatus
from app.common.database import Dispensing
from app.common.signal_bus import signalBus
from app.common.logger import Logger
from app.components.ui_helpers import apply_status_color

logger = Logger("Application")


@dataclass
class RowItem:
    """表格行数据项"""

    time: str
    serial_number: str
    result: str
    sfc_result: str
    upload_time: str
    status: UploadStatus = UploadStatus.PENDING  # 默认状态改为"待上传"

    def get_result_color(self) -> Optional[QColor]:
        """获取结果列的颜色"""
        if self.result == "PASS":
            return QColor(16, 124, 16)  # 绿色
        elif self.result == "FAIL":
            return QColor(196, 43, 28)  # 红色
        elif self.result in ["SKIP", "UNTEST"]:
            return QColor(128, 128, 128)  # 灰色
        return None

    def get_status_color(self) -> Optional[QColor]:
        """获取状态列的颜色"""
        if self.status == UploadStatus.UPLOADED:
            return QColor(16, 124, 16)  # 绿色
        elif self.status in [UploadStatus.UPLOAD_FAILED, UploadStatus.UOP]:
            return QColor(196, 43, 28)  # 红色
        elif self.status in [
            UploadStatus.PENDING,
            UploadStatus.UPLOADING,
            UploadStatus.SKIP,
            UploadStatus.UNTEST,
        ]:
            return QColor(157, 93, 0)  # 橙色
        return None

    def to_items(self) -> list[QTableWidgetItem]:
        """转换为表格项列表"""
        items = [
            QTableWidgetItem(self.slot_id),
            QTableWidgetItem(self.time),
            QTableWidgetItem(self.serial_number),
            QTableWidgetItem(self.result),
            QTableWidgetItem(self.status.value),
        ]

        # 为结果列添加颜色
        result_color = self.get_result_color()
        if result_color:
            items[3].setForeground(result_color)

        # 为状态列添加颜色
        status_color = self.get_status_color()
        if status_color:
            items[4].setForeground(status_color)

        return items


class StatusTable(TableWidget):
    """AOI/SPI 状态监控表格"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_table()
        self._setup_signals()

    def _setup_table(self):
        """设置表格属性和列"""
        # 设置列数和表头
        self.setColumnCount(6)
        self.setHorizontalHeaderLabels(
            ["记录时间", "SN", "检查结果", "上传状态", "SFC Result", "上传时间"]
        )

        # 设置列宽
        self.setColumnWidth(0, 120)
        self.setColumnWidth(1, 180)
        self.setColumnWidth(2, 90)
        self.setColumnWidth(3, 120)
        self.setColumnWidth(4, 120)
        self.setColumnWidth(5, 120)

        # 表格样式设置
        self.setBorderVisible(True)
        self.setBorderRadius(8)
        self.setSortingEnabled(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)  # 隐藏行号

    def _setup_signals(self):
        """设置信号槽连接"""
        signalBus.uploadStatusSig.connect(self.update_status)
        signalBus.clearStatusTableSig.connect(self.clear)

    def add_row(
        self,
        time: str,
        serial_number: str,
        result: str,
        status: UploadStatus,
        sfc_result: str,
        upload_time: str,
    ):
        """向表格添加一行数据

        Args:
            time: 时间
            serial_number: 序列号 (SN)
            result: 测试结果 (PASS/FAIL/SKIP)
            status: 上传状态 (待上传/上传中/已上传/上传失败)
        """
        # 创建行数据项
        row_item = RowItem(
            time=time,
            serial_number=serial_number,
            result=result,
            status=status,
            sfc_result=sfc_result,
            upload_time=upload_time,
        )

        self.add_row_item(row_item)

    def add_row_item(self, row_item: RowItem):
        """添加 RowItem 对象到表格

        Args:
            row_item: RowItem 行数据对象
        """
        row_count = self.rowCount()
        self.insertRow(row_count)

        # 获取表格项列表并添加到表格
        items = row_item.to_items()
        for col_idx, item in enumerate(items):
            self.setItem(row_count, col_idx, item)

        # 滚动到最新行
        self.scrollToBottom()

    def add_row_from_model(self, model: Dispensing):
        """从模型添加一行数据

        Args:
            model: Dispensing 数据库模型对象
        """
        self.add_row(
            model.record_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            model.serial_number,
            model.result,
            UploadStatus(model.upload_status)
            if isinstance(model.upload_status, str)
            else model.upload_status,
            model.sfc_result,
            model.upload_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            if model.upload_time
            else "",
        )

    def update_status(self, model: Dispensing, new_status: UploadStatus, message: str):
        """根据序列号更新状态

        Args:
            serial_number: 序列号
            new_status: 新状态
            update_db: 是否同步更新数据库
        """
        logger.info(
            f"Update Status: {model.serial_number}, {new_status.value}, {message}"
        )

        for row in range(self.rowCount()):
            serial_item = self.item(row, 2)  # SN在第2列
            if serial_item and serial_item.text() == model.serial_number:
                self.update_status_by_row(row, new_status, model)
                break

    def update_status_by_row(self, row: int, new_status: UploadStatus, model=None):
        """根据行号更新状态

        Args:
            row: 行号
            new_status: 新状态
            update_db: 是否同步更新数据库
        """
        if 0 <= row < self.rowCount():
            status_item = QTableWidgetItem(new_status.value)
            apply_status_color(status_item, new_status)
            self.setItem(row, 4, status_item)  # 状态在第4列

            if model.sfc_result:
                sfc_result_item = QTableWidgetItem(model.sfc_result)
                apply_status_color(sfc_result_item, new_status)
                self.setItem(row, 5, sfc_result_item)  # SFC Result在第5列

            if new_status == UploadStatus.UPLOADED:
                _upload_time = QTableWidgetItem(
                    model.upload_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                )
                self.setItem(row, 6, _upload_time)  # 上传时间在第6列

            # 同步更新数据库
            model.upload_status = new_status.value
            model.save()

    def get_pending_rows(self) -> list[int]:
        """获取所有待上传的行号列表

        Returns:
            待上传的行号列表
        """
        pending_rows = []
        for row in range(self.rowCount()):
            status_item = self.item(row, 4)  # 状态在第4列
            if status_item and status_item.text() == UploadStatus.PENDING.value:
                pending_rows.append(row)
        return pending_rows

    def clear(self):
        """清空表格"""
        self.setRowCount(0)


class ContentTable(TableWidget):
    """详细内容表格"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_table()

    def _setup_table(self):
        """设置表格属性和列"""
        # 设置列数和表头
        self.setColumnCount(16)
        self.setHorizontalHeaderLabels(
            [
                "时间",
                "上传状态",
                "SFC Result",
                "上传时间",
                "序号",
                "检查结果",
                "总设定重量",
                "IPQC阀门重量",
                "阀门单点重量",
                "称重频率",
                "冲洗频率",
                "清洁频率",
                "喷嘴温度",
                "底部加热器温度",
                "加热时间",
                "冲洗/清洁时间",
                "点胶路径",
            ]
        )

        # 设置列宽
        self.setColumnWidth(0, 120)
        self.setColumnWidth(1, 80)
        self.setColumnWidth(2, 120)
        self.setColumnWidth(3, 120)
        self.setColumnWidth(4, 180)
        self.setColumnWidth(5, 90)

        # 表格样式设置
        self.setBorderVisible(True)
        self.setBorderRadius(8)
        self.setSortingEnabled(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.verticalHeader().setVisible(False)  # 隐藏行号

    def add_row(self, data: dict):
        """向表格添加一行数据"""

        row_count = self.rowCount()
        if row_count >= 100:
            self.removeRow(row_count - 1)
        self.insertRow(0)

        columns = data.keys()
        for col_idx, key in enumerate(columns):
            value = data.get(key, "")
            if value is None:
                value = ""

            # 处理状态字段
            if key == "status":
                if isinstance(value, UploadStatus):
                    value = value.value
                elif value == "":
                    value = UploadStatus.PENDING.value

            item = QTableWidgetItem(str(value))

            # 结果列添加颜色
            if key == "result":
                if value == "PASS":
                    item.setForeground(QColor(16, 124, 16))
                elif value == "FAIL":
                    item.setForeground(QColor(196, 43, 28))
                elif value in ["SKIP", "UNTEST"]:
                    item.setForeground(QColor(128, 128, 128))

            # 状态列添加颜色
            elif key in ["status", "sfc_result"]:
                # 将字符串转换为枚举类型
                try:
                    if key == "sfc_result":
                        value = data.get("status")

                    status_enum = UploadStatus(value)
                    apply_status_color(item, status_enum)
                except ValueError:
                    pass  # 如果值不匹配，忽略颜色设置

            self.setItem(0, col_idx, item)

        # 滚动到最新行
        # self.scrollToBottom()

    def add_row_from_model(self, model: Dispensing):
        """从模型添加一行数据"""

        data = model.to_tabele_dict()
        self.add_row(data)

    def clear(self):
        """清空表格"""
        self.setRowCount(0)
