# -*- coding: utf-8 -*-
"""
monitor_service.py
====================
这是安卓"服务(Service)"的入口脚本，会被 buildozer 打包成一个独立跑在
后台的 Python 进程（跟主 App 界面的进程是分开的）。

它做的事情跟原来的桌面版 goodchain_cn_monitor.py 完全一样：
    每隔 N 分钟读一次链上储备量 -> 算比例 -> 比对高低阈值 -> ntfy 推送通知

区别只是：
    - 参数从 config_store 里读（您在 App 设置页改的参数，这里立刻生效）
    - 每次检查结果写入 status 文件，главный App 界面可以显示出来
"""

import base64
import sys
import time
import traceback
from datetime import datetime

import requests

# 让 service 进程也能 import 到项目根目录下的模块
sys.path.append(sys.path[0] + "/..")

from config_store import load_config, load_status, save_status  # noqa: E402
import eth_client  # noqa: E402


def encode_header_utf8(text: str) -> str:
    b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
    return f"=?UTF-8?B?{b64}?="


def send_notification(ntfy_topic: str, title: str, message: str):
    try:
        requests.post(
            f"https://ntfy.sh/{ntfy_topic}",
            data=message.encode("utf-8"),
            headers={
                "Title": encode_header_utf8(title),
                "Priority": "high",
                "Tags": "warning",
            },
            timeout=10,
        )
    except Exception:
        pass  # 通知发送失败不应该让整个监控循环挂掉


def run_once(cfg: dict, last_state: str) -> str:
    """跑一次检查，返回新的 state（'low' / 'high' / 'normal'）"""
    dec0 = eth_client.get_decimals(cfg["rpc_url"], cfg["token0_address"])
    dec1 = eth_client.get_decimals(cfg["rpc_url"], cfg["token1_address"])
    sym0 = eth_client.get_symbol(cfg["rpc_url"], cfg["token0_address"])
    sym1 = eth_client.get_symbol(cfg["rpc_url"], cfg["token1_address"])

    r0, r1 = eth_client.get_reserves(cfg["rpc_url"], cfg["pair_address"])
    amount0 = r0 / (10 ** dec0)
    amount1 = r1 / (10 ** dec1)
    amounts = {sym0: amount0, sym1: amount1}

    if "CGC" not in amounts or "WGDC" not in amounts:
        raise RuntimeError(f"池子里没找到 CGC/WGDC，实际 token 是 {sym0}/{sym1}，请检查地址")

    cgc_amount = amounts["CGC"]
    wgdc_amount = amounts["WGDC"]
    ratio = cgc_amount / wgdc_amount if wgdc_amount else 0

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if ratio < cfg["threshold_low"]:
        state = "low"
        if not cfg["notify_only_on_state_change"] or state != last_state:
            send_notification(cfg["ntfy_topic"], "GDC比例提醒", f"GDC现在比例数低！当前比例={ratio:.6f}")
    elif ratio > cfg["threshold_high"]:
        state = "high"
        if not cfg["notify_only_on_state_change"] or state != last_state:
            send_notification(cfg["ntfy_topic"], "GDC比例提醒", f"GDC现在比例数高！当前比例={ratio:.6f}")
    else:
        state = "normal"

    save_status({
        "last_check": now_str,
        "last_ratio": ratio,
        "cgc_amount": cgc_amount,
        "wgdc_amount": wgdc_amount,
        "last_error": "",
        "state": state,
    })
    return state


def main_loop():
    last_state = None
    status = load_status()
    if status.get("state") in ("low", "high", "normal"):
        last_state = status["state"]

    while True:
        cfg = load_config()
        try:
            last_state = run_once(cfg, last_state)
        except Exception as e:
            err = f"{e}"
            save_status({
                **load_status(),
                "last_error": err,
                "last_check": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
            traceback.print_exc()

        # 每次循环都重新读取配置，这样您在设置页改了刷新间隔，
        # 下一轮就会用新的间隔，不需要重启服务
        sleep_seconds = max(30, int(cfg.get("interval_minutes", 5)) * 60)
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    main_loop()
