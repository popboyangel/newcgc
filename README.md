# mycgc —— CGC/WGDC 比例监控 安卓 App

把原来跑在云服务器上的 `goodchain_cn_monitor.py` 改造成了手机 App：
可以直接在手机上改刷新分钟数、低/高阈值、ntfy 主题，后台常驻轮询链上数据，
触发阈值时通过 ntfy.sh 推送到手机。

## 项目结构

```
mycgc_app/
├── main.py                     # Kivy 主界面（设置页 + 状态页）
├── config_store.py             # App 与后台服务共享的配置/状态读写
├── eth_client.py                # 不依赖 web3.py 的轻量 JSON-RPC 客户端
├── service/
│   └── monitor_service.py      # 后台监控服务（安卓前台服务运行）
├── buildozer.spec              # 打包配置
└── .github/workflows/
    └── build-apk.yml           # GitHub Actions 自动构建 APK
```

## 为什么不用 web3.py

`web3.py` 依赖 `eth-abi`、`eth-hash`、`pycryptodome` 等一堆需要编译的 C 扩展，
在 `python-for-android` 上经常编译失败，很可能是之前构建卡住的原因之一。
这里改成手写最小化的 JSON-RPC 调用（只用 `requests`），只覆盖脚本实际需要的
三个函数：`getReserves()` / `decimals()` / `symbol()`，兼容性好很多。

## 本地先测一下界面（可选，非必须）

如果电脑上装了 Python + Kivy，可以先跑：

```bash
pip install kivy requests
python main.py
```

在电脑上跑的时候，"启动后台监控"按钮不会真的常驻后台（那是安卓专属的
Service 机制），只是给您看一下界面是否顺手，参数改完点"保存设置"即可。

## 构建 APK（推荐：GitHub Actions）

1. 把这个项目推到您自己的 GitHub 仓库（新建一个仓库即可，不需要用回之前
   那个）。
2. 进 GitHub 仓库的 Actions 标签页，手动触发 `Build mycgc APK`
   （或者直接 push 到 `main` 分支会自动触发）。
3. 构建完成后，在这次运行的 Artifacts 里下载 `mycgc-debug-apk`，
   里面就是签名调试版 APK，传到手机上安装即可（需要在手机设置里允许
   "安装未知来源应用"）。

这次用的是社区维护的 `buildozer-action`，它把 Android SDK/NDK、Cython
版本匹配这些坑都封装好了，比之前手写 apt/pip 命令的方式稳定很多。
如果还是构建失败，把 Actions 日志里报错的那一段贴给我，我再帮您调整
`buildozer.spec` 里的版本号。

## 安装后的重要设置（不然后台会被系统杀掉）

1. 打开手机的「设置 → 应用 → mycgc比例监控 → 电池」，选择**不限制 / 无限制**
   （不同品牌手机叫法不同，小米叫"无限制"，华为叫"手动管理→允许后台活动"，
   一定要关掉，否则安卓迟早会把后台监控进程杀掉）。
2. 首次打开 App 时，把 8 个参数改成您自己的值：
   - RPC 节点地址、Pair 合约地址、Token0/Token1 地址（默认已经填好您之前用的地址）
   - 刷新间隔（分钟）
   - 低阈值 / 高阈值
   - ntfy 推送主题（跟您手机 ntfy App 里订阅的主题名一致）
3. 点"保存设置"，再点"启动后台监控"。

## 关于耗电和流量

后台服务会按您设的间隔一直发 RPC 请求，这跟原来放服务器上跑没有本质区别，
只是现在是手机自己在跑，会有一定的耗电和流量消耗（间隔越短，消耗越多）。
如果不想手机一直耗电，也可以考虑："真正的监控循环仍然放云服务器上跑（省电），
这个 App 只做远程改参数的控制面"这种混合方案——如果您想要这个方向，
告诉我，我可以再加一个简单的远程配置接口。

## 已知需要您自己核实的点

- `main.py` 里调用安卓服务用的是 `android.AndroidService` 这个类，这是
  python-for-android 目前文档里的标准用法；如果构建出来的 APK 上服务启动
  按钮报错，大概率是 p4a 版本对这个 API 有细节差异，把报错信息发我，
  我帮您改成对应版本兼容的写法。
- 通知仍然是通过 ntfy.sh 服务器推送，跟原来桌面版机制完全一样，
  App 本身不需要保持在前台，手机息屏也能收到。
