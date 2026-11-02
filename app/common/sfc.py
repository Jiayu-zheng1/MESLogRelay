# -*- coding: utf-8 -*-

# 20250313 PengWu
# v1 适用于产线 SFC 系统

"""
功能说明:
    connectServer        检查SFC连接
    checkRoute           检查SN是否在当站
    add_pass             上传为PASS
    add_fail             上传为FAIL
    panelSn_get_mlbSn    用连板SN带出单板SN

参数说明:
    isUopOn          在线/离线模式,True/False
    url              SFC 服务地址，在应用设置页配置（现场环境信息，不入库）
    ip_id            对应的terminal ID,由SFC提供,绑定电脑的IP地址.(IP地址可由SFC指定,指定后就是固定IP,与MAC地址相绑定.)
    usrID            测试员工账号(工号),在上传PASS/FAIL时会上传到SFC,在SFC系统可查询由谁测试.
    pw               测试员工密码,一般与工号相同
    errorcode        错误代码,需在上传FAIL时提供,且与SFC系统中建立的代码一致,否则无法记录FAIL.
"""

from threading import Thread
import time
import urllib.request
from datetime import datetime

from app.common.config import cfg
from app.common.signal_bus import signalBus
from app.common.logger import Logger
from app.common.enums import ChipType
import re


logger = Logger("SFC")


panle_sn_rex = re.compile(r";(\w+)")


