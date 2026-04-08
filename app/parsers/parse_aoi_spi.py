import re
from typing import List
from app.common.model import AOI_SPI, Result
from app.common.config import cfg

pattern = re.compile(
    r"""
(?P<program>.+)\n
(?P<panel_serial_number>.+)\n
(?P<station_code>.+)\n
(?P<class_type>\w+)\n
(?P<user_name>.+)\n
(?P<work_order_number>.+)\n
(?P<date>\d{8})\n
(?P<time>\d{6})\n
(?P<flags>[\d;]*)\n
(?P<bot_or_top>[A-Z])\n
(?P<items>\d+)\n
(?P<result>\d+)\n
(?P<slot>\d+)?
""",
    re.VERBOSE,
)


def parse_records(text: str) -> List[AOI_SPI]:
    records = []
    for m in pattern.finditer(text):
        r = AOI_SPI(
            product_name="Moose",
            station_code=m.group("station_code"),
            slot_id=int(m.group("slot") if m.group("slot") else len(records) + 1),
            panel_serial_number=m.group("panel_serial_number"),
            class_type=m.group("class_type"),
            user_name=m.group("user_name"),
            work_order_number=m.group("work_order_number"),
            date=m.group("date"),
            time=m.group("time"),
            flags=m.group("flags"),
            bot_or_top=m.group("bot_or_top"),
            items=int(m.group("items")),
            result=Result.PASS if int(m.group("result")) == 0 else Result.FAIL,
        )
        records.append(r)

    return records


def parse_log_file(log_file_path: str) -> List[AOI_SPI]:
    with open(log_file_path, "r", encoding="utf-8") as f:
        text = f.read()
    return parse_records(text)


if __name__ == "__main__":
    from pprint import pprint

    records = parse_log_file("log/20251009/106_20251009140937.txt")

    for r in records:
        pprint(r)
