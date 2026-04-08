import os
import sys
import re
from datetime import datetime
from typing import List, Optional
from app.common.logger import Logger
from app.common.config import cfg
import time
import version

sn_rex = re.compile(r"([^_]+)$")

# 当直接运行此脚本（而非以模块方式通过 `python -m` 导入）时，
# Python 不会自动将项目根目录加入导入路径，导致 `from app...` 无法找到包。
# 下面的逻辑检测到直接脚本运行时，自动调整 sys.path，使导入正常工作。
if __name__ == "__main__" and __package__ is None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(
        os.path.dirname(script_dir)
    )  # 从 app/parsers/xxx.py 推导到项目根
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from app.common.model import ReflowOven, Result
from app.common.logger import logger

Logger = Logger("ReflowOvenParser")


def parse_log_file_reflow(log_file_path: str) -> Optional[ReflowOven]:
    """
    解析炉温LOG文件

    Args:
        log_file_path: LOG文件路径

    Returns:
        ReflowOven对象，如果解析失败返回None
    """
    try:
        with open(log_file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 第一次解析
        result = parse_content(content, log_file_path)

        # 检查所有字段是否有 None
        if result:
            Logger.info("检查解析结果字段完整性")
            none_fields = []
            # 获取对象的所有属性
            for attr_name in dir(result):
                # 跳过私有属性和方法
                if not attr_name.startswith("_") and not callable(
                    getattr(result, attr_name)
                ):
                    attr_value = getattr(result, attr_name)
                    if "None" == str(attr_value):
                        none_fields.append(attr_name)

            # 如果有字段为 None，重试一次
            if none_fields:
                Logger.warning(f"解析结果中以下字段为 None: {', '.join(none_fields)}")
                time.sleep(1)  # 等待0.5秒再重试
                result = parse_content(content, log_file_path)

                # 再次检查
                none_fields_retry = []
                for attr_name in dir(result):
                    if not attr_name.startswith("_") and not callable(
                        getattr(result, attr_name)
                    ):
                        attr_value = getattr(result, attr_name)
                        if "None" == str(attr_value):
                            none_fields_retry.append(attr_name)
                if none_fields_retry:
                    Logger.info(
                        f"重新解析后以下字段仍为 None: {', '.join(none_fields_retry)}，返回 None"
                    )
                    return None
                else:
                    Logger.info("重新解析成功，所有字段都有值")

        return result

    except Exception as e:
        Logger.info(f"解析炉温LOG文件失败: {log_file_path}, 错误: {e}")
        return None


def parse_content(content: str, log_file_path: str) -> Optional[ReflowOven]:
    """
    解析炉温LOG内容

    Args:
        content: LOG文件内容

    Returns:
        ReflowOven对象，如果解析失败返回None
    """
    try:
        lines = content.strip().split("\n")
        # 解析基本信息
        serial_number = None
        profile_start_time = None
        profile_end_time = None
        set_top_setpoints = []
        set_bottom_setpoints = []
        set_conveyor_speed = None
        actual_top_setpoints = []
        actual_bottom_setpoints = []
        actual_conveyor_speed = None
        max_rise_slope_upper = None
        max_rise_slope_lower = None
        max_fall_slope_upper = None
        max_fall_slope_lower = None
        peak_temp_upper = None
        peak_temp_lower = None
        tc_rise_slope = {}
        tc_fall_slope = {}
        tc_peak_temp = {}

        Logger.info(f"解析文件路径: {str(log_file_path)}")

        # 逐行解析
        for i, line in enumerate(lines):
            line = line.strip()

            # 解析序列号
            if line.startswith("SN") and ":" in line:
                # 使用制表符分割，取最后一个非空值
                parts = [p.strip() for p in line.split("\t") if p.strip()]
                # 如果有多个部分，取最后一个（跳过 'SN:' 或 'SN1:' 标签）
                if len(parts) >= 2:
                    serial_number = parts[-1]
                else:
                    # 回退方案：使用冒号分割
                    serial_number = (
                        line.split(":", 1)[1].strip() if ":" in line else None
                    )
            if not serial_number:
                log_file_path = str(log_file_path).replace(".txt", "")
                serial_number = re.search(sn_rex, str(log_file_path)).group(1)

            # 解析开始时间
            elif line.startswith("Profile Start Time:"):
                # 使用制表符分割，取最后一个非空值
                parts = [p.strip() for p in line.split("\t") if p.strip()]
                if len(parts) >= 2:
                    profile_start_time = parts[-1]
                else:
                    profile_start_time = (
                        line.split(":", 1)[1].strip() if ":" in line else None
                    )

            # 解析结束时间
            elif line.startswith("Profile End Time:"):
                # 使用制表符分割，取最后一个非空值
                parts = [p.strip() for p in line.split("\t") if p.strip()]
                if len(parts) >= 2:
                    profile_end_time = parts[-1]
                else:
                    profile_end_time = (
                        line.split(":", 1)[1].strip() if ":" in line else None
                    )

            elif line.startswith("Set Top Setpoints:"):
                after_colon = line.split(":", 1)[1]
                set_top_setpoints = [
                    v for v in re.split(r"[\t ]+", after_colon.strip()) if v
                ]
                Logger.info(f"解析到设定顶部设定点: {set_top_setpoints}")

            elif line.startswith("Set Bottom Setpoints"):
                after_colon = (
                    line.split(":", 1)[1]
                    if ":" in line
                    else re.sub(r"^Set Bottom Setpoints\s*", "", line)
                )
                set_bottom_setpoints = [
                    v for v in re.split(r"[\t ]+", after_colon.strip()) if v
                ]
                Logger.info(f"解析到设定底部设定点: {set_bottom_setpoints}")
            elif line.startswith("Set Conveyor Speed:"):
                # 使用制表符分割，取最后一个非空值
                parts = [p.strip() for p in line.split("\t") if p.strip()]
                if len(parts) >= 2:
                    set_conveyor_speed = parts[-1]
                else:
                    set_conveyor_speed = (
                        line.split(":", 1)[1].strip() if ":" in line else None
                    )
                Logger.info(f"解析到设定传送带速度: {set_conveyor_speed}")
            elif line.startswith("Actual Top Setpoints:"):
                after_colon = line.split(":", 1)[1]
                actual_top_setpoints = [
                    v for v in re.split(r"[\t ]+", after_colon.strip()) if v
                ]
                Logger.info(f"解析到实际顶部设定点: {actual_top_setpoints}")
            elif line.startswith("Actual Bottom Setpoints"):
                after_colon = (
                    line.split(":", 1)[1]
                    if ":" in line
                    else re.sub(r"^Actual Bottom Setpoints\s*", "", line)
                )
                actual_bottom_setpoints = [
                    v for v in re.split(r"[\t ]+", after_colon.strip()) if v
                ]
                Logger.info(f"解析到实际底部设定点: {actual_bottom_setpoints}")
            elif line.startswith("Actual Conveyor Speed:"):
                # 使用制表符分割，取最后一个非空值
                parts = [p.strip() for p in line.split("\t") if p.strip()]
                if len(parts) >= 2:
                    actual_conveyor_speed = parts[-1]
                else:
                    actual_conveyor_speed = (
                        line.split(":", 1)[1].strip() if ":" in line else None
                    )
                Logger.info(f"解析到实际传送带速度: {actual_conveyor_speed}")

            elif line.startswith("MaxRiseSlope"):
                vals = line.split()
                if len(vals) >= 3:
                    max_rise_slope_upper = vals[1]
                    max_rise_slope_lower = vals[2]
                    Logger.info(
                        f"解析到MaxRiseSlope上下限: upper={max_rise_slope_upper}, lower={max_rise_slope_lower}"
                    )

            elif line.startswith("MaxFallSlope"):
                vals = line.split()
                if len(vals) >= 3:
                    max_fall_slope_upper = vals[1]
                    max_fall_slope_lower = vals[2]
                    Logger.info(
                        f"解析到MaxFallSlope上下限: upper={max_fall_slope_upper}, lower={max_fall_slope_lower}"
                    )

            elif line.startswith("Peak"):
                vals = line.split()
                if len(vals) >= 3:
                    peak_temp_upper = vals[1]
                    peak_temp_lower = vals[2]
                    Logger.info(
                        f"解析到Peak温度上下限: upper={peak_temp_upper}, lower={peak_temp_lower}"
                    )

            elif re.match(r"^T(\d+)\s", line):
                vals = line.split()
                tc_num = vals[0]  # "T2", "T3", ...
                if len(vals) >= 7:
                    tc_rise_slope[tc_num] = vals[4]
                    tc_fall_slope[tc_num] = vals[5]
                    tc_peak_temp[tc_num] = vals[6]
                    Logger.info(
                        f"解析到{tc_num}: RiseSlope={vals[4]}, FallSlope={vals[5]}, Peak={vals[6]}"
                    )

        ExternalTemp = lines[-1].split("\t")[-1].strip()
        Logger.info(f"解析到外部温度: {ExternalTemp}")

        # 提取产品名称和线别（从序列号中）
        product_name = "Moose"  # 默认产品名称
        line_name = None
        station_code = f"Reflow-{cfg.get(cfg.station_code)}"

        # 尝试从文件路径解析线别
        if log_file_path:
            # 格式示例: MOOS-T-01R1-01-P2-9_E85-T-01R1-P2-01_251204_08-34-24_C472538051040631802D021.txt
            # 提取第一个下划线到第二个下划线之间的内容作为线别（E85-T-01R1-P2-01）
            filename = os.path.basename(log_file_path)
            match = re.search(r"_([^_]+)_", filename)
            if match:
                line_name = match.group(1)
                Logger.info(f"从文件路径中解析线别: {line_name}")
            else:
                Logger.info(f"从文件路径中解析线别: None")

        # 格式化温度数据为JSON字符串

        # 转换测试时间格式
        test_time = None
        test_time_dt = None
        if profile_start_time:
            try:
                # 格式: 2025/11/25 16:57:07
                dt = datetime.strptime(profile_start_time, "%Y/%m/%d %H:%M:%S")
                test_time = int(dt.timestamp())
                test_time_dt = dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                pass

        O2_value, motor_value = for_csv_get_O2()

        # 创建 ReflowOven 对象
        reflow_oven = ReflowOven(
            product_name=product_name,
            line_name=line_name,
            station_code=station_code,
            serial_number=serial_number,
            panel_sn=serial_number,
            carrier_No=serial_number,  # 载具编号
            # result=Result.Pass,
            test_time=test_time,
            test_time_dt=test_time_dt,
            version=version.get_version(),  # 新增字段
            InTime=profile_start_time,
            OutTime=profile_end_time,
            O2="".join(O2_value) if O2_value else None,  # LOG中未包含氧气浓度
            ExternalTemp=ExternalTemp,
            # LOG中未包含外部温度
            Motor_UpHeat=motor_value[0] if motor_value else None,
            Motor_DnHeat=motor_value[1] if motor_value else None,
            Motor_UpWeld=motor_value[2] if motor_value else None,
            Motor_DnWeld=motor_value[3] if motor_value else None,
            Motor_Cooling=motor_value[4] if motor_value else None,
            SetConveyorSpeed=set_conveyor_speed,
            ConveyorSpeed=actual_conveyor_speed,
        )
        # 保存文件路径到对象属性（用于后续文件移动）
        reflow_oven.log_file_path = log_file_path
        logger.info(f"创建 ReflowOven 对象: {reflow_oven}")

        reflow_oven.MaxRiseSlope_upper = max_rise_slope_upper
        reflow_oven.MaxRiseSlope_lower = max_rise_slope_lower
        reflow_oven.MaxFallSlope_upper = max_fall_slope_upper
        reflow_oven.MaxFallSlope_lower = max_fall_slope_lower
        reflow_oven.Peak_Temp_upper = peak_temp_upper
        reflow_oven.Peak_Temp_lower = peak_temp_lower

        for tc_key, val in tc_rise_slope.items():
            setattr(reflow_oven, f"{tc_key}_RiseSlope", val)
        for tc_key, val in tc_fall_slope.items():
            setattr(reflow_oven, f"{tc_key}_FallSlope", val)
        for tc_key, val in tc_peak_temp.items():
            setattr(reflow_oven, f"{tc_key}_Peak_Temp", val)

        for idx, value in enumerate(set_top_setpoints, start=1):
            setattr(reflow_oven, f"SetTopZoneT{idx:02d}", value)

        for idx, value in enumerate(set_bottom_setpoints, start=1):
            setattr(reflow_oven, f"SetBottomZoneT{idx:02d}", value)

        for idx, value in enumerate(actual_top_setpoints, start=1):
            setattr(reflow_oven, f"TopZoneT{idx:02d}", value)

        for idx, value in enumerate(actual_bottom_setpoints, start=1):
            setattr(reflow_oven, f"BottomZoneT{idx:02d}", value)

        Logger.info(f"解析完成，返回 {reflow_oven} 对象")

        return reflow_oven

    except Exception as e:
        Logger.exception(f"解析炉温LOG内容失败: {e}")
        return None


def for_csv_get_O2():
    Logger.info("開始取得O2值")
    try:
        CSV_Path = cfg.get(cfg.csv_path)
        if not os.path.exists(CSV_Path):
            Logger.warning(f"CSV路径不存在: {CSV_Path}")
            return
        csv_files = datetime.now().strftime("%Y-%m-%d") + ".csv"
        if not csv_files:
            Logger.warning(f"No CSV files found in path: {CSV_Path}")
            return None
        latest_file = os.path.join(CSV_Path, csv_files)

        O2_value, motor_value = get_last_column_by_index(latest_file)

        if O2_value and motor_value:
            return O2_value, motor_value
        else:
            return None, None

    except Exception as e:
        Logger.error("取得O2值失敗")
        Logger.error(f"Error getting Reflow result: {e}")
        return None, None


def get_last_column_by_index(filename):
    for i in range(6):
        try:
            with open(filename, "r", encoding="utf-8") as file:
                result = file.readlines()[-1].strip().split(",")
                o2, motor = result[11:12:], result[43:48:]
                return o2, motor

        except Exception as e:
            Logger.error(f"Error reading CSV file {filename}: {e}")
            time.sleep(0.5)
            continue


def parse_batch_files(file_paths: List[str]) -> List[ReflowOven]:
    results = []
    for file_path in file_paths:
        record = parse_log_file_reflow(file_path)
        if record:
            results.append(record)

    return results


if __name__ == "__main__":
    from pprint import pprint

    # 测试解析
    log_file = "app/parsers/MOOS-T-01R1-01-P2-9_E85-T-01R1-P2-01_251204_08-34-24_C472538051040631802D021.txt"

    result = parse_log_file_reflow(log_file)

    if result:
        print("=" * 80)
        print("解析结果:")
        print("=" * 80)
        pprint(result)
        print("\n")
        print("=" * 80)
        print("字典格式:")
        print("=" * 80)
    else:
        print("解析失败")
