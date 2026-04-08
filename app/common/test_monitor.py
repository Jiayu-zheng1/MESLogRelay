from pathlib import Path
import time
from queue import Queue
from threading import Thread

from watchdog.observers import Observer

from app.components.handler import EventHandler_AOI_SPI
from app.parsers.parse_spi_csv import parse_log_file
from app.parsers.parse_reflow_oven import parse_log_file_reflow
from app.common.database import AOI_SPI as AOI_SPI_Model, ReflowOven as ReflowOven_Model
from app.common.sfc import SFCMonitor, sfc
from app.common.signal_bus import signalBus
from app.common.config import cfg
from app.components.raw_data_converter import raw_manager
from datetime import datetime
from app.common.logger import Logger
from version import get_version


logger = Logger("TestMonitor")


class TestMonitor:
    def __init__(self):
        logger.info(f"Init TestMonitor")
        self.is_running = False

        self.sfc_monitor = SFCMonitor(sfc)

        self.event_queue = Queue()
        self.state_queue = Queue()

        # 使用标准Observer
        self.observer = Observer()

        self.result_queue = Queue()

        self.event_handler = EventHandler_AOI_SPI(self.event_queue, self.state_queue)

    def _setup_observer(self):
        """配置Observer和事件处理器"""
        logger.info("Setting up Observer and Event Handler")
        self.observer.schedule(
            self.event_handler, cfg.get(cfg.monitor_path), recursive=True
        )
        print("Observer scheduled for path:", cfg.get(cfg.monitor_path))

    def _setup_threads(self):
        """配置解析和结果处理线程"""
        logger.info("Setting up Parse and Get Result Threads")
        self.parse_thread = Thread(target=self.parse_task, daemon=True)
        self.get_result_thread = Thread(target=self.get_result, daemon=True)

    def check_monitor_path(self):
        """检查监控路径是否配置正确"""
        logger.info("Checking monitor path configuration")
        errors = cfg.validate_settings()

        if errors.get("monitor_path"):
            error_msg = errors["monitor_path"]
            if "not configured" in error_msg:
                raise ValueError(error_msg)
            else:
                raise FileNotFoundError(error_msg)

        monitor_path = cfg.get(cfg.monitor_path)
        logger.info(f"Monitor path set to: {monitor_path}")

    def stop(self):
        """停止Observer和相关监控"""
        logger.info("Stopping TestMonitor")
        self.is_running = False

        try:
            # 停止 Observer
            self.observer.stop()
            # 停止 SFC 监控
            self.sfc_monitor.stop()
            self.event_queue.put_nowait(None)
            self.result_queue.put_nowait(None)
        except Exception:
            pass

        # 等待 Observer 退出
        if self.observer.is_alive():
            self.observer.join(timeout=5)

        # 等待解析线程退出
        if hasattr(self, "parse_thread") and self.parse_thread.is_alive():
            self.parse_thread.join(timeout=5)
            if self.parse_thread.is_alive():
                logger.warning("Parse thread did not exit cleanly")

        # 等待结果处理线程退出
        if hasattr(self, "get_result_thread") and self.get_result_thread.is_alive():
            self.get_result_thread.join(timeout=5)
            if self.get_result_thread.is_alive():
                logger.warning("Get result thread did not exit cleanly")

    def start(self):
        """启动Observer和解析线程"""
        logger.info("Starting TestMonitor")
        self.is_running = True
        self.sfc_monitor.start()
        self.observer.start()
        self.parse_thread.start()
        self.get_result_thread.start()

    def parse_task(self):
        """解析文件任务，从事件队列获取文件并处理"""
        logger.info("Parse task started")

        items = None

        while self.is_running:
            file_path = self.event_queue.get()  # 阻塞等待
            if file_path is None:  # 退出线程
                logger.info("Parse task exited")
                break

            logger.info(f"Processing file: {file_path}")
            try:
                if int(cfg.get(cfg.station_code)) in (109, 122):  # 炉温站别
                    time.sleep(2)  # 等待文件完全写入
                    items = parse_log_file_reflow(file_path)
                    if items and items.InTime is None:
                        logger.warning(
                            "InTime is None, waiting 2 seconds and retrying..."
                        )
                        time.sleep(2)
                        items = parse_log_file_reflow(file_path)  # 再试一次
                    if not items:
                        logger.error(
                            f"Failed to parse reflow log file Because Result is None: {file_path}"
                        )
                    else:
                        self.result_queue.put(items)

                else:
                    time.sleep(2)  # AOI/SPI站别
                    items = parse_log_file(file_path)
                    if not items:
                        logger.error(
                            f"Failed to parse AOI/SPI log file Because Result is None: {file_path}"
                        )
                    else:
                        self.result_queue.put(items)

            except Exception as e:
                logger.error(f"Error parsing file {file_path}: {e}")

    def get_result(self):
        while self.is_running:
            try:
                items = self.result_queue.get()
                if items is None:
                    logger.info("Get result task exited")
                    break

                if int(cfg.get(cfg.station_code)) in (109, 122):  # 炉温站别
                    self._handle_reflow_result(items)
                else:  # AOI/SPI站别
                    self._handle_aoi_spi_result(items)
            except Exception as e:
                logger.error(f"Error getting result from queue: {e}")

    def _handle_aoi_spi_result(self, items):
        """
        处理 AOI/SPI 测试结果

        Args:
            items: 槽位数据列表，每次测试生成 8 条记录（8 连板）
        """
        try:
            # 检查输入数据
            if not items or len(items) == 0:
                logger.warning("AOI/SPI result is empty")
                return

            # 获取 Panel SN (所有 item 的 Barcode 应该相同)
            panel_serial_number = items[0].get("Barcode", "N/A")
            logger.info(
                f"[AOI/SPI Mode] Processing result: Panel SN={panel_serial_number}, 共 {len(items)} 个槽位"
            )

            # 检查数据库中是否已存在该连板SN的记录
            existing_record = (
                AOI_SPI_Model.select()
                .where(AOI_SPI_Model.panel_sn == panel_serial_number)
                .first()
            )

            # if existing_record:
            #     logger.warning(
            #         f"[AOI/SPI Mode] Panel SN={panel_serial_number} already exists in database, skipping..."
            #     )
            #     return

            # 从 SFC 获取该连板下的所有单板序列号（一次性获取 8 个）
            serial_numbers, panel_SN = sfc.get_SN(panel_serial_number)
            if not serial_numbers:
                logger.warning(
                    f"[AOI/SPI Mode] Failed to get serial numbers from SFC for panel SN: {panel_serial_number}"
                )
                return

            logger.info(f"[AOI/SPI Mode] Got serial numbers from SFC: {serial_numbers}")

            # 清空UI状态表格
            signalBus.clearStatusTableSig.emit()

            # 收集原始数据用于上传（只收集当前站点的数据）
            raw_data = {}

            # 遍历每个槽位
            for item in items:
                result = item.get("Result", "")
                # 将 slot_id 转换为整数以匹配 SFC 返回的字典键
                sn_info = serial_numbers.get(int(item.get("BoardNo", "")))
                if sn_info is None:
                    logger.warning(
                        f"[AOI/SPI Mode] No serial number for slot {item.get('BoardNo', '')}"
                    )
                    continue

                mlb_serial_number = sn_info[0]  # 取单板SN
                route = sn_info[1] if len(sn_info) > 1 else None  # 取路由信息

                # 将单板 SN 添加到 item 字典中
                item["single_SN"] = mlb_serial_number

                logger.info(
                    f"[AOI/SPI Mode] Processing slot {item.get('BoardNo', '')}: SN={mlb_serial_number}, Route={route}, Result={item.get('Result', '')}"
                )

                if item.get("measurements"):
                    item = self.limits_check(item)
                    print("after limits_check:", item)

                # 创建数据库记录对象
                aoi_spi_record = AOI_SPI_Model(
                    line_name=item.get("Job", ""),
                    product_name="Moose",
                    slot_id=item.get("BoardNo", ""),
                    station_code=cfg.get(cfg.station_code),
                    serial_number=mlb_serial_number,
                    single_SN=mlb_serial_number,  # 保存单板SN
                    panel_sn=panel_SN,
                    result=result,
                    flags=result,
                    bot_or_top=cfg.get(cfg.face),
                    version=get_version(),
                    test_time=item.get("Time", ""),
                    sfc_result=route if route else "OK",
                    failed_components=item.get("failed_components"),  # 不良元件位置
                    failed_cause=item.get("failed_cause"),  # 不良原因
                    failed_pid=item.get("failed_pid"),  # PAD ID
                )

                # 如果有测量数据，添加到记录中
                measurements = item.get("measurements")
                if measurements:
                    # measurements 格式: {Component_ID: {Volume_percent: [...], ...}}
                    aoi_spi_record.measurements = measurements
                    logger.info(
                        f"[AOI/SPI Mode] Slot {item.get('BoardNo', '')} has measurement data: {list(measurements.keys())}"
                    )

                # 保存到数据库
                aoi_spi_record.save()
                logger.info(
                    f"[AOI/SPI Mode] ✓ Record saved: Slot={item.get('BoardNo', '')}, SN={mlb_serial_number}, Route={route}"
                )

                if route == "OK":
                    raw_data[item.get("BoardNo", "")] = aoi_spi_record.raw_data

                    logger.info(
                        f"[AOI/SPI Mode] ✓ Added to raw_data: Slot={item.get('BoardNo', '')}"
                    )
                else:
                    logger.info(
                        f"[AOI/SPI Mode] ✗ Not at current station, skipping raw_data: Slot={item.get('BoardNo', '')}, Route={route}"
                    )

                # 发送UI信号显示在表格中（所有记录都显示）
                signalBus.addStatusRowSig.emit(aoi_spi_record)

            # # 如果有单板在当前站点，则生成raw文件
            if raw_data:
                raw_manager.raw_queue.put(raw_data)
                logger.info(
                    f"[AOI/SPI Raw Data] ✓ {len(raw_data)} records queued for RAW file generation"
                )
            else:
                logger.warning(
                    "[AOI/SPI Raw Data] ✗ No boards at current station, skipping RAW file generation"
                )

        except Exception as e:
            logger.exception(f"Error handling AOI/SPI result: {e}")

    def limits_check(self, item):
        """对测量数据进行上下限检查，更新结果字段和失败零件名称（只记录第一个不良）"""
        measurements = item.get("measurements", {})
        volume_upper = cfg.get(cfg.Volume_upper)
        volume_lower = cfg.get(cfg.Volume_lower)
        offsetX_upper = cfg.get(cfg.OffsetX_upper)
        offsetX_lower = cfg.get(cfg.OffsetX_lower)
        offsetY_upper = cfg.get(cfg.OffsetY_upper)
        offsetY_lower = cfg.get(cfg.OffsetY_lower)

        # 初始化 item 中的 failed_cause 列表

        item["failed_cause"] = []
        item["failed_components"] = []
        item["failed_pid"] = []

        # 分别存储失败信息
        failed_components = None  # 不良元件位置，如 J0100
        failed_cause = None  # 不良原因，如 Volume_Upper, OffsetX
        failed_pid = None  # PAD ID
        found_defect = False  # 标志是否已找到不良

        for component_id, measures in measurements.items():
            # if found_defect:  # 如果已找到不良，跳出外层循环
            #     break

            # 提取零件名称（去掉槽位号，如 J0100_7 -> J0100）
            component_name = (
                component_id.rsplit("_", 1)[0] if "_" in component_id else component_id
            )

            # 获取 PIDs 列表
            pids = measures.get("PIDs", [])

            # 检查 Volume_percent
            volume_values = measures.get("Volume_percent", [])
            for idx, value in enumerate(volume_values):
                try:
                    val = float(value)
                    pid = pids[idx] if idx < len(pids) else ""
                    if volume_upper and val > float(volume_upper):
                        failed_components = component_name
                        failed_cause = volume_values
                        failed_pid = pid

                        item["failed_components"].append(failed_components)
                        item["failed_cause"].append(val)
                        item["failed_pid"].append(failed_pid)

                        logger.warning(
                            f"[Limits Check] {component_id} PID={pid} Volume={val} exceeds upper limit {volume_upper}"
                        )
                        found_defect = True
                        break
                    if volume_lower and val < float(volume_lower):
                        failed_components = component_name
                        failed_cause = volume_values
                        failed_pid = pid

                        item["failed_components"].append(failed_components)
                        item["failed_cause"].append(val)
                        item["failed_pid"].append(failed_pid)

                        logger.warning(
                            f"[Limits Check] {component_id} PID={pid} Volume={val} below lower limit {volume_lower}"
                        )
                        found_defect = True
                        break
                except ValueError:
                    continue

            # if found_defect:  # 找到不良后跳出
            #     break

            # 检查 OffsetX_percent
            offsetX_values = measures.get("OffsetX_percent", [])
            for idx, value in enumerate(offsetX_values):
                try:
                    val = float(value)
                    pid = pids[idx] if idx < len(pids) else ""
                    if offsetX_upper and val > float(offsetX_upper):
                        failed_components = component_name
                        failed_cause = offsetX_values
                        failed_pid = pid

                        item["failed_components"].append(failed_components)
                        item["failed_cause"].append(val)
                        item["failed_pid"].append(failed_pid)

                        logger.warning(
                            f"[Limits Check] {component_id} PID={pid} OffsetX={val} exceeds upper limit {offsetX_upper}"
                        )
                        found_defect = True
                        break
                    if offsetX_lower and val < float(offsetX_lower):
                        failed_components = component_name
                        failed_cause = offsetX_values
                        failed_pid = pid

                        item["failed_components"].append(failed_components)
                        item["failed_cause"].append(val)
                        item["failed_pid"].append(failed_pid)

                        logger.warning(
                            f"[Limits Check] {component_id} PID={pid} OffsetX={val} below lower limit {offsetX_lower}"
                        )
                        found_defect = True
                        break
                except ValueError:
                    continue

            # if found_defect:  # 找到不良后跳出
            #     break

            # 检查 OffsetY_percent
            offsetY_values = measures.get("OffsetY_percent", [])
            for idx, value in enumerate(offsetY_values):
                try:
                    val = float(value)
                    pid = pids[idx] if idx < len(pids) else ""
                    if offsetY_upper and val > float(offsetY_upper):
                        failed_components = component_name
                        failed_cause = offsetY_values
                        failed_pid = pid

                        item["failed_components"].append(failed_components)
                        item["failed_cause"].append(val)
                        item["failed_pid"].append(failed_pid)
                        logger.warning(
                            f"[Limits Check] {component_id} PID={pid} OffsetY={val} exceeds upper limit {offsetY_upper}"
                        )
                        found_defect = True
                        break
                    if offsetY_lower and val < float(offsetY_lower):
                        failed_components = component_name
                        failed_cause = offsetY_values
                        failed_pid = pid

                        item["failed_components"].append(failed_components)
                        item["failed_cause"].append(val)
                        item["failed_pid"].append(failed_pid)
                        logger.warning(
                            f"[Limits Check] {component_id} PID={pid} OffsetY={val} below lower limit {offsetY_lower}"
                        )
                        found_defect = True
                        break
                except ValueError:
                    continue

            # if found_defect:  # 找到不良后跳出
            #     break

        # 如果有零件失败，更新结果（只记录第一个）
        if found_defect:
            item["Result"] = "FAIL"
            # item["failed_components"] = failed_components  # 不良元件位置，如 J0100
            # item["failed_cause"] = failed_cause  # 不良原因，如 Volume_Upper
            # item["failed_pid"] = failed_pid  # PAD ID
            logger.info(
                f"[Limits Check] Test result set to FAIL - Components: {failed_components}, Cause: {failed_cause}, PID: {failed_pid}"
            )

        return item

    def _handle_reflow_result(self, items):
        try:
            # 检查输入数据
            if items is None:
                logger.warning("Reflow result is None")
                return

            # 炉温的序列号是连板SN，需要从SFC获取单板SN
            Log_SN = items.serial_number if items else "N/A"
            logger.info(f"[ReflowMode] Processing result: Log SN={Log_SN}")

            # 从 SFC 获取该连板下的所有单板序列号
            result_dict = sfc.get_SN(Log_SN)

            if not result_dict.get("single_SN"):
                logger.warning(
                    f"[ReflowMode] Failed to get single_SN from SFC for log SN: {Log_SN}"
                )
                return

            logger.info(f"[ReflowMode] Got single_SN from SFC: {Log_SN}")
            serial_numbers = result_dict.get("single_SN", {})
            panel_SN = result_dict.get("panle_SN", "N/A")
            box_SN = result_dict.get("box_SN", "N/A")

            # 清空UI状态表格
            signalBus.clearStatusTableSig.emit()

            # 收集原始数据用于上传
            raw_data = {}
            for slot_id, sn_info in serial_numbers.items():
                if sn_info is None:
                    logger.warning(f"[ReflowMode] No serial number for slot {slot_id}")
                    continue

                mlb_serial_number = sn_info[0]  # 取单板SN
                route = sn_info[1] if len(sn_info) > 1 else None  # 取路由信息

                logger.info(
                    f"[ReflowMode] Processing slot {slot_id}: SN={mlb_serial_number}, Route={route}"
                )

                # 创建数据库记录对象
                reflow_record = ReflowOven_Model(
                    line_name=items.line_name,
                    product_name=items.product_name,
                    Slot_id=slot_id,
                    station_code=items.station_code,
                    serial_number=mlb_serial_number,
                    panel_sn=panel_SN,
                    carrier_No=box_SN,  # 载具编号
                    result=items.sfc_result.value if items.sfc_result else "PASS",
                    version=getattr(items, "version", None),
                    InTime=items.InTime,
                    OutTime=items.OutTime,
                    single_ct=self._calculate_single_ct(items.InTime, items.OutTime),
                    O2=items.O2,
                    Motor_UpHeat=items.Motor_UpHeat,
                    Motor_DnHeat=items.Motor_DnHeat,
                    Motor_UpWeld=items.Motor_UpWeld,
                    Motor_DnWeld=items.Motor_DnWeld,
                    Motor_Cooling=items.Motor_Cooling,
                    SetConveyorSpeed=items.SetConveyorSpeed,
                    ConveyorSpeed=items.ConveyorSpeed,
                    ExternalTemp=items.ExternalTemp,
                    sfc_result=route if route else "OK",
                )

                for i in range(1, 14):
                    idx = str(i).zfill(2)

                    # 设定温度属性名
                    set_top_attr = f"SetTopZoneT{idx}"
                    set_bottom_attr = f"SetBottomZoneT{idx}"
                    # 实际温度属性名
                    top_attr = f"TopZoneT{idx}"
                    bottom_attr = f"BottomZoneT{idx}"

                    val = getattr(items, set_top_attr, None)
                    if val is None:
                        val = getattr(items, f"SetTopZoneT{i}", None)
                    setattr(reflow_record, set_top_attr, val)

                    val = getattr(items, set_bottom_attr, None)
                    if val is None:
                        val = getattr(items, f"SetBottomZoneT{i}", None)
                    setattr(reflow_record, set_bottom_attr, val)

                    val = getattr(items, top_attr, None)
                    if val is None:
                        val = getattr(items, f"TopZoneT{i}", None)
                    setattr(reflow_record, top_attr, val)

                    val = getattr(items, bottom_attr, None)
                    if val is None:
                        val = getattr(items, f"BottomZoneT{i}", None)
                    setattr(reflow_record, bottom_attr, val)

                # 赋值 MaxRiseSlope / MaxFallSlope / Peak 上下限
                reflow_record.MaxRiseSlope_upper = getattr(
                    items, "MaxRiseSlope_upper", None
                )
                reflow_record.MaxRiseSlope_lower = getattr(
                    items, "MaxRiseSlope_lower", None
                )
                reflow_record.MaxFallSlope_upper = getattr(
                    items, "MaxFallSlope_upper", None
                )
                reflow_record.MaxFallSlope_lower = getattr(
                    items, "MaxFallSlope_lower", None
                )
                reflow_record.Peak_Temp_upper = getattr(items, "Peak_Temp_upper", None)
                reflow_record.Peak_Temp_lower = getattr(items, "Peak_Temp_lower", None)

                # 赋值 T2~T10 实测值
                for tc_n in range(2, 11):
                    tc = f"T{tc_n}"
                    setattr(
                        reflow_record,
                        f"{tc}_RiseSlope",
                        getattr(items, f"{tc}_RiseSlope", None),
                    )
                    setattr(
                        reflow_record,
                        f"{tc}_FallSlope",
                        getattr(items, f"{tc}_FallSlope", None),
                    )
                    setattr(
                        reflow_record,
                        f"{tc}_Peak_Temp",
                        getattr(items, f"{tc}_Peak_Temp", None),
                    )

                # 保存到数据库
                reflow_record.save()
                logger.info(
                    f"[ReflowMode] ✓ Record saved: Slot={slot_id}, SN={mlb_serial_number}, Route={route}"
                )

                # 只有在当前站点(route=="OK")的单板才收集原始数据用于生成RAW文件
                if route == "OK":
                    raw_data[slot_id] = reflow_record.raw_data
                    logger.info(f"[ReflowMode] ✓ Added to raw_data: Slot={slot_id}")
                else:
                    logger.info(
                        f"[ReflowMode] ✗ Not at current station, skipping raw_data: Slot={slot_id}, Route={route}"
                    )

                # 发送UI信号显示在表格中（所有记录都显示）
                signalBus.addStatusRowSig.emit(reflow_record)

            # 如果有单板在当前站点，则生成raw文件
            if raw_data:
                print("生成RAW文件的原始数据:")
                raw_manager.raw_queue.put(raw_data)
                self.move_file_to_processed(items.log_file_path)
                logger.info(
                    f"[Raw Data setting] ✓ {len(raw_data)} records queued for RAW file generation"
                )
            else:
                logger.warning(
                    "[Raw Data setting] ✗ No boards at current station, skipping RAW file generation"
                )

        except Exception as e:
            logger.exception(f"Error getting Reflow result: {e}")

    def _calculate_single_ct(self, InTime, OutTime) -> str:
        """计算单板CT: (出板时间 - 进板时间) 转为秒数 / 8

        支持两种时间格式:
        1. YYYY/MM/DD HH:MM:SS (完整日期时间)
        2. HH:MM:SS (仅时间)
        """

        try:
            in_time_str = str(InTime).strip()
            out_time_str = str(OutTime).strip()

            # 尝试解析完整的日期时间格式 (YYYY/MM/DD HH:MM:SS)
            try:
                in_time_obj = datetime.strptime(in_time_str, "%Y/%m/%d %H:%M:%S")
                out_time_obj = datetime.strptime(out_time_str, "%Y/%m/%d %H:%M:%S")
            except ValueError:
                # 如果完整格式解析失败，尝试仅时间格式 (HH:MM:SS)
                in_time_obj = datetime.strptime(in_time_str, "%H:%M:%S")
                out_time_obj = datetime.strptime(out_time_str, "%H:%M:%S")

            # 计算时间差（秒数）
            time_diff_seconds = (out_time_obj - in_time_obj).total_seconds()

            # 如果时间差为负（跨越午夜），添加86400秒（24小时）
            if time_diff_seconds < 0:
                time_diff_seconds += 86400

            # 除以8得到单板CT
            single_ct = time_diff_seconds / 8

            # 保留3位小数
            return f"{single_ct:.3f}"
        except Exception as e:
            return "NULL"

    def move_file_to_processed(self, file_path: str):
        """将处理过的文件移动到备份文件夹"""
        try:
            # 检查源文件是否存在
            source_file = Path(file_path)
            if not source_file.exists():
                logger.warning(
                    f"Source file does not exist, skipping move: {file_path}"
                )
                return

            # 获取监控路径
            monitor_path = Path(cfg.get(cfg.monitor_path))
            # 获取监控文件夹的名字
            monitor_folder_name = monitor_path.name
            # 在监控路径的父级建立 监控文件夹名-backup 的文件夹
            backup_dir = monitor_path.parent / f"{monitor_folder_name}-backup"
            backup_dir.mkdir(exist_ok=True)
            year_dir = backup_dir / datetime.now().strftime("%Y")
            year_dir.mkdir(exist_ok=True)
            year_month_dir = year_dir / datetime.now().strftime("%m")
            year_month_dir.mkdir(exist_ok=True)
            day_dir = year_month_dir / datetime.now().strftime("%d")
            day_dir.mkdir(exist_ok=True)

            dest_path = day_dir / source_file.name
            source_file.rename(dest_path)
            logger.info(f"Moved processed file to backup: {dest_path}")
        except Exception as e:
            logger.error(f"Error moving file {file_path} to backup folder: {e}")


if __name__ == "__main__":
    monitor = TestMonitor()

    monitor.start()
    logger.info("FileMonitor started")
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break
    logger.info("FileMonitor stopped")
    monitor.stop()
