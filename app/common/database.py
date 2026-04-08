from datetime import datetime
from peewee import *
from app.common.const import DB_PATH
from app.common.logger import logger

db = SqliteDatabase(DB_PATH)


class BaseModel(Model):
    record_time = DateTimeField(default=datetime.now)
    product_name = CharField(null=True)
    line_name = CharField(null=True)
    station_code = CharField(null=True)
    serial_number = CharField(null=True)
    panel_sn = CharField(null=True)
    result = CharField()
    upload_status = CharField(default="待上传")  # 上传状态字段
    upload_time = DateTimeField(null=True)  # 上传时间字段
    sfc_result = CharField(null=True)  # SFC返回结果字段

    class Meta:
        database = db


class Dispensing(BaseModel):
    test_time = DateTimeField()
    TotalSettingWeight = CharField(null=True)  # 总设定重量
    IPQC_WeightValve = CharField(null=True)  # IPQC阀门重量（单板重量/图形重量)
    SingleDotValve = CharField(null=True)  # 阀门单点重量
    WeightingFrequency = CharField(default="预设1")  # 称重频率
    PurgeFrequency = CharField(default="预设1")  # 冲洗频率
    CleanFrequency = CharField(default="预设1")  # 清洁频率
    NozzleTemp = CharField(null=True)  # 喷嘴温度
    BottomHeaterTemp = CharField(null=True)  # 底部加热器温度
    HeatingTime = CharField(default="循环")  # 加热时间
    PurgeCleanTime = CharField(default="300")  # 冲洗/清洁时间
    DispensingPath = CharField(default="无")  # 点胶路径

    def to_tabele_dict(self) -> dict:
        """转换为表格所需的字典格式"""
        return {
            "time": self.record_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "status": self.upload_status,
            "sfc_result": self.sfc_result,
            "upload_time": self.upload_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            if self.upload_time
            else None,
            "serial_number": self.serial_number,
            "result": self.result,
            "TotalSettingWeight": self.TotalSettingWeight,
            "IPQC_WeightValve": self.IPQC_WeightValve,
            "SingleDotValve": self.SingleDotValve,
            "NozzleTemp": self.NozzleTemp,
            "BottomHeaterTemp": self.BottomHeaterTemp,
            "DispensingPath": self.DispensingPath,
        }


