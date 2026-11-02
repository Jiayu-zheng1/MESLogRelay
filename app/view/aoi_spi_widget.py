from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTableWidgetItem, QAbstractItemView
from qfluentwidgets import TableWidget
from dataclasses import dataclass
from typing import Optional

from app.common.enums import UploadStatus
from app.common.database import AOI_SPI
from app.common.signal_bus import signalBus
from app.common.logger import Logger
from app.components.ui_helpers import apply_status_color

logger = Logger("Application")


@dataclass
class RowItem:
    """表格行数据项"""       

    slot_id: str
    time: str
    panel_sn: str
    serial_number: str
    result: str
    sfc_result: str
    upload_time: str
    status: UploadStatus = UploadStatus.PENDING  # 默认状态改为"待上传"

    def get_result_color(self) -> Optional[QColor]:
        """获取结果列的颜色"""
        if self.result in ["PASS", "RPASS"]:
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
            QTableWidgetItem(self.panel_sn),
            QTableWidgetItem(self.serial_number),
            QTableWidgetItem(self.result),
            QTableWidgetItem(self.status.value),
            QTableWidgetItem(self.sfc_result),
            QTableWidgetItem(self.upload_time if self.upload_time else ""),
        ]

        # 为结果列添加颜色 (索引调整为 3)
        result_color = self.get_result_color()
        if result_color:
            items[3].setForeground(result_color)

        # 为状态列添加颜色 (索引调整为 4)
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
        self.setColumnCount(7)
        self.setHorizontalHeaderLabels(
            [
                "slot_id",
                "Panel SN",
                "SN",
                "检测结果",
                "上传状态",
                "SFC Result",
                "上传时间",
            ]
        )

        # 设置列宽
        self.setColumnWidth(0, 50)
        self.setColumnWidth(1, 230)
        self.setColumnWidth(2, 180)
        self.setColumnWidth(3, 90)
        self.setColumnWidth(4, 120)
        self.setColumnWidth(5, 120)
        self.setColumnWidth(6, 120)

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
        slot_id: str,
        time: str,
        panel_sn: str,
        serial_number: str,
        result: str,
        status: UploadStatus,
        sfc_result: str,
        upload_time: str,
    ):
        """向表格添加一行数据

        Args:
            slot_id: Slot ID
            time: 时间
            serial_number: 序列号 (SN)
            result: 测试结果 (PASS/FAIL/SKIP)
            status: 上传状态 (待上传/上传中/已上传/上传失败)
        """
        # 创建行数据项
        row_item = RowItem(
            slot_id=slot_id,
            time=time,
            panel_sn=panel_sn,
            serial_number=serial_number,
            result=result,
            status=status,
            sfc_result=sfc_result,
            upload_time=upload_time,
        )

        self.add_row_item(row_item)

    def add_row_item(self, row_item: RowItem):
        """添加 AoiSpiRowItem 对象到表格，按 slot_id 排序插入

        Args:
            row_item: AoiSpiRowItem 行数据对象
        """
        # 查找插入位置（按 slot_id 升序排列）
        try:
            new_slot_id = int(row_item.slot_id)
        except ValueError:
            # 如果转换失败，插入到末尾
            new_slot_id = float("inf")

        insert_row = 0
        for row in range(self.rowCount()):
            existing_slot_item = self.item(row, 0)  # slot_id 在第 0 列
            if existing_slot_item:
                try:
                    existing_slot_id = int(existing_slot_item.text())
                    if new_slot_id < existing_slot_id:
                        insert_row = row
                        break
                except ValueError:
                    continue
            insert_row = row + 1

        # 在找到的位置插入新行
        self.insertRow(insert_row)

        # 获取表格项列表并添加到表格
        items = row_item.to_items()
        for col_idx, item in enumerate(items):
            self.setItem(insert_row, col_idx, item)

        # 滚动到插入的行
        self.scrollToItem(self.item(insert_row, 0))

    def add_row_from_model(self, model: AOI_SPI):
        """从 AOI_SPI 模型添加一行数据

        Args:
            model: AOI_SPI 数据库模型对象
        """
        data = model.to_status_table_dict()
        self.add_row(
            data["slot_id"],
            data["time"],
            data["panel_sn"],
            data["serial_number"],
            data["result"],
            UploadStatus(data["status"])
            if isinstance(data["status"], str)
            else data["status"],
            data.get("sfc_result", ""),
            data.get("upload_time", ""),
        )

    def update_status(self, model, new_status: UploadStatus, message: str):
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
    """AOI/SPI 详细内容表格"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_table()

    def _setup_table(self):
        """设置表格属性和列"""
        # 设置列数和表头
        self.setColumnCount(11)
        self.setHorizontalHeaderLabels(
            [
                "时间",
                "Slot",
                "Panel SN",
                "SN",
                "检测结果",
                "上传状态",
                "SFC Result",
                "上传时间",
                "Flags",
                "Top/Bot",
                "Fail",
            ]
        )

        # 设置列宽
        self.setColumnWidth(0, 150)  # 时间
        self.setColumnWidth(1, 60)  # Slot
        self.setColumnWidth(2, 180)  # Panel SN
        self.setColumnWidth(3, 180)  # SN
        self.setColumnWidth(4, 80)  # 检测结果
        self.setColumnWidth(5, 100)  # 上传状态
        self.setColumnWidth(6, 100)  # SFC Result
        self.setColumnWidth(7, 150)  # 上传时间
        self.setColumnWidth(9, 80)  # Flags
        self.setColumnWidth(10, 80)  # Top/Bot
        self.setColumnWidth(11, 80)  # Items

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
        """向表格添加一行数据

        Args:
            data: 包含所有列数据的字典，键包括:
                - time: 时间
                - status: 上传状态
                - serial_number: 序列号
                - result: 测试结果 (PASS/FAIL/SKIP)
                - flags: 标志位
                - bot_or_top: Top/Bot
                - items: 项目数量
        """
        row_count = self.rowCount()
        if row_count >= 100:
            self.removeRow(row_count - 1)
        self.insertRow(0)

        # 列顺序：时间、上传状态、SFC Result、上传时间、Slot、序号、结果、Flags、Top/Bot、Items
        columns = [
            "time",
            "slot_id",
            "panel_sn",
            "serial_number",
            "result",
            "status",
            "sfc_result",
            "upload_time",
            "flags",
            "bot_or_top",
            "items",
        ]
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

    def add_row_from_model(self, model: AOI_SPI):
        """从 AOI_SPI 模型添加一行数据

        Args:
            model: AOI_SPI 数据库模型对象
        """
        data = model.to_content_table_dict()
        self.add_row(data)

    def clear(self):
        """清空表格"""
        self.setRowCount(0)
