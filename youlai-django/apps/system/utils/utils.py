"""系统工具模块，提供通用的工具函数。"""

# system/utils.py
import requests


def get_ip_location(ip):
    # 如果是内网地址，返回本地
    if ip.startswith("10.") or ip.startswith("192.") or ip.startswith("172.") or ip == "127.0.0.1" or ip == "localhost":
        return "本地"

    url = f"https://opendata.baidu.com/api.php?query={ip}&co=&resource_id=6006&oe=utf8"
    response = requests.get(url)
    data = response.json()

    if data.get("status") == "0" and data.get("data"):
        location = data["data"][0].get("location", "未知")
        return location
    return "未知"
