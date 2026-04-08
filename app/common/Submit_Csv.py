"""
CSV数据存储模块
用于将测试数据保存到本地CSV文件
"""

import csv
from pathlib import Path
from datetime import datetime
from typing import Union, List
from app.common.logger import Logger
from app.common.const import APP_PATH
from app.common.config import cfg
from app.components.smb_mount import smb_mount_service


logger = Logger("Submit_Csv")


def get_field_display_name(field_name):
    """
    获取字段的显示名称（用于 CSV 表头）

    Args:
        field_name: 数据库字段名

    Returns:
        str: CSV 表头显示名称
    """
    field_mapping = {
        "result": "Pass_Fail_Station",
        "id": "Log_id",  # 将 result 显示为 Pass_Fail_Station
    }
    return field_mapping.get(field_name, field_name)


def get_ordered_headers(model_obj):
    """
    获取指定顺序的表头字段

    Args:
        model_obj: 数据模型对象

    Returns:
        list: 有序的字段名列表
    """
    # 检查模型类型
    model_class = type(model_obj).__name__

    # ReflowOven 的字段顺序 - 完整自定义顺序
    if model_class == "ReflowOven":
        ordered_headers = [
            "product_name",
            "line_name",
            "station_code",
            "serial_number",
            "panel_sn",
            "Slot_id",
            "upload_time",
            "record_time",
            "upload_status",
            "sfc_result",
            "result",
            "version",
            "id",
            "InTime",
            "OutTime",
            "single_ct",
            "O2",
            "Motor_UpHeat",
            "Motor_DnHeat",
            "Motor_UpWeld",
            "Motor_DnWeld",
            "Motor_Cooling",
            "SetConveyorSpeed",
            "ConveyorSpeed",
            "ExternalTemp",
            "SetTopZoneT01",
            "SetTopZoneT02",
            "SetTopZoneT03",
            "SetTopZoneT04",
            "SetTopZoneT05",
            "SetTopZoneT06",
            "SetTopZoneT07",
            "SetTopZoneT08",
            "SetTopZoneT09",
            "SetTopZoneT10",
            "SetTopZoneT11",
            "SetTopZoneT12",
            "SetTopZoneT13",
            "TopZoneT01",
            "TopZoneT02",
            "TopZoneT03",
            "TopZoneT04",
            "TopZoneT05",
            "TopZoneT06",
            "TopZoneT07",
            "TopZoneT08",
            "TopZoneT09",
            "TopZoneT10",
            "TopZoneT11",
            "TopZoneT12",
            "TopZoneT13",
            "SetBottomZoneT01",
            "SetBottomZoneT02",
            "SetBottomZoneT03",
            "SetBottomZoneT04",
            "SetBottomZoneT05",
            "SetBottomZoneT06",
            "SetBottomZoneT07",
            "SetBottomZoneT08",
            "SetBottomZoneT09",
            "SetBottomZoneT10",
            "SetBottomZoneT11",
            "SetBottomZoneT12",
            "SetBottomZoneT13",
            "BottomZoneT01",
            "BottomZoneT02",
            "BottomZoneT03",
            "BottomZoneT04",
            "BottomZoneT05",
            "BottomZoneT06",
            "BottomZoneT07",
            "BottomZoneT08",
            "BottomZoneT09",
            "BottomZoneT10",
            "BottomZoneT11",
            "BottomZoneT12",
            "BottomZoneT13",
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

        # 返回所有字段（保持顺序），即使某些字段值为 None
        return ordered_headers

    # AOI_SPI 的字段顺序
    elif model_class == "AOI_SPI":
        base_headers = [
            "upload_status",
            "record_time",
            "line_name",
            "product_name",
            "slot_id",
            "station_code",
            "serial_number",
            "panel_sn",
            "result",
        ]

        remaining_fields = [
            f for f in model_obj.__data__.keys() if f not in base_headers
        ]

        return base_headers + remaining_fields

    # Dispensing 的字段顺序
    elif model_class == "Dispensing":
        base_headers = [
            "upload_status",
            "record_time",
            "line_name",
            "product_name",
            "station_code",
            "serial_number",
            "panel_sn",
            "result",
        ]

        remaining_fields = [
            f for f in model_obj.__data__.keys() if f not in base_headers
        ]

        return base_headers + remaining_fields

    # 默认：使用原有顺序
    return list(model_obj.__data__.keys())


class CsvDataWriter:
    """CSV数据写入器，用于将测试数据保存到本地CSV文件"""

    def __init__(self, base_dir: str = None):
        """
        初始化CSV写入器

        Args:
            base_dir: CSV文件保存的基础目录，默认为 APP_PATH/CSV
        """
        if base_dir is None:
            # 使用与日志相同的基础路径
            base_dir = APP_PATH / "CSV"

        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"CSV数据存储目录: {self.base_dir}")

    def save_test_data(self, data, file_name):
        """
        将测试数据保存到CSV文件

        Args:
            data: 测试数据对象或对象列表 (支持 AOI_SPI, ReflowOven, Dispensing 等模型)
            file_name: CSV文件名

        Returns:
            bool: 保存成功返回True，失败返回False
        """
        try:
            # 如果传入的是单个对象，转换为列表
            if not isinstance(data, list):
                data = [data]

            if not data:
                logger.warning("数据为空，无需保存")
                return False

            # 获取第一个对象用于确定字段名
            first_obj = data[0]

            # 获取字段名（表头）
            if hasattr(first_obj, "to_dict"):
                # 如果对象有 to_dict 方法，使用它
                field_names = list(first_obj.to_dict().keys())
            elif hasattr(first_obj, "__dataclass_fields__"):
                # 如果是 dataclass，获取所有字段
                field_names = list(first_obj.__dataclass_fields__.keys())
            elif isinstance(first_obj, dict):
                # 如果是字典
                field_names = list(first_obj.keys())
            elif hasattr(first_obj, "__data__"):
                # 如果是 Peewee Model 对象，使用自定义顺序
                field_names = get_ordered_headers(first_obj)
            else:
                logger.error(f"不支持的数据类型: {type(first_obj)}")
                return False

            # 将字段名映射为显示名称（用于CSV表头）
            display_headers = [get_field_display_name(f) for f in field_names]

            # 生成文件名：前缀_YYYYMMDD.csv
            csv_filename = f"{file_name}"
            csv_filepath = self.base_dir / csv_filename

            # 检查文件是否存在，判断是否需要写入表头.
            file_exists = csv_filepath.exists()

            # 打开CSV文件，追加模式
            with open(csv_filepath, "a", newline="", encoding="utf-8-sig") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=display_headers)

                # 如果文件不存在或为空，写入表头
                if not file_exists or csvfile.tell() == 0:
                    writer.writeheader()
                    logger.info(f"创建新CSV文件并写入表头: {csv_filepath}")

                # 写入数据行
                for obj in data:
                    if hasattr(obj, "to_dict"):
                        row_data = obj.to_dict()
                    elif hasattr(obj, "__dataclass_fields__"):
                        row_data = {
                            field: getattr(obj, field, None) for field in field_names
                        }
                    elif isinstance(obj, dict):
                        row_data = obj
                    elif hasattr(obj, "__data__"):
                        # Peewee Model 对象
                        row_data = {}
                        for field in field_names:
                            value = getattr(obj, field, None)
                            # 处理datetime对象
                            if value is not None and hasattr(value, "strftime"):
                                value = value.strftime("%Y-%m-%d %H:%M:%S")
                            row_data[field] = value
                    else:
                        logger.warning(f"跳过不支持的对象类型: {type(obj)}")
                        continue

                    # 处理枚举类型
                    for key, value in row_data.items():
                        if hasattr(value, "value"):
                            row_data[key] = value.value

                    # 将原始字段名映射为显示字段名，保持字段顺序
                    mapped_row_data = {}
                    for field in field_names:
                        display_name = get_field_display_name(field)
                        mapped_row_data[display_name] = row_data.get(field)

                    writer.writerow(mapped_row_data)

                logger.info(f"成功保存 {len(data)} 条测试数据到: {csv_filepath}")

            return True

        except Exception as e:
            logger.error(f"保存CSV数据失败: {e}")
            return False

    def save_csv_data(self, data, file_name):
        """
        保存炉温测试数据到CSV

        Args:
            data: ReflowOven数据对象或对象列表

        Returns:
            bool: 保存成功返回True，失败返回False
        """
        return self.save_test_data(data, file_name)


