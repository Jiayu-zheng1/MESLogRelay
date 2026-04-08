import csv
from typing import List, Dict
from app.common.logger import Logger

logger = Logger("SPI_CSV_Parser")


def parse_log_file(file_path: str) -> List[Dict]:
    """
    解析 SPI CSV 文件，只读取最后一次测试的数据（最后 8 行）
    文件格式:
    - 第1行: 表头 (No,BoardNo,Barcode,Time,Job,Result,User,Line,Lot)
    - 第2行开始: Panel 数据，每次测试生成 8 条记录（8 连板）
      - No: 流水号（每次测试递增）
      - Barcode: 连板 SN（8 条记录相同）
      - BoardNo: 槽位号 1-8（区分每个单板）

    返回: 最后一个 Panel 的槽位数据列表（8 条记录）
    """
    try:
        all_records = []

        with open(file_path, "r", encoding="utf-8") as f:
            csv_reader = csv.DictReader(f)

            # 读取所有 Panel 数据行
            for row in csv_reader:
                no_value = (row.get("No") or "").strip()

                # 遇到空行或无效的 No 值（非数字），停止读取
                if not no_value:
                    break

                # 检查 No 是否是有效的数字（流水号）
                try:
                    int(no_value)
                except (ValueError, TypeError):
                    # No 不是数字，说明到了第二部分数据，停止读取
                    break

                # 只保留前9列基本信息，处理 None 值
                record = {
                    "No": no_value,
                    "BoardNo": (row.get("BoardNo") or "").strip(),
                    "Barcode": (row.get("Barcode") or "").strip(),
                    "Time": (row.get("Time") or "").strip(),
                    "Job": (row.get("Job") or "").strip(),
                    "Result": (row.get("Result") or "").strip(),
                    "User": (row.get("User") or "").strip(),
                    "Line": (row.get("Line") or "").strip(),
                    "Lot": (row.get("Lot") or "").strip(),
                }
                all_records.append(record)

        # 只取最后 8 条记录（最后一个 Panel）
        records = all_records[-8:] if len(all_records) >= 8 else all_records

        # 记录解析结果
        logger.info(
            f"文件共有 {len(all_records)} 条记录，取最后 {len(records)} 条（最后一个 Panel）"
        )

        if len(records) > 0:
            last_record = records[-1]
            last_no_value = last_record.get("No", "")
            panel_barcode = last_record.get("Barcode", "")
            logger.info(f"最后一个 Panel: No={last_no_value}, Barcode={panel_barcode}")

            # 1. 获取整个 CSV 文件中最后有数据的列号
            last_col_with_data = get_last_column_with_data(file_path)

            # 2. 在最后一列中找到与 last_no_value 相同的值，获取行号
            matching_rows = find_rows_in_column(
                file_path, last_col_with_data, last_no_value
            )

            # 3. 获取 RPASS 槽位的详细测量数据并添加到 records 中
            get_rpass_slot_measurements(
                file_path, records, last_no_value, matching_rows
            )

        return records

    except Exception as e:
        logger.error(f"解析文件时出错: {e}", exc_info=True)
        return None


def get_panel_data_by_no(records: List[Dict], no_value: str) -> List[Dict]:
    """
    获取指定 No 值的所有行数据，按 BoardNo 排序，每行作为一个独立的字典

    Args:
        records: 所有记录列表
        no_value: 要查找的 No 值

    Returns:
        字典列表，每个字典包含一个槽位的数据（slot, result, panel_SN, TestTime）
    """
    # 找到所有 No 等于指定值的行
    matching_records = [r for r in records if r.get("No") == no_value]

    # 按 BoardNo 排序
    matching_records.sort(key=lambda x: int(x.get("BoardNo", "0")))

    # 组成字典列表，每行一个字典
    result = []
    for record in matching_records:
        result.append(
            {
                "slot": record.get("BoardNo", ""),
                "result": record.get("Result", ""),
                "panel_SN": record.get("Barcode", ""),
                "TestTime": record.get("Time", ""),
            }
        )

    return result


def get_last_column_with_data(file_path: str) -> int:
    """
    获取整个 CSV 文件中最后有数据的列号（从0开始）

    Args:
        file_path: CSV 文件路径

    Returns:
        最后有数据的列号（从0开始）
    """
    max_col_index = 0

    with open(file_path, "r", encoding="utf-8") as f:
        csv_reader = csv.reader(f)

        for row in csv_reader:
            # 从右往左找到第一个非空单元格
            for i in range(len(row) - 1, -1, -1):
                if row[i].strip():
                    max_col_index = max(max_col_index, i)
                    break

    return max_col_index


def find_rows_in_column(file_path: str, col_index: int, search_value: str) -> List[int]:
    """
    在指定列中查找匹配的值，返回所有匹配的行号

    Args:
        file_path: CSV 文件路径
        col_index: 列号（从0开始）
        search_value: 要查找的值

    Returns:
        匹配的行号列表（从0开始）
    """
    matching_rows = []

    with open(file_path, "r", encoding="utf-8") as f:
        csv_reader = csv.reader(f)

        for row_num, row in enumerate(csv_reader):
            if col_index < len(row) and row[col_index].strip() == search_value:
                matching_rows.append(row_num)

    return matching_rows