class SFCConnector:
    def __init__(self):
        cfg.ent.valueChanged.connect(lambda value: setattr(self, "vip", cfg.get_ip()))

        self.url = cfg.get(cfg.sfc_url)
        self.vip = cfg.get_ip()

    def executeSFCFunc(self, p_cmd, p_data):
        urlinfo = f"{self.url}vip={self.vip}&p_cmd={p_cmd}&p_data={p_data}"
        logger.info(f"请求URL: {urlinfo}")
        starttime = datetime.now()

        try:
            req = urllib.request.Request(urlinfo)
            logger.info(f"{req.full_url}")
            fd = urllib.request.urlopen(req, timeout=5).read()
            response_str = fd.decode("utf - 8")
            start_index = response_str.find('org/">') + 6
            end_index = response_str.find("</string")
            result = response_str[start_index:end_index]
            stoptime = datetime.now()
            elapsed = stoptime - starttime
            logger.info(f"返回: {result}")
            logger.info(f"耗时: {elapsed.total_seconds():.4f}秒")

            return result

        except Exception as e:
            logger.error(f"请求发生异常：{e}")
            return str(e)

    def connectServer(self):
        if cfg.get(cfg.uop_mode):
            result = self.executeSFCFunc("1", f"{cfg.get(cfg.op_id)};" * 2)
            return result
        else:
            return "OK"

    def checkRoute(self, sn):
        if cfg.get(cfg.uop_mode):
            result = self.executeSFCFunc("2", f"{sn};")
            return result
        else:
            return "OK"

    def add_record(self, sn, status, errorcode=None):
        if cfg.get(cfg.uop_mode):
            if status:
                return self.add_pass(sn)
            else:
                return self.add_fail(sn, errorcode)
        else:
            return "OK"

    def add_pass(self, sn):
        if cfg.get(cfg.uop_mode):
            result = self.executeSFCFunc("53", f"{cfg.get(cfg.op_id)};{sn};OK;")
            return result
        else:
            return "OK"

    def add_fail(self, sn, errorcode=None):
        if not errorcode:
            errorcode = "ATE_NG"
        if cfg.get(cfg.uop_mode):
            result = self.executeSFCFunc(
                "53", f"{cfg.get(cfg.op_id)};{sn};NG;{errorcode}"
            )
            return result
        else:
            return "OK"

    def get_SN(self, Scan_SN):
        """
        单板条码带出连板条码
        用浏览器  result = 'OK;C47HJ30QS0A000166R'
        用python result = 'OK;C47HJ300SBA880166R'

        返回: (serial_numbers, panel_SN) - serial_numbers 是单板字典，panel_SN 是连板条码
        """
        if not cfg.get(cfg.uop_mode):
            logger.info("离线模式,返回模拟数据")
            mock_sns = self.parse_serial_numbers(
                "OK;1,G5YHMG006FA0001BDR,OK&gt;2,G5YHMG006F90001BDR,OK&gt;3,G5YHMG006F80001BDR,OK&gt;4,G5YHMG006F70001BDR,OK&gt;5,G5YHMG006F30001BDR,108.Pre-AOl&gt;6,G5YHMG006F40001BDR,OK&gt;7,G5YHMG006F50001BDR,OK&gt;8,G5YHMG006F60001BDR,OK&gt;"
            )
            return {"panle_SN": Scan_SN, "single_SN": mock_sns, "box_SN": Scan_SN}
        if len(str(Scan_SN).strip()) == 23:
            result = self.panelSn_get_mlbSn(Scan_SN)
            box_result = self.executeSFCFunc("17", f"{Scan_SN};")
            if "OK;" in box_result:
                box_SN = box_result.split(";")[1]
            result_dict = {"panle_SN": Scan_SN, "single_SN": result, "box_SN": box_SN}
            return result_dict

        else:
            sfc_SN = self.executeSFCFunc("28", f"{Scan_SN};")
            logger.info(f"治具SN获取连板条码 请求返回：{sfc_SN}")
            panle_SN = panle_sn_rex.search(sfc_SN).group(1) if "OK;" in sfc_SN else None
            if panle_SN:
                result = self.panelSn_get_mlbSn(panle_SN)
                result_dict = {
                    "panle_SN": panle_SN,
                    "single_SN": result,
                    "box_SN": Scan_SN,
                }
                return result_dict
            else:
                logger.error(f"治具获取连板条码 请求返回错误：{panle_SN}")
                return

    def API_get_SN(self, Scan_SN):
        """
        单板条码带出连板条码
        用浏览器  result = 'OK;C47HJ30QS0A000166R'
        用python result = 'OK;C47HJ300SBA880166R'

        返回: (serial_numbers, panel_SN) - serial_numbers 是单板字典，panel_SN 是连板条码
        """
        if not cfg.get(cfg.uop_mode):
            logger.info("离线模式,返回模拟数据")
            return self.parse_serial_numbers(
                "OK;1,G5YHMG006FA0001BDR,OK&gt;2,G5YHMG006F90001BDR,OK&gt;3,G5YHMG006F80001BDR,OK&gt;4,G5YHMG006F70001BDR,OK&gt;5,G5YHMG006F30001BDR,108.Pre-AOl&gt;6,G5YHMG006F40001BDR,OK&gt;7,G5YHMG006F50001BDR,OK&gt;8,G5YHMG006F60001BDR,OK&gt;"
            )
        if len(str(Scan_SN).strip()) == 23:
            result = self.executeSFCFunc("52", f"{Scan_SN};")
            return result

        else:
            sfc_SN = self.executeSFCFunc("28", f"{Scan_SN};")
            logger.info(f"治具SN获取连板条码 请求返回：{sfc_SN}")
            panle_SN = panle_sn_rex.search(sfc_SN).group(1) if "OK;" in sfc_SN else None
            if panle_SN:
                result = self.executeSFCFunc("52", f"{panle_SN};")
                return result
            else:
                logger.error(f"治具获取连板条码 请求返回错误：{panle_SN}")
                return None

    def panelSn_get_mlbSn(self, panelSn):
        """
        连板条码带出单板条码
        用浏览器  result = 'OK;1,C47HJ30QS0A000166R,141.Cosmetic AVI>2,C47HJ30QS0B000166R,141.Cosmetic AVI>3,C47HJ30QS0C000166R,141.Cosmetic AVI>4,C47HJ30QS0D000166R,142.Packing>5,C47HJ30QS0E000166R,141.Cosmetic AVI>7,C47HJ30QS0G000166R,141.Cosmetic AVI>8,C47HJ30QS0H000166R,141.Cosmetic AVI>'
        用python result = 'OK;1,C47HJ300SBA880166R,141.Cosmetic AVI&gt;2,C47HJ30QS8B000166R,141.Cosmetic AVI&gt;3,C47HJ300S0C080166R,141.Cosmetic AVI&gt;4,C47HJ300SBDB00166R,142.Packing&gt;5,C47HJ30QSBE080166R,141.Cosmetic AVI&gt;7,C47HJ30QS0G888166R,141.Cosmetic AVI&gt;8,C47HJ300S0H000166R,141.Cosmetic AVI&gt;'
        """
        if cfg.get(cfg.uop_mode):
            result = self.executeSFCFunc("52", f"{panelSn};")
            return self.parse_serial_numbers(result)
        else:
            return self.parse_serial_numbers(
                "OK;1,G5YHMG006FA0001BDR,OK&gt;2,G5YHMG006F90001BDR,OK&gt;3,G5YHMG006F80001BDR,OK&gt;4,G5YHMG006F70001BDR,OK&gt;5,G5YHMG006F30001BDR,108.Pre-AOl&gt;6,G5YHMG006F40001BDR,OK&gt;7,G5YHMG006F50001BDR,OK&gt;8,G5YHMG006F60001BDR,OK&gt;"
            )

    #         return {}  # 返回空字典

    # def panelSn_get_mlbSn(self, panelSn):
    #     """
    #     连板条码带出单板条码
    #     用浏览器  result = 'OK;1,C47HJ30QS0A000166R,141.Cosmetic AVI>2,C47HJ30QS0B000166R,141.Cosmetic AVI>3,C47HJ30QS0C000166R,141.Cosmetic AVI>4,C47HJ30QS0D000166R,142.Packing>5,C47HJ30QS0E000166R,141.Cosmetic AVI>7,C47HJ30QS0G000166R,141.Cosmetic AVI>8,C47HJ30QS0H000166R,141.Cosmetic AVI>'
    #     用python result = 'OK;1,C47HJ300SBA880166R,141.Cosmetic AVI&gt;2,C47HJ30QS8B000166R,141.Cosmetic AVI&gt;3,C47HJ300S0C080166R,141.Cosmetic AVI&gt;4,C47HJ300SBDB00166R,142.Packing&gt;5,C47HJ30QSBE080166R,141.Cosmetic AVI&gt;7,C47HJ30QS0G888166R,141.Cosmetic AVI&gt;8,C47HJ300S0H000166R,141.Cosmetic AVI&gt;'
    #     """
    #     try:
    #         result = self.executeSFCFunc("52", f"{panelSn};")
    #         if "OK;" not in result:
    #             logger.error(f"SFC获取连板条码 请求返回错误：{result}")
    #             return self.parse_serial_numbers(
    #                 "OK;1,G5YHMG006FA0001BDR,OK&gt;2,G5YHMG006F90001BDR,OK&gt;3,G5YHMG006F80001BDR,OK&gt;4,G5YHMG006F70001BDR,OK&gt;5,G5YHMG006F30001BDR,108.Pre-AOl&gt;6,G5YHMG006F40001BDR,OK&gt;7,G5YHMG006F50001BDR,OK&gt;8,G5YHMG006F60001BDR,OK&gt;"
    #             )

    #         return self.parse_serial_numbers(result)

    #     except Exception as e:
    #         logger.error(f"SFC获取连板条码 请求发生异常：{e}")
    #         return self.parse_serial_numbers(
    #             "OK;1,G5YHMG006FA0001BDR,OK&gt;2,G5YHMG006F90001BDR,OK&gt;3,G5YHMG006F80001BDR,OK&gt;4,G5YHMG006F70001BDR,OK&gt;5,G5YHMG006F30001BDR,108.Pre-AOl&gt;6,G5YHMG006F40001BDR,OK&gt;7,G5YHMG006F50001BDR,OK&gt;8,G5YHMG006F60001BDR,OK&gt;"
    #         )

    def parse_serial_numbers(self, data):
        logger.info(f"解析连板带出的单板SN列表: {data}")
        """解析连板带出的单板SN列表"""

        if "OK;" not in data:
            return None

        _, records_data = data.split(";", 1)
        serial_numbers = {}
        records = records_data.split("&gt;")
        for record in records:
            logger.debug(f"处理记录: {record}")
            if record:  # 确保不是空字符串
                parts = record.split(",")
                if len(parts) >= 3:  # 确保有至少3个部分
                    serial_numbers[int(parts[0])] = [parts[1], parts[2]]
                    logger.warning(
                        f"Slot: {parts[0]}, Serial Number: {parts[1]}, Route: {parts[2]}"
                    )

        return serial_numbers


