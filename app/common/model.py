from dataclasses import dataclass, field
from app.common.enums import Result


@dataclass
class BaseData:
    product_name: str = None  # 機種名
    line_name: str = None  # 產線名稱
    station_code: str = None  # 工站名稱
    serial_number: str = None
    panel_sn: str = None  # 序號
    test_time: str = None  # 測試時間
    test_time_dt: str = None  # 測試時間的日期時間格式
    sfc_result: Result = Result.PASS  # 測試結果


@dataclass
class SPI(BaseData):
    slot_id: int = None  # 槽位ID
    panel_sn: str = None  # 面板序號
    test_time: str = None  # 测试时间
    flags: str = None  # SKIP/UNTEST/PASS/FAIL
    bot_or_top: str = None  # 機種面別
    items: int = 0  # 檢測項目數量
    failed_components: str = None  # 不良元件位置（如 J0100）
    failed_cause: str = None  # 不良原因（如 Volume_Upper, OffsetX）
    failed_pid: str = None  # 不良PAD ID（如 A1

    def to_dict(self):
        return {
            "product_name": self.product_name,
            "line_name": self.line_name,
            "station_code": self.station_code,
            "serial_number": self.serial_number,
            "slot_id": self.slot_id,
            "panel_sn": self.panel_sn,
            "test_time": self.test_time,
            "flags": self.flags,
            "bot_or_top": self.bot_or_top,
            "items": self.items,
            "failed_components": self.failed_components,
            "failed_cause": self.failed_cause,
            "failed_pid": self.failed_pid,
            "sfc_result": self.sfc_result.value,
        }


