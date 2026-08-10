import re
from datetime import datetime
from app.common.enums import Result
from app.common.database import Dispensing


def parse_log_file(log_file_path):
    """解析日志文件，提取 Encap_Glue_Dispensing 数据"""

    with open(log_file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    encap_data_list = []
    current_board_data = {}

    i = 0
    skip_pcs = 0
    valve = 0.0
    while i < len(lines):
        line = lines[i].strip()

        # 提取阀门重量
        if "Flowrate Measured, Scale=1" in line:
            match = re.search(r"Actual= ([\d.]+) mg/dot", line)
            if match:
                valve = match.group(1)

        # 检测新的测试开始
        if "Run Started" in line and "Board #" in line:
            current_board_data = {}
            # 提取 Board 编号
            match = re.search(r"Board #(\d+)", line)
            if match:
                current_board_data["board_number"] = match.group(1)

            # 提取测试时间
            date_time_match = re.match(
                r"(\d{4}-\d{2}-\d{2}),(\d{2}:\d{2}:\d{2}\.\d+)", line
            )
            if date_time_match:
                date_str = date_time_match.group(1)
                time_str = date_time_match.group(2).split(".")[0]
                dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
                current_board_data["test_time"] = int(dt.timestamp())

        # 喷嘴温度
        if "Current Heater Temperature,Heater 1, Channel 1" in line:
            match = re.search(
                r"Current Heater Temperature,Heater 1, Channel 1, Temp ([\d.]+)", line
            )
            if match:
                current_board_data["nozzle_temp"] = match.group(1)

        # 底部加热器温度
        if "Current Heater Temperature,Heater 1, Channel 2" in line:
            match = re.search(
                r"Current Heater Temperature,Heater 1, Channel 2, Temp ([\d.]+)", line
            )
            if match:
                current_board_data["bottom_heater_temp"] = match.group(1)

        # 提取 Serial Number
        if "Scanner Instruction Code Read" in line:
            match = re.search(r"Code Read = ([A-Z0-9]+)", line)
            if match:
                current_board_data["serial_number"] = match.group(1)

        # 提取重量数据
        if "Programmed Instruction Weight" in line:
            match = re.search(r"programmed weight = ([\d.]+) mg", line)
            if match:
                weight = match.group(1)
                if "weights" not in current_board_data:
                    current_board_data["weights"] = []
                current_board_data["weights"].append(weight)

        # 跳过 pcs
        if "Pattern Skipped" in line:
            match = re.search(r"Pattern Skipped,(\d+)pcs", line)
            if match:
                skip_pcs += int(match.group(1))

        # 检测测试结束
        if "Run Finished" in line and "Board #" in line:
            # 提取测试结果
            if "Status: PASS" in line:
                current_board_data["result"] = Result.PASS
            elif "Status: FAIL" in line:
                current_board_data["result"] = Result.FAIL
            elif "Status: RPASS" in line:
                current_board_data["result"] = Result.RPASS

            # 设置跳过的 pcs
            current_board_data["skip_pcs"] = skip_pcs

            # 如果有完整数据，创建 Encap_Glue_Dispensing 对象
            if (
                "serial_number" in current_board_data
                and "test_time" in current_board_data
            ):
                try:
                    dispensing_obj = create_dispensing(current_board_data)
                    encap_data_list.append(dispensing_obj)
                except Exception as e:
                    print(f"创建对象失败: {e}")
                    print(f"数据: {current_board_data}")

            current_board_data = {}

        i += 1

    # 设置阀门重量
    if valve:
        for i in range(len(encap_data_list)):
            encap_data_list[i].IPQC_WeightValve = valve
            encap_data_list[i].SingleDotValve = valve

    return encap_data_list


def create_dispensing(data):
    """根据解析的数据创建 Dispensing 对象"""

    # 计算总设定重量
    weights = data.get("weights", [])
    skip_pcs = data.get("skip_pcs", 0)
    total_pcs = len(weights)
    effective_pcs = total_pcs - skip_pcs

    if effective_pcs <= 0:
        total_weight = sum(float(w) for w in weights)
    else:
        total_weight = sum(float(w) for w in weights) / float(effective_pcs)

    # 喷嘴温度
    nozzle_temp = data.get("nozzle_temp", "0.0")

    # 底部加热器温度
    bottom_heater = data.get("bottom_heater_temp", "0.0")

    test_time = data.get("test_time", 0)

    return Dispensing(
        product_name="MOOSE",
        serial_number=data.get("serial_number", ""),
        test_time=test_time,
        test_time_dt=datetime.fromtimestamp(test_time).strftime("%Y-%m-%d %H:%M:%S"),
        result=data.get("result", Result.PASS),
        TotalSettingWeight=f"{total_weight:.3f}",
        NozzleTemp=nozzle_temp,
        BottomHeaterTemp=bottom_heater,
    )


def get_value_from_serial_number(sn, log_file_path):
    """根据序列号从日志文件中获取对应的值"""
    encap_data_list = parse_log_file(log_file_path)
    for data in encap_data_list:
        if data.serial_number == sn:
            return data
    return None


def test_single_record(log_file_path, record_index=0):
    """测试解析单个记录"""
    print("=" * 80)
    print(f"解析日志文件: {log_file_path}")
    print("=" * 80)

    encap_data_list = parse_log_file(log_file_path)

    print(f"\n总共找到 {len(encap_data_list)} 条 Encap_Glue_Dispensing 记录\n")

    if len(encap_data_list) == 0:
        print("未找到任何记录")
        return None

    if record_index >= len(encap_data_list):
        print(
            f"记录索引 {record_index} 超出范围，最大索引为 {len(encap_data_list) - 1}"
        )
        return None

    # 显示指定索引的记录
    record = encap_data_list[record_index]

    print(f"测试记录 #{record_index + 1}:")
    print("-" * 80)
    print(f"产线名称: {record.line_name}")
    print(f"工站名称: {record.station_code}")
    print(f"机种名: {record.product_name}")
    print(f"序列号: {record.serial_number}")
    print(f"测试时间: {record.test_time} ({datetime.fromtimestamp(record.test_time)})")
    print(f"测试结果: {record.result.value}")
    print(f"总设定重量: {record.TotalSettingWeight} mg")
    print(f"IPQC阀门重量: {record.IPQC_WeightValve} mg")
    print(f"阀门单点重量: {record.SingleDotValve} mg")
    print(f"喷嘴温度: {record.NozzleTemp} °C")
    print(f"底部加热器温度: {record.BottomHeaterTemp} °C")
    print(f"点胶路径: {record.DispensingPath}")
    print("-" * 80)

    return record


if __name__ == "__main__":
    log_file = "log/20251114.log"

    # 测试第一条记录
    test_single_record(log_file, record_index=1)

    print("\n")
