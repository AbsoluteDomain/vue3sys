"""
STOMP 协议帧解析和生成模块

实现 STOMP 1.2 协议规范
参考: https://stomp.github.io/stomp-specification-1.2.html
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any
import json


# STOMP 命令常量
class Command:
    CONNECT = "CONNECT"
    CONNECTED = "CONNECTED"
    SUBSCRIBE = "SUBSCRIBE"
    UNSUBSCRIBE = "UNSUBSCRIBE"
    SEND = "SEND"
    MESSAGE = "MESSAGE"
    RECEIPT = "RECEIPT"
    ERROR = "ERROR"
    DISCONNECT = "DISCONNECT"
    ACK = "ACK"
    NACK = "NACK"


# 常用头字段
class Header:
    DESTINATION = "destination"
    CONTENT_TYPE = "content-type"
    SUBSCRIPTION = "subscription"
    MESSAGE_ID = "message-id"
    ID = "id"
    ACK = "ack"
    RECEIPT = "receipt"
    RECEIPT_ID = "receipt-id"
    VERSION = "version"
    HEART_BEAT = "heart-beat"
    ACCEPT_VERSION = "accept-version"
    HOST = "host"
    LOGIN = "login"
    PASSCODE = "passcode"


# NULL 字符（帧终止符）
NULL_CHAR = '\x00'


@dataclass
class Frame:
    """STOMP 帧"""
    command: str
    headers: Dict[str, str] = field(default_factory=dict)
    body: Optional[str] = None

    def get_header(self, key: str, default: str = None) -> Optional[str]:
        """获取头信息"""
        return self.headers.get(key, default)

    def set_header(self, key: str, value: str) -> 'Frame':
        """设置头信息"""
        self.headers[key] = value
        return self

    def set_body(self, body: Any) -> 'Frame':
        """设置消息体"""
        if isinstance(body, str):
            self.body = body
        elif isinstance(body, (dict, list)):
            self.body = json.dumps(body, ensure_ascii=False)
        else:
            self.body = str(body)
        return self

    def marshal(self) -> str:
        """将帧序列化为字符串"""
        lines = [self.command]

        # 添加头信息
        for key, value in self.headers.items():
            lines.append(f"{_escape_header(key)}:{_escape_header(value)}")

        # 空行分隔头和消息体
        lines.append("")

        # 添加消息体
        if self.body:
            lines.append(self.body)

        # 组合并添加终止符
        return "\n".join(lines) + NULL_CHAR


def _escape_header(value: str) -> str:
    """转义头信息中的特殊字符"""
    if value is None:
        return ""
    value = value.replace("\\", "\\\\")
    value = value.replace("\n", "\\n")
    value = value.replace("\r", "\\r")
    value = value.replace(":", "\\c")
    return value


def _unescape_header(value: str) -> str:
    """反转义头信息"""
    if value is None:
        return ""
    value = value.replace("\\c", ":")
    value = value.replace("\\r", "\r")
    value = value.replace("\\n", "\n")
    value = value.replace("\\\\", "\\")
    return value


def unmarshal(data: str) -> Optional[Frame]:
    """从字符串解析帧"""
    if not data:
        return None

    # 移除终止符
    if data.endswith(NULL_CHAR):
        data = data[:-1]

    lines = data.split("\n")
    if not lines:
        return None

    # 第一行是命令
    command = lines[0].strip()
    if not command:
        return None

    frame = Frame(command=command)

    # 解析头信息
    body_start_index = 1
    for i, line in enumerate(lines[1:], start=1):
        # 空行表示头信息结束
        if line == "":
            body_start_index = i + 1
            break

        # 解析键值对
        if ":" in line:
            key, value = line.split(":", 1)
            frame.headers[_unescape_header(key)] = _unescape_header(value)

    # 解析消息体
    if body_start_index < len(lines):
        frame.body = "\n".join(lines[body_start_index:])

    return frame


# ============ 工厂函数 ============

def new_connected_frame() -> Frame:
    """创建 CONNECTED 帧"""
    return Frame(
        command=Command.CONNECTED,
        headers={
            Header.VERSION: "1.2",
            Header.HEART_BEAT: "0,0"
        }
    )


def new_message_frame(
    destination: str,
    subscription_id: str,
    message_id: str,
    body: Any,
    content_type: str = "application/json"
) -> Frame:
    """创建 MESSAGE 帧"""
    frame = Frame(
        command=Command.MESSAGE,
        headers={
            Header.DESTINATION: destination,
            Header.SUBSCRIPTION: subscription_id,
            Header.MESSAGE_ID: message_id,
            Header.CONTENT_TYPE: content_type
        }
    )
    frame.set_body(body)
    return frame


def new_error_frame(message: str) -> Frame:
    """创建 ERROR 帧"""
    return Frame(
        command=Command.ERROR,
        headers={"message": message},
        body=message
    )


def new_receipt_frame(receipt_id: str) -> Frame:
    """创建 RECEIPT 帧"""
    return Frame(
        command=Command.RECEIPT,
        headers={Header.RECEIPT_ID: receipt_id}
    )
