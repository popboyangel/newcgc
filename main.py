# -*- coding: utf-8 -*-
"""
main.py —— mycgc App 主界面
=============================
两块功能：
  1. 设置页：改 RPC 地址、Pair/Token 地址、刷新分钟数、低/高阈值、ntfy 主题
  2. 状态页：显示后台服务最近一次检查结果，启动/停止后台监控服务
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.switch import Switch
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.utils import platform

from config_store import load_config, save_config, load_status

FIELD_SPECS = [
    ("rpc_url", "RPC 节点地址"),
    ("pair_address", "DEX Pair 合约地址"),
    ("token0_address", "Token0 地址"),
    ("token1_address", "Token1 地址"),
    ("interval_minutes", "刷新间隔（分钟）"),
    ("threshold_low", "低阈值（低于此值提醒“低”）"),
    ("threshold_high", "高阈值（高于此值提醒“高”）"),
    ("ntfy_topic", "ntfy 推送主题（Topic）"),
]


class RootLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=12, spacing=8, **kwargs)
        self.cfg = load_config()
        self.inputs = {}
        self._service = None

        self.status_label = Label(
            text="状态：未启动", size_hint_y=None, height=90, halign="left", valign="top"
        )
        self.status_label.bind(size=lambda *_: setattr(self.status_label, "text_size", self.status_label.size))
        self.add_widget(self.status_label)

        scroll = ScrollView()
        grid = GridLayout(cols=1, spacing=6, size_hint_y=None, padding=(0, 6))
        grid.bind(minimum_height=grid.setter("height"))

        for key, label_text in FIELD_SPECS:
            grid.add_widget(Label(text=label_text, size_hint_y=None, height=24, halign="left"))
            ti = TextInput(
                text=str(self.cfg.get(key, "")),
                multiline=False,
                size_hint_y=None,
                height=44,
            )
            self.inputs[key] = ti
            grid.add_widget(ti)

        # 状态变化才通知 / 每次都通知
        row = BoxLayout(size_hint_y=None, height=44, spacing=8)
        row.add_widget(Label(text="同一状态只提醒一次", size_hint_x=0.7))
        self.switch_state_change = Switch(active=bool(self.cfg.get("notify_only_on_state_change", True)))
        row.add_widget(self.switch_state_change)
        grid.add_widget(row)

        scroll.add_widget(grid)
        self.add_widget(scroll)

        btn_row = BoxLayout(size_hint_y=None, height=52, spacing=8)
        save_btn = Button(text="保存设置")
        save_btn.bind(on_release=self.on_save)
        btn_row.add_widget(save_btn)

        self.toggle_btn = Button(text="启动后台监控")
        self.toggle_btn.bind(on_release=self.on_toggle_service)
        btn_row.add_widget(self.toggle_btn)
        self.add_widget(btn_row)

        Clock.schedule_interval(self.refresh_status, 5)
        self.refresh_status()

    def collect_config(self) -> dict:
        cfg = dict(self.cfg)
        for key, _ in FIELD_SPECS:
            raw = self.inputs[key].text.strip()
            if key in ("interval_minutes",):
                cfg[key] = int(raw) if raw else cfg.get(key, 5)
            elif key in ("threshold_low", "threshold_high"):
                cfg[key] = float(raw) if raw else cfg.get(key, 0)
            else:
                cfg[key] = raw
        cfg["notify_only_on_state_change"] = self.switch_state_change.active
        return cfg

    def on_save(self, *_):
        cfg = self.collect_config()
        cfg["service_running"] = self.cfg.get("service_running", False)
        save_config(cfg)
        self.cfg = cfg
        self.status_label.text = "设置已保存，后台服务下一轮检查会自动使用新参数"

    def on_toggle_service(self, *_):
        cfg = self.collect_config()
        if not self._is_service_running():
            cfg["service_running"] = True
            save_config(cfg)
            self.cfg = cfg
            self._start_service()
            self.toggle_btn.text = "停止后台监控"
        else:
            cfg["service_running"] = False
            save_config(cfg)
            self.cfg = cfg
            self._stop_service()
            self.toggle_btn.text = "启动后台监控"

    def _is_service_running(self) -> bool:
        return self.cfg.get("service_running", False)

    def _start_service(self):
        if platform == "android":
            try:
                from android import AndroidService
                self._service = AndroidService("CGC比例监控", "正在后台监控 CGC/WGDC 比例")
                self._service.start("mycgc monitor running")
            except Exception as e:
                self.status_label.text = f"启动服务失败：{e}"
        else:
            self.status_label.text = "非安卓环境：这里只做界面测试，实际监控请打包成 APK 后在手机上运行"

    def _stop_service(self):
        if platform == "android":
            try:
                if self._service is not None:
                    self._service.stop()
                else:
                    from android import AndroidService
                    AndroidService("CGC比例监控", "").stop()
            except Exception as e:
                self.status_label.text = f"停止服务失败：{e}"

    def refresh_status(self, *_):
        status = load_status()
        state_map = {"low": "偏低", "high": "偏高", "normal": "正常", "unknown": "暂无数据"}
        state_text = state_map.get(status.get("state", "unknown"), "暂无数据")
        ratio = status.get("last_ratio")
        ratio_text = f"{ratio:.6f}" if isinstance(ratio, (int, float)) else "--"
        last_check = status.get("last_check") or "尚未检查"
        err = status.get("last_error") or ""
        running_text = "运行中" if self._is_service_running() else "未启动"
        text = (
            f"服务状态：{running_text}\n"
            f"最近检查时间：{last_check}\n"
            f"当前比例：{ratio_text}（{state_text}）"
        )
        if err:
            text += f"\n最近错误：{err}"
        self.status_label.text = text


class MyCgcApp(App):
    def build(self):
        return RootLayout()

    def on_start(self):
        # 如果上次关闭 App 前服务是"运行中"状态，重新拉起服务（比如手机重启后）
        cfg = load_config()
        if cfg.get("service_running") and platform == "android":
            try:
                from android import AndroidService
                svc = AndroidService("CGC比例监控", "正在后台监控 CGC/WGDC 比例")
                svc.start("mycgc monitor running")
            except Exception:
                pass


if __name__ == "__main__":
    MyCgcApp().run()
