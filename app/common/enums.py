from enum import Enum


class Result(Enum):
    SKIP = "SKIP"
    UNTEST = "UNTEST"
    PASS = "PASS"
    FAIL = "FAIL"
    RPASS = "RPASS"


class UploadStatus(Enum):
    SKIP = "跳过"
    UNTEST = "未测试"
    PENDING = "待上传"
    UPLOADING = "上传中"
    UPLOADED = "已上传"
    UPLOAD_FAILED = "上传失败"
    CHECK_UOP = "检查UOP"
    UOP = "UOP"


class ChipType:
    INFO = "信息"
    SUCCESS = "成功"
    WARNING = "警告"
    DANGER = "错误"
    ONLINE = "在线"
    OFFLINE = "离线"
    CONN_FAILED = "连接失败"
