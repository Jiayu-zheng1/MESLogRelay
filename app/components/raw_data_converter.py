import os
from pathlib import Path
import sys
from datetime import datetime
import json
from queue import Queue
import threading
import csv
import shutil
from itertools import zip_longest

from PySide6.QtCore import QStandardPaths

from app.common.const import RAW_COUNT_FILE
from app.common.config import cfg
from app.common.logger import Logger
from app.common.database import ReflowOven, AOI_SPI

logger = Logger("RawDataConverter")


class CounterManager:
    def __init__(self):
        self.counter_file = RAW_COUNT_FILE

    def _get_current_date(self):
        return datetime.now().strftime("%Y%m%d")

    def _load_counter_data(self):
        try:
            if self.counter_file.exists():
                with open(self.counter_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("date") == self._get_current_date():
                        return data
            return {"date": self._get_current_date(), "count": 0}
        except Exception as e:
            logger.error(f"Error loading counter data: {e}")
            return {"date": self._get_current_date(), "count": 0}

    def _save_counter_data(self, data):
        try:
            with open(self.counter_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving counter data: {e}")
            return False

    def get_next_number(self):
        try:
            data = self._load_counter_data()
            current_date = self._get_current_date()

            if data.get("date") != current_date:
                data = {"date": current_date, "count": 0}

            data["count"] += 1
            next_number = data["count"]

            if self._save_counter_data(data):
                logger.info(f"Current count: {next_number:06d} (Date: {current_date})")
                return next_number
            else:
                logger.error("Failed to save counter, using default value 1")
                return 1
        except Exception as e:
            logger.error(f"Error getting next number: {e}")
            return 1

    def get_current_info(self):
        data = self._load_counter_data()
        return {
            "date": data.get("date", "None"),
            "count": data.get("count", 0),
            "next_number": data.get("count", 0) + 1,
        }


class RawDataConverter:
    def __init__(self):
        self.temp_dir = (
            Path(QStandardPaths.writableLocation(QStandardPaths.TempLocation))
            / "raw_temp"
        )
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.base_dir = Path(cfg.get(cfg.raw_data_path))
        self.counter_manager = CounterManager()
        self.current_file = None
        self.raw_queue = Queue()
        self.process_thread = threading.Thread(target=self.process_queue, daemon=True)
        self._raw_model = cfg.get(cfg.raw_upload_mode)
        self._is_running = False

    def _generate_filename(self):
        try:
            today = datetime.now().strftime("%Y%m%d")
            next_number = self.counter_manager.get_next_number()
            filename = f"{today}{next_number:06d}.raw"
            full_path = self.temp_dir / filename
            return full_path
        except Exception as e:
            logger.error(f"Error generating filename: {e}")
            return self.temp_dir / "backup.raw"

    def convert_to_raw(self, input_data):
        try:
            logger.info(f"开始转换RAW数据，输入数据keys: {list(input_data.keys())}")
            output_lines = []

            check_date = None
            check_time = None

            for slot_id in range(1, 9):
                processed_fields = []

                # 支持整数key和字符串key两种格式
                if slot_id in input_data.keys() or str(slot_id) in input_data.keys():
                    # 优先使用整数key，如果没有则使用字符串key
                    processed_data = input_data.get(slot_id) or input_data.get(
                        str(slot_id)
                    )
                    logger.info(
                        f"Slot {slot_id}: 找到数据，字段数={len(processed_data)}"
                    )
                    if check_date is None and check_time is None:
                        # 提取日期和时间用于后续记录
                        if len(processed_data) >= 5:
                            check_date = processed_data[3]
                            check_time = processed_data[4]
                            logger.info(
                                f"提取时间: date={check_date}, time={check_time}"
                            )
                else:
                    logger.info(f"Slot {slot_id}: 未找到数据，生成默认记录")
                    if int(cfg.get(cfg.station_code)) in [103, 106, 112]:
                        record = AOI_SPI(
                            line_name=cfg.get(cfg.line_name),
                            station_code=f"SPI-{cfg.get(cfg.station_code)}",
                            Slot_id=slot_id,
                            record_time=datetime.now(),
                        )
                    else:
                        record = ReflowOven(
                            line_name=cfg.get(cfg.line_name),
                            station_code=f"Reflow-{cfg.get(cfg.station_code)}",
                            Slot_id=slot_id,
                            record_time=datetime.now(),
                        )
                    processed_data = record.raw_data
                    if check_date and check_time:
                        processed_data[3] = check_date
                        processed_data[4] = check_time

                for value in processed_data:
                    if not value or value in ("NULL", '""', "''"):
                        processed_fields.append("NULL")
                    else:
                        processed_fields.append(value)

                output_lines.append(processed_fields)

            logger.info(f"RAW数据转换完成，总共生成 {len(output_lines)} 行数据")
            return output_lines

        except Exception as e:
            logger.error(f"Error converting data: {e}", exc_info=True)
            return None

    def save_raw_data(self, input_data):
        try:
            raw_data = self.convert_to_raw(input_data)

            if not raw_data:
                logger.error("Error: No valid data to save")
                return None

            filepath = self._generate_filename()

            with open(filepath, "w", encoding="utf-8") as f:
                writer = csv.writer(f, delimiter="\t", lineterminator="\n")
                for row in raw_data:
                    writer.writerow(row)

            logger.info(f"Data successfully saved to: {filepath}")
            logger.info(f"File size: {len(raw_data)} bytes")

            current_info = self.counter_manager.get_current_info()
            logger.info(
                f"Counter status - Date: {current_info['date']}, Current count: {current_info['count']:06d}"
            )

            return filepath
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            return None

    def process_queue(self):
        while self._is_running:
            input_data = self.raw_queue.get()
            if not input_data:
                break
            try:
                self.current_file = self.save_raw_data(input_data)
                self.mv_raw_file()
            except Exception as e:
                logger.error(f"Error processing queue: {e}")
        self._is_running = False

    def start(self):
        if self._is_running:
            logger.warning("RAW data processing thread is already running")
            return
        if not cfg.get(cfg.raw_upload_mode):
            logger.info("RAW upload mode is disabled, skipping start")
            return
        if not self.process_thread.is_alive():
            logger.info("Starting RAW data processing thread")
            self._is_running = True
            self.process_thread.start()

    def stop(self):
        logger.info("Stopping RAW data processing thread")
        self._is_running = False
        self.raw_queue.put(None)
        # 只有在线程已经启动时才调用 join()
        if self.process_thread.is_alive():
            self.process_thread.join(timeout=5)
            if self.process_thread.is_alive():
                logger.warning("RAW data processing thread did not exit cleanly")

    @property
    def is_running(self) -> bool:
        return self._is_running

    def mv_raw_file(self):
        """将当前RAW文件移动到目标文件夹"""
        try:
            if self.current_file and self.current_file.exists():
                target_path = self.base_dir / self.current_file.name
                self.base_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(self.current_file, target_path)
                logger.info(f"File moved to: {target_path}")
                self.current_file = None
                return target_path
            else:
                logger.warning("No RAW file to move")
                return None
        except Exception as e:
            logger.error(f"Error moving RAW file: {e}")
            return None


raw_manager = RawDataConverter()


def show_counter_status():
    """显示当前计数器状态"""
    counter_manager = CounterManager()
    info = counter_manager.get_current_info()
    print(f"\n=== 计数器状态 ===")
    print(f"当前日期: {info['date']}")
    print(f"当前计数: {info['count']:06d}")
    print(f"下一个编号: {info['next_number']:06d}")
    print(f"计数器文件: {counter_manager.counter_file}")


def reset_counter():
    """重置计数器（仅用于测试）"""
    counter_manager = CounterManager()
    data = {"date": counter_manager._get_current_date(), "count": 0}
    if counter_manager._save_counter_data(data):
        print("计数器已重置为0")
    else:
        print("重置计数器失败")


def main():
    """主函数：从标准输入读取数据并保存"""
    print("=== RAW数据转换器 (Windows版本) ===")
    print("正在初始化...")

    # 显示计数器状态
    show_counter_status()

    # 创建转换器实例
    converter = RawDataConverter()

    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        # 如果提供了文件路径作为参数
        input_file = sys.argv[1]
        try:
            print(f"正在读取文件: {input_file}")
            with open(input_file, "r", encoding="utf-8") as f:
                input_data = f.read()
        except Exception as e:
            print(f"读取文件时出错: {e}")
            return
    else:
        # 从标准输入读取数据
        print("请输入数据（输入完成后按Ctrl+Z然后回车结束输入）:")
        input_data = sys.stdin.read()

    if not input_data.strip():
        print("错误：没有输入数据")
        return

    print("正在处理数据...")
    # 保存数据
    result = converter.save_raw_data(input_data)

    if result:
        print("处理完成！")
    else:
        print("处理失败！")


def process_example():
    """处理示例数据"""
    print("=== 处理示例数据 ===")
    converter = RawDataConverter()

    # 示例数据
    data = "AOI;1;1;2025/11/5;9:03:44;G5YHLN0021R000166R;12.556;12.556;NULL;NULL;NULL;11;1;NULL;NULL;33;1;NULL;NULL;55;1;66;1;77;1;88;1;99;1;NULL;NULL;111;1;NULL;NULL"

    data = [
        [
            "AOI",
            "1",
            "1",
            "2025/11/5",
            "9:03:44",
            "G5YHLN0021R000166R",
            "12.556",
            "12.556",
            "NULL",
            "NULL",
        ],
        [
            "AOI",
            "2",
            "1",
            "2025/11/5",
            "9:03:44",
            "G5YHLN0021R000166R",
            "12.556",
            "12.556",
            "NULL",
            "NULL",
        ],
        [
            "AOI",
            "3",
            "1",
            "2025/11/5",
            "9:03:44",
            "G5YHLN0021R000166R",
            "12.556",
            "12.556",
            "NULL",
            "NULL",
        ],
        [
            "AOI",
            "4",
            "1",
            "2025/11/5",
            "9:03:44",
            "G5YHLN0021R000166R",
            "12.556",
            "12.556",
            "NULL",
            "NULL",
        ],
    ]

    print("示例数据:")
    print(data)
    print("\n正在转换并保存...")

    result = converter.save_raw_data(data)

    if result:
        print("示例数据处理完成！")
    else:
        print("示例数据处理失败！")


if __name__ == "__main__":
    print("RAW数据转换器 - Windows版本")
    print("使用方法:")
    print("1. 直接运行: python raw_data_converter.py")
    print("2. 处理文件: python raw_data_converter.py 文件名.txt")
    print("3. 运行示例: python raw_data_converter.py -example")
    print("4. 查看状态: python raw_data_converter.py -status")
    print("5. 重置计数: python raw_data_converter.py -reset")
    print("-" * 50)

    if len(sys.argv) > 1:
        if sys.argv[1] == "-example":
            process_example()
        elif sys.argv[1] == "-status":
            show_counter_status()
        elif sys.argv[1] == "-reset":
            reset_counter()
        else:
            main()
    else:
        main()

    # 暂停，让用户看到结果
    input("\n按回车键退出...")
