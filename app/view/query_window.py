# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from PySide6.QtCore import Qt, QDate, QAbstractTableModel
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QAbstractItemView,
    QFileDialog,
)
from qfluentwidgets import (
    CardWidget,
    LineEdit,
    PrimaryPushButton,
    PushButton,
    TableView,
    BodyLabel,
    ZhDatePicker,
    ComboBox,
    MessageBox,
)

from app.common.database import AOI_SPI, ReflowOven
from app.common.enums import UploadStatus
from app.common.logger import Logger
from app.common.config import cfg
import csv

logger = Logger("QueryWindow")

REFLOW_EXTRA_33_HEADERS = [
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


def _build_reflow_row(record):
    row = [
        record.record_time.strftime("%Y-%m-%d %H:%M:%S") if record.record_time else "",
        record.product_name or "",
        record.line_name or "",
        record.station_code or "",
        str(record.Slot_id) if hasattr(record, "Slot_id") else "",
        record.carrier_No or "",
        record.panel_sn or "",
        record.serial_number or "",
        record.result or "",
        record.upload_status or "",
        record.sfc_result or "",
        record.upload_time.strftime("%Y-%m-%d %H:%M:%S") if record.upload_time else "",
        record.single_ct or "",
        record.InTime or "",
        record.OutTime or "",
        record.O2 or "",
        record.ExternalTemp or "",
        record.Motor_UpHeat or "",
        record.Motor_DnHeat or "",
        record.Motor_UpWeld or "",
        record.Motor_DnWeld or "",
        record.Motor_Cooling or "",
        record.SetConveyorSpeed or "",
        record.ConveyorSpeed or "",
        record.SetTopZoneT01 or "",
        record.SetTopZoneT02 or "",
        record.SetTopZoneT03 or "",
        record.SetTopZoneT04 or "",
        record.SetTopZoneT05 or "",
        record.SetTopZoneT06 or "",
        record.SetTopZoneT07 or "",
        record.SetTopZoneT08 or "",
        record.SetTopZoneT09 or "",
        record.SetTopZoneT10 or "",
        record.SetTopZoneT11 or "",
        record.SetTopZoneT12 or "",
        record.SetTopZoneT13 or "",
        record.SetBottomZoneT01 or "",
        record.SetBottomZoneT02 or "",
        record.SetBottomZoneT03 or "",
        record.SetBottomZoneT04 or "",
        record.SetBottomZoneT05 or "",
        record.SetBottomZoneT06 or "",
        record.SetBottomZoneT07 or "",
        record.SetBottomZoneT08 or "",
        record.SetBottomZoneT09 or "",
        record.SetBottomZoneT10 or "",
        record.SetBottomZoneT11 or "",
        record.SetBottomZoneT12 or "",
        record.SetBottomZoneT13 or "",
        record.TopZoneT01 or "",
        record.TopZoneT02 or "",
        record.TopZoneT03 or "",
        record.TopZoneT04 or "",
        record.TopZoneT05 or "",
        record.TopZoneT06 or "",
        record.TopZoneT07 or "",
        record.TopZoneT08 or "",
        record.TopZoneT09 or "",
        record.TopZoneT10 or "",
        record.TopZoneT11 or "",
        record.TopZoneT12 or "",
        record.TopZoneT13 or "",
        record.BottomZoneT01 or "",
        record.BottomZoneT02 or "",
        record.BottomZoneT03 or "",
        record.BottomZoneT04 or "",
        record.BottomZoneT05 or "",
        record.BottomZoneT06 or "",
        record.BottomZoneT07 or "",
        record.BottomZoneT08 or "",
        record.BottomZoneT09 or "",
        record.BottomZoneT10 or "",
        record.BottomZoneT11 or "",
        record.BottomZoneT12 or "",
        record.BottomZoneT13 or "",
        record.MaxRiseSlope_upper or "",
        record.MaxRiseSlope_lower or "",
        record.MaxFallSlope_upper or "",
        record.MaxFallSlope_lower or "",
        record.Peak_Temp_upper or "",
        record.Peak_Temp_lower or "",
        record.T2_RiseSlope or "",
        record.T2_FallSlope or "",
        record.T2_Peak_Temp or "",
        record.T3_RiseSlope or "",
        record.T3_FallSlope or "",
        record.T3_Peak_Temp or "",
        record.T4_RiseSlope or "",
        record.T4_FallSlope or "",
        record.T4_Peak_Temp or "",
        record.T5_RiseSlope or "",
        record.T5_FallSlope or "",
        record.T5_Peak_Temp or "",
        record.T6_RiseSlope or "",
        record.T6_FallSlope or "",
        record.T6_Peak_Temp or "",
        record.T7_RiseSlope or "",
        record.T7_FallSlope or "",
        record.T7_Peak_Temp or "",
        record.T8_RiseSlope or "",
        record.T8_FallSlope or "",
        record.T8_Peak_Temp or "",
        record.T9_RiseSlope or "",
        record.T9_FallSlope or "",
        record.T9_Peak_Temp or "",
        record.T10_RiseSlope or "",
        record.T10_FallSlope or "",
        record.T10_Peak_Temp or "",
    ]
    return row


class QueryResultModel(QAbstractTableModel):
    """查询结果表格模型"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []
        self._headers = []

    def set_headers(self, headers):
        """设置表头"""
        self._headers = headers

    def set_data(self, data):
        """设置数据"""
        self.beginResetModel()
        self._data = data
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._headers) if self._headers else 0

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None

        row = index.row()
        col = index.column()

        if 0 <= row < len(self._data) and 0 <= col < len(self._headers):
            return self._data[row][col]

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Horizontal:
            if 0 <= section < len(self._headers):
                return self._headers[section]
        return None

    def clear(self):
        """清空数据"""
        self.beginResetModel()
        self._data = []
        self.endResetModel()


class QueryWindow(QWidget):
    """数据查询窗口"""

    def __init__(self, parent):
        super().__init__()
        self.setWindowTitle("数据查询")
        self.setWindowIcon(parent.windowIcon())
        self.resize(1200, 700)
        self.setWindowModality(Qt.WindowModal)

        # print(1 / 0)  # 测试崩溃处理

        self._create_widgets()
        self._setup_layouts()
        self._connect_signals()

    def _create_widgets(self):
        """创建控件"""
        # 查询条件卡片
        self.query_card = CardWidget(self)

        # 查询条件控件
        self.sn_input = LineEdit(self)
        self.sn_input.setPlaceholderText("SN: 输入完整或部分序列号")
        self.sn_input.setClearButtonEnabled(True)

        self.panel_sn_input = LineEdit(self)
        self.panel_sn_input.setPlaceholderText("Panel SN: 输入连板序列号")
        self.panel_sn_input.setClearButtonEnabled(True)

        self.status_combo = ComboBox(self)
        self.status_combo.addItems(["全部状态"] + [s.value for s in UploadStatus])
        self.status_combo.setPlaceholderText("上传状态")

        self.result_combo = ComboBox(self)
        self.result_combo.addItems(["全部结果", "PASS", "FAIL", "SKIP", "UNTEST"])
        self.result_combo.setPlaceholderText("检测结果")

        self.start_date_picker = ZhDatePicker(self)
        start_date = datetime.now() - timedelta(days=7)
        self.start_date_picker.setDate(
            QDate(start_date.year, start_date.month, start_date.day)
        )

        self.end_date_picker = ZhDatePicker(self)
        end_date = datetime.now()
        self.end_date_picker.setDate(QDate(end_date.year, end_date.month, end_date.day))

        # 查询按钮
        self.search_button = PrimaryPushButton("查询", self)
        self.clear_button = PushButton("清空条件", self)
        self.export_button = PushButton("导出结果", self)
        self.export_button.setEnabled(False)

        # 结果显示卡片
        self.result_card = CardWidget(self)
        self.result_label_text = BodyLabel("查询结果: 0 条记录")

        # 结果表格 - 使用自定义模型
        self.result_model = QueryResultModel(self)
        self.result_table = TableView(self)
        self.result_table.setModel(self.result_model)
        self.result_table.setBorderVisible(True)
        self.result_table.setBorderRadius(8)
        self.result_table.setSortingEnabled(False)
        self.result_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.result_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.result_table.setAlternatingRowColors(True)
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.verticalHeader().setVisible(True)

        # 存储当前查询结果（用于导出）
        self.current_results = []

    def _setup_layouts(self):
        """设置布局"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # 查询条件卡片布局
        query_layout = QVBoxLayout(self.query_card)
        query_layout.setContentsMargins(10, 10, 10, 10)
        query_layout.setSpacing(8)

        # 第一行：序列号和连板序列号
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(10)
        row1_layout.addWidget(self.panel_sn_input, 1)
        row1_layout.addWidget(self.sn_input, 1)
        query_layout.addLayout(row1_layout)

        # 第二行：状态、结果、日期、按钮
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(10)
        row2_layout.addWidget(self.status_combo)
        row2_layout.addWidget(self.result_combo)
        row2_layout.addWidget(self.start_date_picker)
        row2_layout.addWidget(BodyLabel("-"))
        row2_layout.addWidget(self.end_date_picker)
        row2_layout.addStretch()
        row2_layout.addWidget(self.clear_button)
        row2_layout.addWidget(self.search_button)
        row2_layout.addWidget(self.export_button)
        query_layout.addLayout(row2_layout)

        main_layout.addWidget(self.query_card)

        # 结果卡片布局
        result_layout = QVBoxLayout(self.result_card)
        result_layout.setContentsMargins(10, 10, 10, 10)
        result_layout.setSpacing(8)

        result_layout.addWidget(self.result_label_text)
        result_layout.addWidget(self.result_table)

        main_layout.addWidget(self.result_card)

    def _connect_signals(self):
        """连接信号"""
        self.search_button.clicked.connect(self._on_search)
        self.clear_button.clicked.connect(self._on_clear)
        self.export_button.clicked.connect(self._on_export)

    def _on_search(self):
        """执行查询"""
        try:
            # 获取当前工站代码
            station_code = cfg.get(cfg.station_code)
            logger.info(f"开始查询数据，工站代码: {station_code}")

            # 根据工站代码选择对应的数据模型
            if int(station_code) in (103, 106, 112, 116):  # AOI/SPI站别
                model_class = AOI_SPI
                headers = [
                    "记录时间",
                    "产品名称",
                    "线别",
                    "工站",
                    "Slot ID",
                    "Panel SN",
                    "SN",
                    "结果",
                    "上传状态",
                    "SFC结果",
                    "上传时间",
                    "班别",
                    "用户",
                    "工单号",
                    "日期",
                    "时间",
                    "标志",
                    "面别",
                    "检测项数",
                ]
            elif int(station_code) in (109, 122):  # 炉温站别
                model_class = ReflowOven
                headers = [
                    "记录时间",
                    "产品名称",
                    "线别",
                    "工站",
                    "Slot ID",
                    "载具码",
                    "Panel SN",
                    "SN",
                    "结果",
                    "上传状态",
                    "SFC结果",
                    "上传时间",
                    "单板CT",
                    "进板时间",
                    "出板时间",
                    "O2",
                    "外部温度",
                    "Motor_UpHeat",
                    "Motor_DnHeat",
                    "Motor_UpWeld",
                    "Motor_DnWeld",
                    "Motor_Cooling",
                    "设定链速",
                    "实际链速",
                    "SetTopT01",
                    "SetTopT02",
                    "SetTopT03",
                    "SetTopT04",
                    "SetTopT05",
                    "SetTopT06",
                    "SetTopT07",
                    "SetTopT08",
                    "SetTopT09",
                    "SetTopT10",
                    "SetTopT11",
                    "SetTopT12",
                    "SetTopT13",
                    "SetBottomT01",
                    "SetBottomT02",
                    "SetBottomT03",
                    "SetBottomT04",
                    "SetBottomT05",
                    "SetBottomT06",
                    "SetBottomT07",
                    "SetBottomT08",
                    "SetBottomT09",
                    "SetBottomT10",
                    "SetBottomT11",
                    "SetBottomT12",
                    "SetBottomT13",
                    "TopT01",
                    "TopT02",
                    "TopT03",
                    "TopT04",
                    "TopT05",
                    "TopT06",
                    "TopT07",
                    "TopT08",
                    "TopT09",
                    "TopT10",
                    "TopT11",
                    "TopT12",
                    "TopT13",
                    "BottomT01",
                    "BottomT02",
                    "BottomT03",
                    "BottomT04",
                    "BottomT05",
                    "BottomT06",
                    "BottomT07",
                    "BottomT08",
                    "BottomT09",
                    "BottomT10",
                    "BottomT11",
                    "BottomT12",
                    "BottomT13",
                ] + REFLOW_EXTRA_33_HEADERS
            else:
                MessageBox("错误", f"不支持的工站代码: {station_code}", self).exec_()
                return

            # 构建查询条件
            query = model_class.select()

            # SN 条件
            sn = self.sn_input.text().strip()
            if sn:
                query = query.where(model_class.serial_number.contains(sn))

            # Panel SN 条件
            panel_sn = self.panel_sn_input.text().strip()
            if panel_sn:
                query = query.where(model_class.panel_sn.contains(panel_sn))

            # 状态条件
            status = self.status_combo.currentText()
            if status != "全部状态":
                query = query.where(model_class.upload_status == status)

            # 结果条件
            result = self.result_combo.currentText()
            if result != "全部结果":
                query = query.where(model_class.result == result)

            # 日期范围条件
            start_date = self.start_date_picker.getDate()
            end_date = self.end_date_picker.getDate()

            # 转换为 datetime
            start_datetime = datetime(
                start_date.year(), start_date.month(), start_date.day()
            )
            end_datetime = datetime(
                end_date.year(), end_date.month(), end_date.day(), 23, 59, 59
            )

            query = query.where(
                model_class.record_time >= start_datetime,
                model_class.record_time <= end_datetime,
            )

            # 排序
            query = query.order_by(model_class.record_time.desc())

            # 限制最大结果数
            # query = query.limit()

            # 执行查询
            results = list(query)

            # 转换为表格数据
            table_data = []
            for record in results:
                if int(station_code) in (103, 106, 112, 116):  # AOI/SPI
                    row = [
                        record.record_time.strftime("%Y-%m-%d %H:%M:%S")
                        if record.record_time
                        else "",
                        record.product_name or "",
                        record.line_name or "",
                        record.station_code or "",
                        str(record.slot_id) if hasattr(record, "slot_id") else "",
                        record.panel_sn or "",
                        record.serial_number or "",
                        record.result or "",
                        record.upload_status or "",
                        record.sfc_result or "",
                        record.upload_time.strftime("%Y-%m-%d %H:%M:%S")
                        if record.upload_time
                        else "",
                        record.class_type or "",
                        record.user_name or "",
                        record.work_order_number or "",
                        record.date or "",
                        record.time or "",
                        record.flags or "",
                        record.bot_or_top or "",
                        str(record.items) if hasattr(record, "items") else "",
                    ]
                else:  # 炉温
                    row = _build_reflow_row(record)
                table_data.append(row)

            # 显示结果
            self._display_results(table_data, headers, results)

            logger.info(f"查询完成: 找到 {len(results)} 条记录")

        except Exception as e:
            logger.error(f"查询失败: {e}", exc_info=True)
            MessageBox("查询错误", f"查询失败: {str(e)}", self).exec_()

    def _display_results(self, table_data, headers, raw_results):
        """显示查询结果"""
        self.result_model.set_headers(headers)
        self.result_model.set_data(table_data)
        self.result_label_text.setText(f"查询结果: {len(table_data)} 条记录")

        # 保存原始结果用于导出
        self.current_results = raw_results

        # 启用导出按钮
        self.export_button.setEnabled(len(table_data) > 0)

    def _on_clear(self):
        """清空查询条件"""
        self.sn_input.clear()
        self.panel_sn_input.clear()
        self.status_combo.setCurrentIndex(0)
        self.result_combo.setCurrentIndex(0)
        start_date = datetime.now() - timedelta(days=7)
        self.start_date_picker.setDate(
            QDate(start_date.year, start_date.month, start_date.day)
        )
        end_date = datetime.now()
        self.end_date_picker.setDate(QDate(end_date.year, end_date.month, end_date.day))

        # 清空结果
        self.result_model.clear()
        self.result_label_text.setText("查询结果: 0 条记录")
        self.export_button.setEnabled(False)
        self.current_results = []

        logger.info("查询条件已清空")

    def _on_export(self):
        """导出查询结果到CSV"""
        try:
            if not self.current_results:
                MessageBox("提示", "没有可导出的数据", self).exec_()
                return

            # 选择保存路径
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出数据",
                f"query_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "CSV Files (*.csv)",
            )

            if not file_path:
                return

            # 获取工站代码
            station_code = cfg.get(cfg.station_code)

            # 导出到 CSV
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)

                # 根据工站写入表头（与显示表格相同）
                if int(station_code) in (103, 106, 112, 116):  # AOI/SPI
                    headers = [
                        "记录时间",
                        "产品名称",
                        "线别",
                        "工站",
                        "Slot ID",
                        "Panel SN",
                        "SN",
                        "结果",
                        "上传状态",
                        "SFC结果",
                        "上传时间",
                        "班别",
                        "用户",
                        "工单号",
                        "日期",
                        "时间",
                        "标志",
                        "面别",
                        "检测项数",
                    ]
                else:  # 炉温
                    headers = [
                        "记录时间",
                        "产品名称",
                        "线别",
                        "工站",
                        "Slot ID",
                        "载具码",
                        "Panel SN",
                        "SN",
                        "结果",
                        "上传状态",
                        "SFC结果",
                        "上传时间",
                        "单板CT",
                        "进板时间",
                        "出板时间",
                        "O2",
                        "外部温度",
                        "Motor_UpHeat",
                        "Motor_DnHeat",
                        "Motor_UpWeld",
                        "Motor_DnWeld",
                        "Motor_Cooling",
                        "设定链速",
                        "实际链速",
                        "SetTopT01",
                        "SetTopT02",
                        "SetTopT03",
                        "SetTopT04",
                        "SetTopT05",
                        "SetTopT06",
                        "SetTopT07",
                        "SetTopT08",
                        "SetTopT09",
                        "SetTopT10",
                        "SetTopT11",
                        "SetTopT12",
                        "SetTopT13",
                        "SetBottomT01",
                        "SetBottomT02",
                        "SetBottomT03",
                        "SetBottomT04",
                        "SetBottomT05",
                        "SetBottomT06",
                        "SetBottomT07",
                        "SetBottomT08",
                        "SetBottomT09",
                        "SetBottomT10",
                        "SetBottomT11",
                        "SetBottomT12",
                        "SetBottomT13",
                        "TopT01",
                        "TopT02",
                        "TopT03",
                        "TopT04",
                        "TopT05",
                        "TopT06",
                        "TopT07",
                        "TopT08",
                        "TopT09",
                        "TopT10",
                        "TopT11",
                        "TopT12",
                        "TopT13",
                        "BottomT01",
                        "BottomT02",
                        "BottomT03",
                        "BottomT04",
                        "BottomT05",
                        "BottomT06",
                        "BottomT07",
                        "BottomT08",
                        "BottomT09",
                        "BottomT10",
                        "BottomT11",
                        "BottomT12",
                        "BottomT13",
                    ] + REFLOW_EXTRA_33_HEADERS

                writer.writerow(headers)

                # 写入数据
                for record in self.current_results:
                    if int(station_code) in (103, 106, 112, 116):  # AOI/SPI
                        row = [
                            record.record_time.strftime("%Y-%m-%d %H:%M:%S")
                            if record.record_time
                            else "",
                            record.product_name or "",
                            record.line_name or "",
                            record.station_code or "",
                            str(record.slot_id) if hasattr(record, "slot_id") else "",
                            record.panel_sn or "",
                            record.serial_number or "",
                            record.result or "",
                            record.upload_status or "",
                            record.sfc_result or "",
                            record.upload_time.strftime("%Y-%m-%d %H:%M:%S")
                            if record.upload_time
                            else "",
                            record.class_type or "",
                            record.user_name or "",
                            record.work_order_number or "",
                            record.date or "",
                            record.time or "",
                            record.flags or "",
                            record.bot_or_top or "",
                            str(record.items) if hasattr(record, "items") else "",
                        ]
                    else:  # 炉温
                        row = _build_reflow_row(record)

                    writer.writerow(row)

            logger.info(f"导出 {len(self.current_results)} 条记录到 {file_path}")
            MessageBox(
                "成功", f"成功导出 {len(self.current_results)} 条记录", self
            ).exec_()

        except Exception as e:
            logger.error(f"导出失败: {e}", exc_info=True)
            MessageBox("导出错误", f"导出失败: {str(e)}", self).exec_()