@dataclass
class ReflowOven(BaseData):
    sfc_result: Result = Result.PASS  # 测试结果
    version: str = None  # 版本信息
    carrier_No: str = None  # 载具编号
    InTime: str = None  # 进板时间
    OutTime: str = None  # 出板时间
    O2: str = None  # 氧气浓度
    ExternalTemp: str = None  # 外部温度

    Motor_UpHeat: str = None
    Motor_DnHeat: str = None
    Motor_UpWeld: str = None
    Motor_DnWeld: str = None
    Motor_Cooling: str = None

    SetConveyorSpeed: str = None  # 设定输送带速度（链速）
    ConveyorSpeed: str = None  # 实际输送带速度（链速）

    SetTopZoneT01: str = None  # Set TOP 分区1 温度
    SetTopZoneT02: str = None  # Set TOP 分区2 温度
    SetTopZoneT03: str = None  # Set TOP 分区3 温度
    SetTopZoneT04: str = None  # Set TOP 分区4 温度
    SetTopZoneT05: str = None  # Set TOP 分区5 温度
    SetTopZoneT06: str = None  # Set TOP 分区6 温度
    SetTopZoneT07: str = None  # Set TOP 分区7 温度
    SetTopZoneT08: str = None  # Set TOP 分区8 温度
    SetTopZoneT09: str = None  # Set TOP 分区9 温度
    SetTopZoneT10: str = None  # Set TOP 分区10 温度
    SetTopZoneT11: str = None  # Set TOP 分区11 温度
    SetTopZoneT12: str = None  # Set TOP 分区12 温度
    SetTopZoneT13: str = None  # Set TOP 分区13 温度

    SetBottomZoneT01: str = None  # Set BOTTOM 分区1 温度
    SetBottomZoneT02: str = None  # Set BOTTOM 分区2 温度
    SetBottomZoneT03: str = None  # Set BOTTOM 分区3 温度
    SetBottomZoneT04: str = None  # Set BOTTOM 分区4 温度
    SetBottomZoneT05: str = None  # Set BOTTOM 分区5 温度
    SetBottomZoneT06: str = None  # Set BOTTOM 分区6 温度
    SetBottomZoneT07: str = None  # Set BOTTOM 分区7 温度
    SetBottomZoneT08: str = None  # Set BOTTOM 分区8 温度
    SetBottomZoneT09: str = None  # Set BOTTOM 分区9 温度
    SetBottomZoneT10: str = None  # Set BOTTOM 分区10 温度
    SetBottomZoneT11: str = None  # Set BOTTOM 分区11 温度
    SetBottomZoneT12: str = None  # Set BOTTOM 分区12 温度
    SetBottomZoneT13: str = None  # Set BOTTOM 分区13 温度

    TopZoneT01: str = None  # Actual TOP 分区1 温度
    TopZoneT02: str = None  # Actual TOP 分区2 温度
    TopZoneT03: str = None  # Actual TOP 分区3 温度
    TopZoneT04: str = None  # Actual TOP 分区4 温度
    TopZoneT05: str = None  # Actual TOP 分区5 温度
    TopZoneT06: str = None  # Actual TOP 分区6 温度
    TopZoneT07: str = None  # Actual TOP 分区7 温度
    TopZoneT08: str = None  # Actual TOP 分区8 温度
    TopZoneT09: str = None  # Actual TOP 分区9 温度
    TopZoneT10: str = None  # Actual TOP 分区10 温度
    TopZoneT11: str = None  # Actual TOP 分区11 温度
    TopZoneT12: str = None  # Actual TOP 分区12 温度
    TopZoneT13: str = None  # Actual TOP 分区13 温度

    BottomZoneT01: str = None  # Actual BOTTOM 分区1 温度
    BottomZoneT02: str = None  # Actual BOTTOM 分区2 温度
    BottomZoneT03: str = None  # Actual BOTTOM 分区3 温度
    BottomZoneT04: str = None  # Actual BOTTOM 分区4 温度
    BottomZoneT05: str = None  # Actual BOTTOM 分区5 温度
    BottomZoneT06: str = None  # Actual BOTTOM 分区6 温度
    BottomZoneT07: str = None  # Actual BOTTOM 分区7 温度
    BottomZoneT08: str = None  # Actual BOTTOM 分区8 温度
    BottomZoneT09: str = None  # Actual BOTTOM 分区9 温度
    BottomZoneT10: str = None  # Actual BOTTOM 分区10 温度
    BottomZoneT11: str = None  # Actual BOTTOM 分区11 温度
    BottomZoneT12: str = None  # Actual BOTTOM 分区12 温度
    BottomZoneT13: str = None  # Actual BOTTOM 分区13 温度

    MaxRiseSlope_upper: str = None  # Max Rise Slope 上限
    MaxRiseSlope_lower: str = None  # Max Rise Slope 下限
    MaxFallSlope_upper: str = None  # Max Fall Slope 上限
    MaxFallSlope_lower: str = None  # Max Fall Slope 下限
    Peak_Temp_upper: str = None  # Peak Temp 上限
    Peak_Temp_lower: str = None  # Peak Temp 下限

    T2_RiseSlope: str = None  # T2 Rise Slope
    T2_FallSlope: str = None  # T2 Fall Slope
    T2_Peak_Temp: str = None  # T2 Peak Temp
    T3_RiseSlope: str = None  # T3 Rise Slope
    T3_FallSlope: str = None  # T3 Fall Slope
    T3_Peak_Temp: str = None  # T3 Peak Temp
    T4_RiseSlope: str = None  # T4 Rise Slope
    T4_FallSlope: str = None  # T4 Fall Slope
    T4_Peak_Temp: str = None  # T4 Peak Temp
    T5_RiseSlope: str = None  # T5 Rise Slope
    T5_FallSlope: str = None  # T5 Fall Slope
    T5_Peak_Temp: str = None  # T5 Peak Temp
    T6_RiseSlope: str = None  # T6 Rise Slope
    T6_FallSlope: str = None  # T6 Fall Slope
    T6_Peak_Temp: str = None  # T6 Peak Temp
    T7_RiseSlope: str = None  # T7 Rise Slope
    T7_FallSlope: str = None  # T7 Fall Slope
    T7_Peak_Temp: str = None  # T7 Peak Temp
    T8_RiseSlope: str = None  # T8 Rise Slope
    T8_FallSlope: str = None  # T8 Fall Slope
    T8_Peak_Temp: str = None  # T8 Peak Temp
    T9_RiseSlope: str = None  # T9 Rise Slope
    T9_FallSlope: str = None  # T9 Fall Slope
    T9_Peak_Temp: str = None  # T9 Peak Temp
    T10_RiseSlope: str = None  # T10 Rise Slope
    T10_FallSlope: str = None  # T10 Fall Slope
    T10_Peak_Temp: str = None  # T10 Peak Temp