def get_rpass_slot_measurements(
    file_path: str, records: List[Dict], no_value: str, detail_rows: List[int]
) -> Dict[str, List[Dict]]:
    """
    获取所有 RPASS 槽位的详细测量数据并添加到 records 中

    Args:
        file_path: CSV 文件路径
        records: 所有记录列表（将直接修改此列表）
        no_value: Panel 编号
        detail_rows: 详细数据的行号列表

    Returns:
        字典，key 为 slot 编号，value 为该 slot 的测量数据列表
    """
    # 1. 找出该 Panel 中所有 RPASS 的槽位及其在 records 中的索引
    rpass_slots_info = []  # [(slot, record_index), ...]
    for i, record in enumerate(records):
        if record.get("No") == no_value and record.get("Result", "").upper() == "RPASS":
            rpass_slots_info.append((record.get("BoardNo", ""), i))

    if not rpass_slots_info:
        logger.debug("没有找到 RPASS 的槽位")
        return {}

    rpass_slots = [slot for slot, _ in rpass_slots_info]
    logger.info(f"找到 RPASS 槽位: {rpass_slots}")

    # 2. 读取详细数据部分
    # detail_rows 包含标题行，标题行的最后一列是 Panel number
    # 从标题行的下一行开始读取，直到遇到空行或列数不足为止
    # 数据格式: {Slot_ID: {Component_ID: {Volume_percent: [], ...}}}
    slot_measurements = {slot: {} for slot in rpass_slots}

    if not detail_rows:
        logger.warning("没有找到详细数据行")
        return {}

    # 找到详细数据的起始行号（标题行的下一行）
    detail_start_row = detail_rows[0] + 1
    logger.debug(f"详细数据起始行: {detail_start_row} (标题行: {detail_rows[0]})")

    # 读取表头，建立列名到索引的映射
    header_map = {}
    with open(file_path, "r", encoding="utf-8") as f:
        csv_reader = csv.reader(f)
        for row_num, row in enumerate(csv_reader):
            if row_num == detail_rows[0]:  # 标题行
                for idx, col_name in enumerate(row):
                    col_name = col_name.strip()
                    if col_name:
                        header_map[col_name] = idx
                logger.debug(f"详细数据表头: {list(header_map.keys())}")
                break

    # 检查必需的列是否存在
    required_columns = [
        "Component ID",
        "PAD ID",
        "Volume(%)",
        "OffsetX(%)",
        "OffsetY(%)",
    ]
    missing_columns = [col for col in required_columns if col not in header_map]
    if missing_columns:
        logger.warning(f"缺少必需的列: {missing_columns}")
        return {}

    matched_panel_rows = 0
    with open(file_path, "r", encoding="utf-8") as f:
        csv_reader = csv.reader(f)

        for row_num, row in enumerate(csv_reader):
            # 只处理详细数据区域的行（从标题行的下一行开始）
            if row_num < detail_start_row:
                continue

            # 如果行为空或者是下一个Panel的表头（以"Inspection Time"开头），说明这个Panel的数据结束了
            if len(row) == 0 or (len(row) > 0 and row[0].strip() == "Inspection Time"):
                break

            # 使用表头获取 Component ID
            component_id_idx = header_map.get("Component ID")
            component_id = (
                row[component_id_idx].strip()
                if component_id_idx is not None and len(row) > component_id_idx
                else ""
            )

            # 如果 Component ID 为空，跳过
            if not component_id:
                continue

            matched_panel_rows += 1

            # 检查这个 Component ID 是否包含 RPASS 槽位编号
            # 例如: slot=7 匹配 J0100_7, SUS_7
            for slot in rpass_slots:
                # 匹配模式：Component ID 包含 _槽位号
                if f"_{slot}" in component_id:
                    # 初始化该 Component ID 的数据结构
                    if component_id not in slot_measurements[slot]:
                        slot_measurements[slot][component_id] = {
                            "PIDs": [],
                            "Volume_percent": [],
                            "OffsetX_percent": [],
                            "OffsetY_percent": [],
                        }

                    # 使用表头获取数据
                    pad_id_idx = header_map.get("PAD ID")
                    volume_idx = header_map.get("Volume(%)")
                    offset_x_idx = header_map.get("OffsetX(%)")
                    offset_y_idx = header_map.get("OffsetY(%)")

                    pad_id = (
                        row[pad_id_idx].strip()
                        if pad_id_idx is not None and len(row) > pad_id_idx
                        else ""
                    )
                    volume = (
                        row[volume_idx].strip()
                        if volume_idx is not None and len(row) > volume_idx
                        else ""
                    )
                    offset_x = (
                        row[offset_x_idx].strip()
                        if offset_x_idx is not None and len(row) > offset_x_idx
                        else ""
                    )
                    offset_y = (
                        row[offset_y_idx].strip()
                        if offset_y_idx is not None and len(row) > offset_y_idx
                        else ""
                    )

                    # 添加 PID
                    if pad_id:
                        slot_measurements[slot][component_id]["PIDs"].append(pad_id)

                    if volume:
                        slot_measurements[slot][component_id]["Volume_percent"].append(
                            volume
                        )
                    if offset_x:
                        slot_measurements[slot][component_id]["OffsetX_percent"].append(
                            offset_x
                        )
                    if offset_y:
                        slot_measurements[slot][component_id]["OffsetY_percent"].append(
                            offset_y
                        )

    logger.info(f"总共找到 {matched_panel_rows} 行 Panel '{no_value}' 的数据")

    # 记录每个槽位找到的 Component IDs
    for slot in rpass_slots:
        comp_ids = list(slot_measurements[slot].keys())
        logger.info(f"Slot {slot} 找到的 Component ID: {comp_ids}")

    # 3. 将测量数据添加到 records 中对应的字典
    for slot, record_index in rpass_slots_info:
        # 直接将该 slot 的所有 Component ID 数据添加到 records
        records[record_index]["measurements"] = slot_measurements[slot]

        # 计算总数据量
        total_count = sum(
            len(comp_data["Volume_percent"])
            for comp_data in slot_measurements[slot].values()
        )
        logger.info(f"Slot {slot} 添加了 {total_count} 条测量数据")

    return slot_measurements
