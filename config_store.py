# -*- coding: utf-8 -*-
"""
config_store.py
=================
配置的读写。主 App（设置页面）和后台 Service 是两个独立的进程，
必须用同一个"文件路径"才能共享配置和状态，这里统一处理路径问题。
"""

import json
import os

CONFIG_FILENAME = "mycgc_config.json"
STATUS_FILENAME = "mycgc_status.json"

DEFAULT_CONFIG = {
    "rpc_url": "https://rpc1.goodchainscan.org/",
    "pair_address": "0x4575De99337ccd0A63BF4e20A33BFd776e40e215",
    "token0_address": "0x1c7ca2f2a0de1ffcce397b539acda16e054ae348",
    "token1_address": "0xdde17d5ef0cce745ce35f5ccd618b728fe7164ac",
    "interval_minutes": 5,
    "threshold_low": 1.0,
    "threshold_high": 3.0,
    "ntfy_topic": "your-unique-topic-name-here",
    "notify_only_on_state_change": True,
    "service_running": False,
}


def get_files_dir() -> str:
    """
    获取安卓私有存储目录（App 和 Service 两个进程都能访问到同一个目录）。
    非安卓环境（比如您在电脑上先测试 UI）下，退回到当前脚本所在目录。
    """
    try:
        from jnius import autoclass  # noqa: F401  只有在安卓上才能 import 成功
        try:
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            ctx = PythonActivity.mActivity
            if ctx is None:
                raise RuntimeError("mActivity is None")
        except Exception:
            PythonService = autoclass("org.kivy.android.PythonService")
            ctx = PythonService.mService
        return ctx.getFilesDir().getAbsolutePath()
    except Exception:
        return os.path.dirname(os.path.abspath(__file__))


def _path(filename: str) -> str:
    return os.path.join(get_files_dir(), filename)


def load_config() -> dict:
    path = _path(CONFIG_FILENAME)
    if not os.path.exists(path):
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        merged = dict(DEFAULT_CONFIG)
        merged.update(cfg)
        return merged
    except Exception:
        return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    path = _path(CONFIG_FILENAME)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def load_status() -> dict:
    path = _path(STATUS_FILENAME)
    if not os.path.exists(path):
        return {"last_check": "", "last_ratio": None, "last_error": "", "state": "unknown"}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"last_check": "", "last_ratio": None, "last_error": "", "state": "unknown"}


def save_status(status: dict) -> None:
    path = _path(STATUS_FILENAME)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
