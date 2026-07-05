[app]
title = mycgc比例监控
package.name = mycgc
package.domain = org.dahai.mycgc

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json

version = 0.1.0

# 主 App 和后台服务都需要这些依赖。
# 注意：这里特意不用 web3，改用 requests 直连 JSON-RPC，避免 web3 相关
# 依赖（pycryptodome / eth-hash 等）在 python-for-android 上编译失败。
requirements = python3,kivy==2.3.0,requests,pyjnius,certifi,urllib3,idna,charset-normalizer

# 后台服务声明：格式是 服务名:脚本路径[:foreground]
# 加 foreground 是关键 —— 会以"前台服务+常驻通知"的方式运行，
# 大幅降低被安卓系统后台杀掉的概率（但仍建议手动关闭该 App 的电池优化）。
services = monitor:service/monitor_service.py:foreground

[app:android.permissions]
INTERNET
ACCESS_NETWORK_STATE
FOREGROUND_SERVICE
WAKE_LOCK
POST_NOTIFICATIONS
RECEIVE_BOOT_COMPLETED

orientation = portrait
fullscreen = 0

[buildozer]
log_level = 2
warn_on_root = 1

[app:android]
android.api = 33
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a, armeabi-v7a
# 用较新且经过验证的 p4a 分支，避免旧版本兼容性问题
p4a.branch = master