class AOI_SPI(BaseModel):
    slot_id = IntegerField()  # Slot ID
    serial_number = CharField(null=True)  # 单板SN（从SFC获取）
    test_time = CharField()  # 测试时间
    flags = CharField(null=True)  # 可选字段,CSV格式不包含
    bot_or_top = CharField(null=True)  # 机种面别
    items = CharField(null=True)  # 检测项目数量
    failed_components = CharField(null=True)  # 不良元件位置（如 J0100）
    failed_cause = CharField(null=True)  # 不良原因（如 Volume_Upper, OffsetX）
    failed_pid = CharField(null=True)  # 不良PAD ID（如 A1, A2）
    Volume = CharField(null=True)  # 点胶体积
    OffsetX = CharField(null=True)  # X偏移
    OffsetY = CharField(null=True)  # Y偏移

    def to_status_table_dict(self) -> dict:
        """转换为状态表格所需的字典格式"""
        return {
            "slot_id": str(self.slot_id),
            "time": self.record_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            if self.record_time
            else None,
            "panel_sn": self.panel_sn,
            "serial_number": self.serial_number,
            "result": self.result,
            "status": self.upload_status,
            "upload_time": self.upload_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            if self.upload_time
            else None,
            "sfc_result": self.sfc_result,
            "failed_components": self.failed_components,
            "failed_cause": self.failed_cause,
            "failed_pid": self.failed_pid,
        }

    def to_content_table_dict(self) -> dict:
        """转换为详细内容表格所需的字典格式"""
        return {
            "time": self.record_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            if self.record_time
            else None,
            "status": self.upload_status,
            "upload_time": self.upload_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            if self.upload_time
            else None,
            "sfc_result": self.sfc_result,
            "slot_id": str(self.slot_id),
            "panel_sn": self.panel_sn,
            "serial_number": self.serial_number,
            "result": self.result,
            "flags": self.flags,
            "bot_or_top": self.bot_or_top,
            "items": str(self.items),
        }

    @property
    def raw_data(self) -> str:
        Date = datetime.now().strftime("%Y-%m-%d")
        Time = datetime.now().strftime("%H:%M:%S")
        """生成raw格式数据（列表形式，用于写入文件）"""
        _raw_data = [
            self.station_code or "NULL",  # 站点代码
            self.slot_id if self.slot_id else "NULL",  # Slot ID
            self.status_code if self.serial_number else 3,  # 状态码
            Date if Date else "NULL",  # 日期
            Time if Time else "NULL",  # 时间
            self.serial_number or "NULL",  # SN
            "NULL",
            "NULL",
            "NULL",
            "NULL",
            "NULL",
            self.serial_number or "NULL",  # 单板SN（从SFC获取）
            self.product_name or "NULL",  # 机种名称
            self.panel_sn or "NULL",  # 连板SN
            self.line_name or "NULL",  # 线别名称
            self.test_time or "NULL",  # 测试时间
            self.result or "NULL",  # 测试结果
            self.bot_or_top or "NULL",  # 机种面别
            self.failed_components or "NULL",  # 不良元件位置（如 J0100）
            self.failed_cause or "NULL",  # 不良原因（如 Volume_Upper, OffsetX）
            self.failed_pid or "NULL",  # 不良PAD ID（如
        ]

        return _raw_data

    @property
    def status_code(self) -> int:
        """根据 result 返回对应的状态码"""
        mapping = {"PASS": 1, "FAIL": 0, "UNTEST": 3, "SKIP": 3, "RPASS": 1}
        return mapping.get(self.result.upper(), 3)  # 默认返回 3 (UNTEST)

    @property
    def convert_date(self):
        if self.date.isdigit() and len(self.date) == 8:
            return datetime.strptime(self.date, "%Y%m%d").strftime("%Y/%m/%d")
        return self.date

    @property
    def convert_time(self):
        if self.time.isdigit() and len(self.time) == 6:
            return datetime.strptime(self.time, "%H%M%S").strftime("%H:%M:%S")
        return self.time


