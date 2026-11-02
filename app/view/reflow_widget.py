from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTableWidgetItem, QAbstractItemView
from qfluentwidgets import TableWidget
from dataclasses import dataclass
from typing import Optional

from app.common.enums import UploadStatus
from app.common.database import ReflowOven
from app.common.signal_bus import signalBus
from app.common.logger import Logger
from app.components.ui_helpers import apply_status_color

logger = Logger("Application")


@dataclass
class RowItem:
    """表格行数据项"""

    slot_id: str
    carrier_No: str
    panel_sn: str
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
        """转换为表格项列表

        表头顺序: slot_id, 载具码, Panel SN, 检测结果, 上传状态, SFC Result, 上传时间
        """
        items = [
            QTableWidgetItem(str(self.slot_id)),  # 列0: slot_id
            QTableWidgetItem(self.carrier_No if self.carrier_No else ""),  # 列1: 载具码
            QTableWidgetItem(self.panel_sn if self.panel_sn else ""),  # 列2: Panel SN
            QTableWidgetItem(self.result),  # 列3: 检测结果
            QTableWidgetItem(self.status.value),  # 列4: 上传状态
            QTableWidgetItem(self.sfc_result),  # 列5: SFC Result
            QTableWidgetItem(
                self.upload_time if self.upload_time else ""
            ),  # 列6: 上传时间
        ]

        # 为结果列添加颜色 (列3)
        result_color = self.get_result_color()
        if result_color:
            items[3].setForeground(result_color)

        # 为状态列添加颜色 (列4)
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
                "载具码",
                "Panel SN",
                "检测结果",
                "上传状态",
                "SFC Result",
                "上传时间",
            ]
        )

        # 设置列宽
        self.setColumnWidth(0, 50)
        self.setColumnWidth(1, 150)
        self.setColumnWidth(2, 220)
        self.setColumnWidth(3, 100)
        self.setColumnWidth(4, 100)
        self.setColumnWidth(5, 100)
        self.setColumnWidth(6, 200)

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
        carrier_No: str,
        panel_sn: str,
        result: str,
        status: UploadStatus,
        sfc_result: str,
        upload_time: str,
    ):
        """向表格添加一行数据

        Args:
            slot_id: Slot ID
            carrier_No: 载具码
            panel_sn: Panel SN
            result: 测试结果 (PASS/FAIL/SKIP)
            status: 上传状态 (待上传/上传中/已上传/上传失败)
        """
        # 创建行数据项
        row_item = RowItem(
            slot_id=slot_id,
            carrier_No=carrier_No,
            panel_sn=panel_sn,
            result=result,
            status=status,
            sfc_result=sfc_result,
            upload_time=upload_time,
        )

        self.add_row_item(row_item)

    def add_row_item(self, row_item: RowItem):
        """添加 AoiSpiRowItem 对象到表格

        Args:
            row_item: AoiSpiRowItem 行数据对象
        """
        # 在第一行插入新数据
        self.insertRow(0)

        # 获取表格项列表并添加到表格
        items = row_item.to_items()
        for col_idx, item in enumerate(items):
            self.setItem(0, col_idx, item)

        # 滚动到最新行（顶部）
        self.scrollToTop()

    def add_row_from_model(self, model: ReflowOven):
        """从 ReflowOven 模型添加一行数据

        Args:
            model: ReflowOven 数据库模型对象
        """
        data = model.to_status_table_dict()
        self.add_row(
            data["slot_id"],
            data.get("carrier_No", ""),
            data.get("panel_sn", ""),
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
            model: 数据模型
            new_status: 新状态
            message: 消息
        """
        logger.info(
            f"Update Status: {model.serial_number}, {new_status.value}, {message}"
        )

        # 通过 slot_id 和 panel_sn 来匹配行（更准确）
        for row in range(self.rowCount()):
            slot_item = self.item(row, 0)  # slot_id在第1列
            panel_item = self.item(row, 2)  # Panel SN在第3列

            # 匹配 slot_id 和 panel_sn
            if (
                slot_item
                and panel_item
                and str(slot_item.text()) == str(model.Slot_id)
                and panel_item.text() == model.panel_sn
            ):
                self.update_status_by_row(row, new_status, model)
                break

    def update_status_by_row(self, row: int, new_status: UploadStatus, model=None):
        """根据行号更新状态

        表头顺序: slot_id, Panel SN, SN, 检查结果, 状态, SFC Result, 上传时间

        Args:
            row: 行号
            new_status: 新状态
            update_db: 是否同步更新数据库
        """
        if 0 <= row < self.rowCount():
            # 列4: 上传状态
            status_item = QTableWidgetItem(new_status.value)
            apply_status_color(status_item, new_status)
            self.setItem(row, 4, status_item)

            # 列5: SFC Result
            if model.sfc_result:
                sfc_result_item = QTableWidgetItem(model.sfc_result)
                apply_status_color(sfc_result_item, new_status)
                self.setItem(row, 5, sfc_result_item)

            # 列6: 上传时间
            if new_status == UploadStatus.UPLOADED:
                _upload_time = QTableWidgetItem(
                    model.upload_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                )
                self.setItem(row, 6, _upload_time)

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
            status_item = self.item(row, 4)  # 状态在第5列(索引4)
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
        headers = [
            "slot_id",
            "载具码",
            "Panle SN",
            "Single SN",
            "检查结果",
            "状态",
            "SFC Result",
            "上传时间",
            "InTime",
            "OutTime",
            "O2",
            "ExternalTemp",
            "Motor_UpHeat",
            "Motor_DnHeat",
            "Motor_UpWeld",
            "Motor_DnWeld",
            "Motor_Cooling",
            "SetConveyorSpeed",
            "ConveyorSpeed",
            "MaxRiseSlope_upper",
            "MaxRiseSlope_lower",
            "MaxFallSlope_upper",
            "MaxFallSlope_lower",
            "Peak_Temp_upper",
            "Peak_Temp_lower",
            "T2_RiseSlope",
            "T2_FallSlope",
            "T2_Peak_Temp",
            "T3_RiseSlope",
            "T3_FallSlope",
            "T3_Peak_Temp",
            "T4_RiseSlope",
            "T4_FallSlope",
            "T4_Peak_Temp",
            "T5_RiseSlope",
            "T5_FallSlope",
            "T5_Peak_Temp",
            "T6_RiseSlope",
            "T6_FallSlope",
            "T6_Peak_Temp",
            "T7_RiseSlope",
            "T7_FallSlope",
            "T7_Peak_Temp",
            "T8_RiseSlope",
            "T8_FallSlope",
            "T8_Peak_Temp",
            "T9_RiseSlope",
            "T9_FallSlope",
            "T9_Peak_Temp",
            "T10_RiseSlope",
            "T10_FallSlope",
            "T10_Peak_Temp",
        ]

        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)

        # 前8列按业务可读性固定宽度，其余参数列统一宽度
        fixed_widths = [50, 150, 220, 200, 100, 100, 120, 200]
        for idx, width in enumerate(fixed_widths):
            self.setColumnWidth(idx, width)

        for idx in range(len(fixed_widths), len(headers)):
            self.setColumnWidth(idx, 130)

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

        表头顺序: slot_id, Panel SN, SN, 检查结果, 上传状态, SFC Result, 上传时间

        Args:
            data: 包含所有列数据的字典
        """
        row_count = self.rowCount()
        if row_count >= 100:
            self.removeRow(row_count - 1)
        self.insertRow(0)

        # 按照表头顺序设置列
        columns = [
            "slot_id",
            "carrier_No",
            "panel_sn",
            "serial_number",
            "result",
            "status",
            "sfc_result",
            "upload_time",
            "InTime",
            "OutTime",
            "O2",
            "ExternalTemp",
            "Motor_UpHeat",
            "Motor_DnHeat",
            "Motor_UpWeld",
            "Motor_DnWeld",
            "Motor_Cooling",
            "SetConveyorSpeed",
            "ConveyorSpeed",
            "MaxRiseSlope_upper",
            "MaxRiseSlope_lower",
            "MaxFallSlope_upper",
            "MaxFallSlope_lower",
            "Peak_Temp_upper",
            "Peak_Temp_lower",
            "T2_RiseSlope",
            "T2_FallSlope",
            "T2_Peak_Temp",
            "T3_RiseSlope",
            "T3_FallSlope",
            "T3_Peak_Temp",
            "T4_RiseSlope",
            "T4_FallSlope",
            "T4_Peak_Temp",
            "T5_RiseSlope",
            "T5_FallSlope",
            "T5_Peak_Temp",
            "T6_RiseSlope",
            "T6_FallSlope",
            "T6_Peak_Temp",
            "T7_RiseSlope",
            "T7_FallSlope",
            "T7_Peak_Temp",
            "T8_RiseSlope",
            "T8_FallSlope",
            "T8_Peak_Temp",
            "T9_RiseSlope",
            "T9_FallSlope",
            "T9_Peak_Temp",
            "T10_RiseSlope",
            "T10_FallSlope",
            "T10_Peak_Temp",
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

            # 结果列添加颜色 (列3)
            if key == "result":
                if value == "PASS":
                    item.setForeground(QColor(16, 124, 16))
                elif value == "FAIL":
                    item.setForeground(QColor(196, 43, 28))
                elif value in ["SKIP", "UNTEST"]:
                    item.setForeground(QColor(128, 128, 128))

            # 状态列添加颜色 (列4和列5)
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

    def add_row_from_model(self, model: ReflowOven):
        """从 ReflowOven 模型添加一行数据

        Args:
            model: ReflowOven 数据库模型对象
        """
        data = model.to_content_table_dict()
        self.add_row(data)

    def clear(self):
        """清空表格"""
        self.setRowCount(0)
