# FakeGPS —— 安卓虚拟定位 App（Python + Kivy）

用 **纯 Python** 写一个能在安卓手机上**模拟任意 GPS 经纬度**的 App，打包成 `.apk`。

> 原理：通过安卓官方 `LocationManager.addTestProvider / setTestProviderLocation`
> 注册一个虚拟 GPS 信号源，把指定经纬度推送给系统。
> **前置条件**：手机「开发者选项 → 选择模拟位置信息应用」必须选中本 App。

---

## 一、用 PyCharm 开发 / 改界面

1. 用 PyCharm 打开本 `FakeGPS` 文件夹。
2. 建个虚拟环境，装本地依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 桌面端运行可**预览界面**（但模拟定位只在安卓生效）：
   ```bash
   python main.py
   ```
4. 想改界面改 `main.py`，想改定位逻辑改 `gps_mock.py`。

---

## 二、本地构建 APK（推荐 WSL2 / Linux）

Buildozer 官方只支持 Linux，Windows 原生跑不了。最简单：Win11 装 **WSL2 Ubuntu**。

```bash
# 1) 在 Ubuntu 里装基础依赖
sudo apt update
sudo apt install -y git python3-pip openjdk-17-jdk unzip zip \
    autoconf libtool pkg-config zlib1g-dev libncurses5-dev \
    libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev

# 2) 装 buildozer
pip install --upgrade buildozer cython==0.29.33

# 3) 进入项目目录，一键构建（首次会自动下载 Android SDK/NDK，较慢）
buildozer android debug
```

构建完成后，APK 在 `bin/fakegps-0.1-debug.apk`。

> 想换包名 / 应用名 / 图标，改 `buildozer.spec` 即可。

---

## 三、免费云端构建（GitHub Actions，无需本地装 SDK）

不想装环境？把项目推到 GitHub，Actions 自动构建，**免费额度**内不花钱，
构建完去 Actions 页面下载 APK 产物即可。已附好工作流文件 `.github/workflows/build.yml`：

```bash
git init
git add .
git commit -m "FakeGPS app"
git branch -M main
git remote add origin <你的仓库地址>
git push -u origin main
# 然后到 GitHub 仓库 → Actions → 等待 "Build Android APK" 完成 → 下载 Artifact
```

---

## 四、手机安装与设置

1. **开启开发者选项**：设置 → 关于手机 → 连续点击「版本号」7 次。
2. 开发者选项 → **选择模拟位置信息应用** → 选「FakeGPS」。
3. 把 `bin/*.apk` 拷到手机安装，首次运行**授予定位权限**。
4. 打开 App：
   - 「手动输入」页：填纬度/经度，点「开始模拟定位」。
   - 「地图选点」页（推荐）：在地图上**点击**任意位置即可选点；或在搜索框输入**地址**（如“上海东方明珠”）自动定位并选点；用「放大/缩小」调层级；选好后点「定位到这里」。
5. 验证：打开任意地图 App，看定位是否跳到你选的坐标。
6. 不用时点「停止模拟」。

> 地图瓦片默认使用**高德地图（AutoNavi）**数据源（国内可直连、带中文标注、无需 API key），
> `map_widget.py` 的 `TILE_PROVIDERS` 里也可切回 OpenStreetMap。联网才能加载瓦片；
> 即便离线，点击地图仍会按当前中心点估算坐标。若加载失败，点地图页「刷新」重试。
> 地址搜索沿用 OSM 的 Nominatim（国内访问可能较慢/受限），搜索不通时可改用“点击地图选点”。

---

## 常见问题：中文显示成方块（口口口）

Kivy 默认字体（Roboto）**不含中文字形**。本项目已内置开源字体
`fonts/NotoSansSC-Regular.otf`（Noto Sans SC，SIL OFL 免费许可，可随 APK 分发），
`font_util.py` 会自动按优先级选用：

1. 项目 `fonts/` 目录内置字体（PC / 安卓统一）
2. Windows 系统字体（simhei / msyh，PC 预览兜底）
3. Android 系统字体（DroidSansFallback 等兜底）

如果界面仍是方块，确认 `fonts/NotoSansSC-Regular.otf` 存在即可，无需改代码。

---

## 五、注意事项

- 本工具定位为**开发测试 / 学习用途**（如测试 LBS 功能、隐私演示）。
- 地图瓦片与地址搜索使用 OpenStreetMap 公共服务，请遵守其使用条款（带合理 UA、勿高频抓取）。
- 请勿用于违反其他应用服务条款、作弊或任何违法违规场景。
- 部分 App（如一些游戏）有反作弊检测，模拟定位可能被识别或封号，风险自负。
