from typing import Union

from fastapi import FastAPI

from app.common.sfc import sfc
from app.common.logger import Logger
import threading
import os
import signal
import uvicorn
import json

app = FastAPI()

logger = Logger("SFC_Server")


@app.get("/get_sfc_result/")
def get_sfc_result(data):

    logger.info(f"Scan SN dict: {data}")
    dict_data = json.loads(data)
    sn = dict_data.get("sn", "")
    logger.info(f"Extracted SN from dict: {sn}")
    return sfc.API_get_SN(sn)


def start_server():
    logger.info("Starting SFC FastAPI server on 127.0.0.1:5005")
    uvicorn.run(app, host="127.0.0.1", port=5005, log_config=None)


def run_server_in_thread():
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    return server_thread


# Url试例  http://127.0.0.1:5005/get_sfc_result/?data={“sn“:”aaa“}