# 创建全局CSV写入器实例
csv_writer = CsvDataWriter()


def save_to_csv(
    data: Union[object, List[object]], file_prefix: str = "test_data"
) -> bool:
    """
    便捷函数：保存测试数据到CSV文件

    Args:
        data: 测试数据对象或对象列表
        file_prefix: CSV文件名前缀

    Returns:
        bool: 保存成功返回True，失败返回False

    Example:
        >>> from app.common.Submit_Csv import save_to_csv
        >>> save_to_csv(aoi_spi_record, "aoi_spi_data")
        >>> save_to_csv([record1, record2], "reflow_data")
    """
    return csv_writer.save_test_data(data, file_prefix)


def _batch_save_to_csv_smb(record, filename):
    """SMB 远程保存 CSV（通过挂载方式）"""
    try:
        # 获取全局挂载管理器
        mount_manager = smb_mount_service.get_manager()

        if not mount_manager or not mount_manager.is_mounted:
            logger.warning("SMB is not mounted, skipping remote save")
            return

        # 构建远程路径
        remote_dir = cfg.get(cfg.smb_remote_path)
        remote_path = f"{remote_dir}/{cfg.get(cfg.station_code)}/CSV/{filename}"

        # 获取本地挂载路径
        file_path = mount_manager.get_local_path(remote_path)

        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 检查文件是否存在
        file_exists = file_path.exists() and file_path.stat().st_size > 0

        # 获取字段名（使用自定义顺序）
        if hasattr(record, "__data__"):
            field_names = get_ordered_headers(record)
        elif hasattr(record, "to_dict"):
            field_names = list(record.to_dict().keys())
        else:
            logger.error(f"不支持的数据类型: {type(record)}")
            return

        # 将字段名映射为显示名称（用于CSV表头）
        display_headers = [get_field_display_name(f) for f in field_names]

        # 使用标准文件 I/O 写入（性能更好）
        mode = "a" if file_exists else "w"
        with open(file_path, mode, newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=display_headers)

            # 只在文件不存在时写入表头
            if not file_exists:
                writer.writeheader()

            # 写入数据行
            if hasattr(record, "__data__"):
                row_data = {}
                for field in field_names:
                    value = getattr(record, field, None)
                    if value is not None and hasattr(value, "strftime"):
                        value = value.strftime("%Y-%m-%d %H:%M:%S")
                    row_data[field] = value
            elif hasattr(record, "to_dict"):
                row_data = record.to_dict()

            # 处理枚举类型
            for key, value in row_data.items():
                if hasattr(value, "value"):
                    row_data[key] = value.value

            # 将原始字段名映射为显示字段名，保持字段顺序
            mapped_row_data = {}
            for field in field_names:
                display_name = get_field_display_name(field)
                mapped_row_data[display_name] = row_data.get(field)

            writer.writerow(mapped_row_data)

        logger.info(
            f"{'Appended' if file_exists else 'Created and saved'} record to SMB CSV: {remote_path}"
        )

    except Exception as e:
        logger.error(f"Failed to save CSV to SMB: {e}", exc_info=True)