class SFCMonitor(Thread):
    def __init__(self, sfc):
        super().__init__()
        self.daemon = True
        self.sfc = sfc
        self.is_running = True

    def run(self):
        while self.is_running:
            try:
                result = self.sfc.connectServer()

                if "OK" in result and cfg.get(cfg.uop_mode):
                    logger.info("SFC_OK")
                    # signalBus.sfc_connect_signal.emit(True)
                    signalBus.sfc_status_signal.emit(ChipType.ONLINE)
                    time.sleep(24)
                else:
                    if not cfg.get(cfg.uop_mode):
                        signalBus.sfc_status_signal.emit(ChipType.OFFLINE)
                    else:
                        signalBus.sfc_status_signal.emit(ChipType.CONN_FAILED)
                        # signalBus.sfc_connect_signal.emit(False)

            except Exception as e:
                # signalBus.sfc_connect_signal.emit(False)
                signalBus.sfc_status_signal.emit(ChipType.CONN_FAILED)
                logger.error(e)

            time.sleep(6)

    def stop(self):
        self.is_running = False


sfc = SFCConnector()

if __name__ == "__main__":
    sfc = SFCConnector()

    isUopOn = True
    # 示例：在下方填入真实服务器地址与账号后再运行
    url = ""  # 如 http://<host>:<port>/Command_Code.asmx/command_code_for_webservice?
    ip_id = sfc.vip
    usrID = ""  # 操作员工号
    pw = ""  # 密码
    sn = ""  # 输入要查询的 SN（18x 单板 或 23x 连板）

    while True:
        print("-" * 30)
        print("输入单板SN检查站别,或输入连板SN获取绑定的单板:")
        sn = input()

        if len(sn) == 18:
            print(f"输入SN={sn},SN长度=18,单板")
            print(f">>> {ip_id} 连接服务器...")
            sfc.connectServer(isUopOn, url, ip_id, usrID, pw)

            time.sleep(0.1)
            print(f"\n>>> {sn} 流程检查 ...")
            sfc.checkRoute(isUopOn, url, ip_id, sn)

            inp = input("输入(99=Add PASS,1=Add FAIL,0=None):")

            if inp == "99":
                print(f"\n>>> {sn} Add Pass...")
                sfc.add_pass(isUopOn, url, ip_id, usrID, sn)

            elif inp == "1":
                print(f"\n>>> {sn} Add Fail ...")
                sfc.add_fail(
                    isUopOn,
                    url,
                    ip_id,
                    usrID,
                    sn,
                )

            elif inp == "0":
                print("None")

        elif len(sn) == 23:
            print(f"输入SN={sn},SN长度=23,连板")
            print(f">>> {ip_id} 连接服务器...")
            retconnect = sfc.connectServer()

            time.sleep(0.1)
            print(f"\n>>> {sn} 用连板条码获取单板条码...")
            data = sfc.panelSn_get_mlbSn(sn)

            if "OK;" in data:
                # 提取状态和记录数据
                status, records_data = data.split(";", 1)
                print(f"状态: {status}")
                # 按>分割每条记录
                records = records_data.split("&gt;")
                # 打印表头
                print("详细信息:")
                print("Slot\tmlb_SN\t\t\tRoute")
                # 打印每条记录
                for record in records:
                    if record:  # 确保不是空字符串
                        parts = record.split(",")
                        if len(parts) == 3:  # 确保有3个部分
                            slot = parts[0]
                            mlb_sn = parts[1]
                            route = parts[2]
                            print(f"{slot}\t{mlb_sn}\t{route}")
            else:
                print("error:", data)
        else:
            print(f"输入SN={sn},SN长度={len(sn)},未知的")


url = ""  # 示例：填入 SFC 服务器地址（含参数）
