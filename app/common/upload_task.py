import time
from datetime import datetime
from app.common.sfc import sfc
from app.common.signal_bus import signalBus
from app.common.enums import UploadStatus


from app.common.logger import Logger

logger = Logger("UploadTask")


def process_upload(record):
    """在线程池中处理上传任务"""

    if record.result == "UNTEST":
        signalBus.uploadStatusSig.emit(
            record, UploadStatus.UNTEST, "Record untested, skipping upload."
        )
        logger.info(f"记录未测试，跳过上传: SN={record.serial_number}")

        record.upload_status = UploadStatus.SKIP.value
        record.save()

        return record
    elif record.result == "SKIP":
        signalBus.uploadStatusSig.emit(
            record, UploadStatus.SKIP, "Record marked as SKIP, skipping upload."
        )
        logger.info(f"记录标记为跳过，跳过上传: SN={record.serial_number}")

        record.upload_status = UploadStatus.SKIP.value
        record.save()

        return record

    # UOP Check
    # signalBus.uploadStatusSig.emit(record, UploadStatus.CHECK_UOP, "Checking UOP route...")
    # uop_result = sfc.checkRoute(record.serial_number)
    # if 'OK' not in uop_result:
    #     signalBus.uploadStatusSig.emit(record, UploadStatus.UOP, uop_result)

    #     record.sfc_result = uop_result
    #     record.save()

    #     return record

    # 记录上传开始时间
    start_time = time.time()

    try:
        signalBus.uploadStatusSig.emit(
            record, UploadStatus.UPLOADING, "Uploading record..."
        )

        status = "PASS" in record.result
        sfc_result = sfc.add_record(record.serial_number, status)

        # 计算上传耗时
        elapsed = time.time() - start_time
        record.sfc_result = sfc_result

        if "OK" in sfc_result:
            record.upload_time = datetime.now()
            record.upload_status = UploadStatus.UPLOADED.value

            signalBus.uploadStatusSig.emit(
                record, UploadStatus.UPLOADED, "Record uploaded successfully."
            )
            logger.info(f"SFC上传成功: SN={record.serial_number}, 耗时={elapsed:.2f}秒")

        else:
            record.upload_status = UploadStatus.UPLOAD_FAILED.value

            signalBus.uploadStatusSig.emit(
                record, UploadStatus.UPLOAD_FAILED, sfc_result
            )
            logger.error(
                f"SFC上传失败: SN={record.serial_number}, 错误={sfc_result}, 耗时={elapsed:.2f}秒"
            )
    except Exception as e:
        logger.error(f"上传过程中出错: {e}")

        record.sfc_result = str(e)
        record.upload_status = UploadStatus.UPLOAD_FAILED.value
        signalBus.uploadStatusSig.emit(record, UploadStatus.UPLOAD_FAILED, str(e))

    finally:
        logger.info("Saved upload result to database.")
        record.save()

    return record


# def _save_to_csv(record, status_desc):
#     """保存记录到CSV文件的辅助函数"""
#     try:
#         station_code = cfg.get(cfg.station_code)
#         if station_code == "110":  # AOI/SPI站别
#             csv_writer.save_aoi_spi_data(record)
#             logger.info(
#                 f"CSV保存成功: AOI/SPI数据, SN={record.serial_number}, 状态={status_desc}"
#             )
#         elif int(station_code) in (109, 122):  # 炉温站别
#             csv_writer.save_reflow_data(record)
#             logger.info(
#                 f"CSV保存成功: 炉温数据, SN={record.serial_number}, 状态={status_desc}"
#             )
#     except Exception as e:
#         logger.error(f"保存CSV失败: SN={record.serial_number}, 错误={e}")