class ReflowOven(BaseModel):
    Slot_id = IntegerField(null=True)  # Slot ID
    single_ct = CharField(null=True)  # 单板C/T (单站C/T)

    # 新增字段
    version = CharField(null=True)  # 版本信息
    carrier_No = CharField(null=True)  # 载具编号

    InTime = CharField(null=True)  # 进板时间
    OutTime = CharField(null=True)  # 出板时间
    O2 = CharField(null=True)  # 氧气浓度
    ExternalTemp = CharField(null=True)  # 外部温度

    Motor_UpHeat = CharField(null=True)
    Motor_DnHeat = CharField(null=True)
    Motor_UpWeld = CharField(null=True)
    Motor_DnWeld = CharField(null=True)
    Motor_Cooling = CharField(null=True)

    SetMotorSpeed = CharField(null=True)  # 设定马达速度
    MotorSpeed = CharField(null=True)  # 实际马达速度
    SetConveyorSpeed = CharField(null=True)  # 设定输送带速度
    ConveyorSpeed = CharField(null=True)  # 实际输送带速度

    SetTopZoneT01 = CharField(null=True)  # Set TOP 分区1 温度
    SetTopZoneT02 = CharField(null=True)  # Set TOP 分区2 温度
    SetTopZoneT03 = CharField(null=True)  # Set TOP 分区3 温度
    SetTopZoneT04 = CharField(null=True)  # Set TOP 分区4 温度
    SetTopZoneT05 = CharField(null=True)  # Set TOP 分区5 温度
    SetTopZoneT06 = CharField(null=True)  # Set TOP 分区6 温度
    SetTopZoneT07 = CharField(null=True)  # Set TOP 分区7 温度
    SetTopZoneT08 = CharField(null=True)  # Set TOP 分区8 温度
    SetTopZoneT09 = CharField(null=True)  # Set TOP 分区9 温度
    SetTopZoneT10 = CharField(null=True)  # Set TOP 分区10 温度
    SetTopZoneT11 = CharField(null=True)  # Set TOP 分区11 温度
    SetTopZoneT12 = CharField(null=True)  # Set TOP 分区12 温度
    SetTopZoneT13 = CharField(null=True)  # Set TOP 分区13 温度
    SetBottomZoneT01 = CharField(null=True)  # Set BOTTOM 分区1 温度
    SetBottomZoneT02 = CharField(null=True)  # Set BOTTOM 分区2 温度
    SetBottomZoneT03 = CharField(null=True)  # Set BOTTOM 分区3 温度
    SetBottomZoneT04 = CharField(null=True)  # Set BOTTOM 分区4 温度
    SetBottomZoneT05 = CharField(null=True)  # Set BOTTOM 分区5 温度
    SetBottomZoneT06 = CharField(null=True)  # Set BOTTOM 分区6 温度
    SetBottomZoneT07 = CharField(null=True)  # Set BOTTOM 分区7 温度
    SetBottomZoneT08 = CharField(null=True)  # Set BOTTOM 分区8 温度
    SetBottomZoneT09 = CharField(null=True)  # Set BOTTOM 分区9 温度
    SetBottomZoneT10 = CharField(null=True)  # Set BOTTOM 分区10 温度
    SetBottomZoneT11 = CharField(null=True)  # Set BOTTOM 分区11 温度
    SetBottomZoneT12 = CharField(null=True)  # Set BOTTOM 分区12 温度
    SetBottomZoneT13 = CharField(null=True)  # Set BOTTOM 分区13 温度

    TopZoneT01 = CharField(null=True)  # Actual TOP 分区1 温度
    TopZoneT02 = CharField(null=True)  # Actual TOP 分区2 温度
    TopZoneT03 = CharField(null=True)  # Actual TOP 分区3 温度
    TopZoneT04 = CharField(null=True)  # Actual TOP 分区4 温度
    TopZoneT05 = CharField(null=True)  # Actual TOP 分区5 温度
    TopZoneT06 = CharField(null=True)  # Actual TOP 分区6 温度
    TopZoneT07 = CharField(null=True)  # Actual TOP 分区7 温度
    TopZoneT08 = CharField(null=True)  # Actual TOP 分区8 温度
    TopZoneT09 = CharField(null=True)  # Actual TOP 分区9 温度
    TopZoneT10 = CharField(null=True)  # Actual TOP 分区10 温度
    TopZoneT11 = CharField(null=True)  # Actual TOP 分区11 温度
    TopZoneT12 = CharField(null=True)  # Actual TOP 分区12 温度
    TopZoneT13 = CharField(null=True)  # Actual TOP 分区13 温度
    BottomZoneT01 = CharField(null=True)  # Actual BOTTOM 分区1 温度
    BottomZoneT02 = CharField(null=True)  # Actual BOTTOM 分区2 温度
    BottomZoneT03 = CharField(null=True)  # Actual BOTTOM 分区3 温度
    BottomZoneT04 = CharField(null=True)  # Actual BOTTOM 分区4 温度
    BottomZoneT05 = CharField(null=True)  # Actual BOTTOM 分区5 温度
    BottomZoneT06 = CharField(null=True)  # Actual BOTTOM 分区6 温度
    BottomZoneT07 = CharField(null=True)  # Actual BOTTOM 分区7 温度
    BottomZoneT08 = CharField(null=True)  # Actual BOTTOM 分区8 温度
    BottomZoneT09 = CharField(null=True)  # Actual BOTTOM 分区9 温度
    BottomZoneT10 = CharField(null=True)  # Actual BOTTOM 分区10 温度
    BottomZoneT11 = CharField(null=True)  # Actual BOTTOM 分区11 温度
    BottomZoneT12 = CharField(null=True)  # Actual BOTTOM 分区12 温度
    BottomZoneT13 = CharField(null=True)  # Actual BOTTOM 分区13 温度

    MaxRiseSlope_upper = CharField(null=True)  # 最高升温斜率-上限
    MaxRiseSlope_lower = CharField(null=True)  # 最高升温斜率-下限
    MaxFallSlope_upper = CharField(null=True)  # 最高降温斜率-上限
    MaxFallSlope_lower = CharField(null=True)  # 最高降温斜率-下限
    Peak_Temp_upper = CharField(null=True)  # 最高温度-上限
    Peak_Temp_lower = CharField(null=True)  # 最高温度-下限

    T2_RiseSlope = CharField(null=True)  # T2升温斜率
    T2_FallSlope = CharField(null=True)  # T2降温斜率
    T2_Peak_Temp = CharField(null=True)  # T2温度
    T3_RiseSlope = CharField(null=True)  # T3升温斜率
    T3_FallSlope = CharField(null=True)  # T3降温斜率
    T3_Peak_Temp = CharField(null=True)  # T3温度
    T4_RiseSlope = CharField(null=True)  # T4升温斜率
    T4_FallSlope = CharField(null=True)  # T4降温斜率
    T4_Peak_Temp = CharField(null=True)  # T4温度
    T5_RiseSlope = CharField(null=True)  # T5升温斜率
    T5_FallSlope = CharField(null=True)  # T5降温斜率
    T5_Peak_Temp = CharField(null=True)  # T5温度
    T6_RiseSlope = CharField(null=True)  # T6升温斜率
    T6_FallSlope = CharField(null=True)  # T6降温斜率
    T6_Peak_Temp = CharField(null=True)  # T6温度
    T7_RiseSlope = CharField(null=True)  # T7升温斜率
    T7_FallSlope = CharField(null=True)  # T7降温斜率
    T7_Peak_Temp = CharField(null=True)  # T7温度
    T8_RiseSlope = CharField(null=True)  # T8升温斜率
    T8_FallSlope = CharField(null=True)  # T8降温斜率
    T8_Peak_Temp = CharField(null=True)  # T8温度
    T9_RiseSlope = CharField(null=True)  # T9升温斜率
    T9_FallSlope = CharField(null=True)  # T9降温斜率
    T9_Peak_Temp = CharField(null=True)  # T9温度
    T10_RiseSlope = CharField(null=True)  # T10升温斜率
    T10_FallSlope = CharField(null=True)  # T10降温斜率
    T10_Peak_Temp = CharField(null=True)  # T10温度

    def to_status_table_dict(self) -> dict:
        """转换为状态表格所需的字典格式"""
        return {
            "slot_id": self.Slot_id,
            "carrier_No": self.carrier_No,
            "panel_sn": self.panel_sn,
            "serial_number": self.serial_number,
            "result": self.result,
            "status": self.upload_status,
            "upload_time": self.upload_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            if self.upload_time
            else None,
            "sfc_result": self.sfc_result,
        }

    def to_content_table_dict(self) -> dict:
        """转换为详细内容表格所需的字典格式"""
        return {
            "slot_id": self.Slot_id,
            "carrier_No": self.carrier_No,
            "status": self.upload_status,
            "upload_time": self.upload_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            if self.upload_time
            else None,
            "sfc_result": self.sfc_result,
            "version": self.version,
            "id": self.id,
            "serial_number": self.serial_number,
            "panel_sn": self.panel_sn,
            "result": self.result,
            "InTime": self.InTime,
            "OutTime": self.OutTime,
            "O2": self.O2,
            "ExternalTemp": self.ExternalTemp,
            "Motor_UpHeat": self.Motor_UpHeat,
            "Motor_DnHeat": self.Motor_DnHeat,
            "Motor_UpWeld": self.Motor_UpWeld,
            "Motor_DnWeld": self.Motor_DnWeld,
            "Motor_Cooling": self.Motor_Cooling,
            "SetMotorSpeed": self.SetMotorSpeed,
            "MotorSpeed": self.MotorSpeed,
            "SetConveyorSpeed": self.SetConveyorSpeed,
            "ConveyorSpeed": self.ConveyorSpeed,
            "MaxRiseSlope_upper": self.MaxRiseSlope_upper,
            "MaxRiseSlope_lower": self.MaxRiseSlope_lower,
            "MaxFallSlope_upper": self.MaxFallSlope_upper,
            "MaxFallSlope_lower": self.MaxFallSlope_lower,
            "Peak_Temp_upper": self.Peak_Temp_upper,
            "Peak_Temp_lower": self.Peak_Temp_lower,
            "T2_RiseSlope": self.T2_RiseSlope,
            "T2_FallSlope": self.T2_FallSlope,
            "T2_Peak_Temp": self.T2_Peak_Temp,
            "T3_RiseSlope": self.T3_RiseSlope,
            "T3_FallSlope": self.T3_FallSlope,
            "T3_Peak_Temp": self.T3_Peak_Temp,
            "T4_RiseSlope": self.T4_RiseSlope,
            "T4_FallSlope": self.T4_FallSlope,
            "T4_Peak_Temp": self.T4_Peak_Temp,
            "T5_RiseSlope": self.T5_RiseSlope,
            "T5_FallSlope": self.T5_FallSlope,
            "T5_Peak_Temp": self.T5_Peak_Temp,
            "T6_RiseSlope": self.T6_RiseSlope,
            "T6_FallSlope": self.T6_FallSlope,
            "T6_Peak_Temp": self.T6_Peak_Temp,
            "T7_RiseSlope": self.T7_RiseSlope,
            "T7_FallSlope": self.T7_FallSlope,
            "T7_Peak_Temp": self.T7_Peak_Temp,
            "T8_RiseSlope": self.T8_RiseSlope,
            "T8_FallSlope": self.T8_FallSlope,
            "T8_Peak_Temp": self.T8_Peak_Temp,
            "T9_RiseSlope": self.T9_RiseSlope,
            "T9_FallSlope": self.T9_FallSlope,
            "T9_Peak_Temp": self.T9_Peak_Temp,
            "T10_RiseSlope": self.T10_RiseSlope,
            "T10_FallSlope": self.T10_FallSlope,
            "T10_Peak_Temp": self.T10_Peak_Temp,
        }

    @property
    def raw_data(self) -> str:
        """生成raw格式数据（列表形式，用于写入文件）"""

        Date = datetime.now().strftime("%Y-%m-%d")
        Time = datetime.now().strftime("%H:%M:%S")

        _raw_data = [
            self.station_code or "NULL",  # 站点代码
            self.Slot_id or "NULL",
            self.status_code if self.serial_number else 3,  # 状态码
            Date if Date else "NULL",  # 日期
            Time if Time else "NULL",  # 时间
            self.serial_number or "NULL",  # SN
            self.single_ct if self.single_ct else "NULL",  # 设备C/T (单站C/T)
            self.single_ct if self.single_ct else "NULL",  # 单板C/T
            "NULL",
            "NULL",
            "NULL",
            self.carrier_No or "NULL",  # 载具编号
            1 if self.result == "PASS" else 0,
            self.panel_sn or "NULL",  # 连板SN
            1 if self.result == "PASS" else 0,
            self.InTime if self.InTime else "NULL",  # 进板时间
            1 if self.result == "PASS" else 0,
            self.OutTime if self.OutTime else "NULL",  # 出板时间
            1 if self.result == "PASS" else 0,
            self.O2 if self.O2 else "NULL",  # 氧气浓度
            1 if self.result == "PASS" else 0,
            self.ExternalTemp if self.ExternalTemp else "NULL",  # 外部温度
            1 if self.result == "PASS" else 0,
            self.Motor_UpHeat if self.Motor_UpHeat else "NULL",
            1 if self.result == "PASS" else 0,
            self.Motor_DnHeat if self.Motor_DnHeat else "NULL",
            1 if self.result == "PASS" else 0,
            self.Motor_UpWeld if self.Motor_UpWeld else "NULL",
            1 if self.result == "PASS" else 0,
            self.Motor_DnWeld if self.Motor_DnWeld else "NULL",
            1 if self.result == "PASS" else 0,
            self.Motor_Cooling if self.Motor_Cooling else "NULL",
            1 if self.result == "PASS" else 0,
            self.SetConveyorSpeed
            if self.SetConveyorSpeed
            else "NULL",  # 设定传送带速度
            1 if self.result == "PASS" else 0,
            self.ConveyorSpeed if self.ConveyorSpeed else "NULL",  # 实际传送带速度
            1 if self.result == "PASS" else 0,
            self.SetTopZoneT01 or "NULL",
            1 if self.result == "PASS" else 0,
            self.SetTopZoneT02 or "NULL",
            1 if self.result == "PASS" else 0,
            self.SetTopZoneT03 or "NULL",
            1 if self.result == "PASS" else 0,
            self.SetTopZoneT04 or "NULL",
            1 if self.result == "PASS" else 0,
            self.SetTopZoneT05 or "NULL",
            1 if self.result == "PASS" else 0,
            self.SetTopZoneT06 or "NULL",
            1 if self.result == "PASS" else 0,
            self.SetTopZoneT07 or "NULL",
            1 if self.result == "PASS" else 0,
            self.SetTopZoneT08 or "NULL",
            1 if self.result == "PASS" else 0,
            self.SetTopZoneT09 or "NULL",
            1 if self.result == "PASS" else 0,
            self.SetTopZoneT10 or "NULL",
            1 if self.result == "PASS" else 0,
            self.SetTopZoneT11 or "NULL",
            1 if self.result == "PASS" else 0,
            self.SetTopZoneT12 or "NULL",
            1 if self.result == "PASS" else 0,
            self.SetTopZoneT13 or "NULL",
            1 if self.result == "PASS" else 0,
            self.SetBottomZoneT01 or "NULL",
            1 if self.result == "PASS" else 0,
            self.SetBottomZoneT02 or "NULL",
            1 if self.result == "PASS" else 0,
            self.SetBottomZoneT03 or "NULL",
            1 if self.result == "PASS" else 0,
            self.SetBottomZoneT04 or "NULL",
            1 if self.result == "PASS" else 0,
            self.SetBottomZoneT05 or "NULL",
            1 if self.result == "PASS" else 0,
            self.SetBottomZoneT06 or "NULL",
            1 if self.result == "PASS" else 0,
            self.SetBottomZoneT07 or "NULL",
            1 if self.result == "PASS" else 0,
            self.SetBottomZoneT08 or "NULL",
            1 if self.result == "PASS" else 0,
            self.SetBottomZoneT09 or "NULL",
            1 if self.result == "PASS" else 0,
            self.SetBottomZoneT10 or "NULL",
            1 if self.result == "PASS" else 0,
            self.SetBottomZoneT11 or "NULL",
            1 if self.result == "PASS" else 0,
            self.SetBottomZoneT12 or "NULL",
            1 if self.result == "PASS" else 0,
            self.SetBottomZoneT13 or "NULL",
            1 if self.result == "PASS" else 0,
            self.TopZoneT01 or "NULL",
            1 if self.result == "PASS" else 0,
            self.TopZoneT02 or "NULL",
            1 if self.result == "PASS" else 0,
            self.TopZoneT03 or "NULL",
            1 if self.result == "PASS" else 0,
            self.TopZoneT04 or "NULL",
            1 if self.result == "PASS" else 0,
            self.TopZoneT05 or "NULL",
            1 if self.result == "PASS" else 0,
            self.TopZoneT06 or "NULL",
            1 if self.result == "PASS" else 0,
            self.TopZoneT07 or "NULL",
            1 if self.result == "PASS" else 0,
            self.TopZoneT08 or "NULL",
            1 if self.result == "PASS" else 0,
            self.TopZoneT09 or "NULL",
            1 if self.result == "PASS" else 0,
            self.TopZoneT10 or "NULL",
            1 if self.result == "PASS" else 0,
            self.TopZoneT11 or "NULL",
            1 if self.result == "PASS" else 0,
            self.TopZoneT12 or "NULL",
            1 if self.result == "PASS" else 0,
            self.TopZoneT13 or "NULL",
            1 if self.result == "PASS" else 0,
            self.BottomZoneT01 or "NULL",
            1 if self.result == "PASS" else 0,
            self.BottomZoneT02 or "NULL",
            1 if self.result == "PASS" else 0,
            self.BottomZoneT03 or "NULL",
            1 if self.result == "PASS" else 0,
            self.BottomZoneT04 or "NULL",
            1 if self.result == "PASS" else 0,
            self.BottomZoneT05 or "NULL",
            1 if self.result == "PASS" else 0,
            self.BottomZoneT06 or "NULL",
            1 if self.result == "PASS" else 0,
            self.BottomZoneT07 or "NULL",
            1 if self.result == "PASS" else 0,
            self.BottomZoneT08 or "NULL",
            1 if self.result == "PASS" else 0,
            self.BottomZoneT09 or "NULL",
            1 if self.result == "PASS" else 0,
            self.BottomZoneT10 or "NULL",
            1 if self.result == "PASS" else 0,
            self.BottomZoneT11 or "NULL",
            1 if self.result == "PASS" else 0,
            self.BottomZoneT12 or "NULL",
            1 if self.result == "PASS" else 0,
            self.BottomZoneT13 or "NULL",
            1 if self.result == "PASS" else 0,
            self.MaxRiseSlope_upper or "NULL",
            1 if self.result == "PASS" else 0,
            self.MaxRiseSlope_lower or "NULL",
            1 if self.result == "PASS" else 0,
            self.MaxFallSlope_upper or "NULL",
            1 if self.result == "PASS" else 0,
            self.MaxFallSlope_lower or "NULL",
            1 if self.result == "PASS" else 0,
            self.Peak_Temp_upper or "NULL",
            1 if self.result == "PASS" else 0,
            self.Peak_Temp_lower or "NULL",
            1 if self.result == "PASS" else 0,
            self.T2_RiseSlope or "NULL",
            1 if self.result == "PASS" else 0,
            self.T2_FallSlope or "NULL",
            1 if self.result == "PASS" else 0,
            self.T2_Peak_Temp or "NULL",
            1 if self.result == "PASS" else 0,
            self.T3_RiseSlope or "NULL",
            1 if self.result == "PASS" else 0,
            self.T3_FallSlope or "NULL",
            1 if self.result == "PASS" else 0,
            self.T3_Peak_Temp or "NULL",
            1 if self.result == "PASS" else 0,
            self.T4_RiseSlope or "NULL",
            1 if self.result == "PASS" else 0,
            self.T4_FallSlope or "NULL",
            1 if self.result == "PASS" else 0,
            self.T4_Peak_Temp or "NULL",
            1 if self.result == "PASS" else 0,
            self.T5_RiseSlope or "NULL",
            1 if self.result == "PASS" else 0,
            self.T5_FallSlope or "NULL",
            1 if self.result == "PASS" else 0,
            self.T5_Peak_Temp or "NULL",
            1 if self.result == "PASS" else 0,
            self.T6_RiseSlope or "NULL",
            1 if self.result == "PASS" else 0,
            self.T6_FallSlope or "NULL",
            1 if self.result == "PASS" else 0,
            self.T6_Peak_Temp or "NULL",
            1 if self.result == "PASS" else 0,
            self.T7_RiseSlope or "NULL",
            1 if self.result == "PASS" else 0,
            self.T7_FallSlope or "NULL",
            1 if self.result == "PASS" else 0,
            self.T7_Peak_Temp or "NULL",
            1 if self.result == "PASS" else 0,
            self.T8_RiseSlope or "NULL",
            1 if self.result == "PASS" else 0,
            self.T8_FallSlope or "NULL",
            1 if self.result == "PASS" else 0,
            self.T8_Peak_Temp or "NULL",
            1 if self.result == "PASS" else 0,
            self.T9_RiseSlope or "NULL",
            1 if self.result == "PASS" else 0,
            self.T9_FallSlope or "NULL",
            1 if self.result == "PASS" else 0,
            self.T9_Peak_Temp or "NULL",
            1 if self.result == "PASS" else 0,
            self.T10_RiseSlope or "NULL",
            1 if self.result == "PASS" else 0,
            self.T10_FallSlope or "NULL",
            1 if self.result == "PASS" else 0,
            self.T10_Peak_Temp or "NULL",
            1 if self.result == "PASS" else 0,
        ]

        return _raw_data

    @property
    def status_code(self) -> int:
        """根据 result 返回对应的状态码"""
        mapping = {"PASS": 1, "FAIL": 0, "UNTEST": 3, "SKIP": 3}
        return mapping.get(self.result.upper() if self.result else "", 3)


db.connect()
db.create_tables([AOI_SPI, Dispensing, ReflowOven], safe=True)

# 数据库迁移：添加 carrier_No 字段（如果不存在）
try:
    cursor = db.execute_sql("PRAGMA table_info(reflowoven)")
    columns = [row[1] for row in cursor.fetchall()]

    if "carrier_No" not in columns:
        db.execute_sql("ALTER TABLE reflowoven ADD COLUMN carrier_No VARCHAR(255)")
        logger.info("数据库迁移成功：已添加 carrier_No 字段到 ReflowOven 表")
except Exception as e:
    logger.error(f"数据库迁移失败: {e}")

db.close()
