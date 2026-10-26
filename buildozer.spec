[app]

# (str) 应用标题
title = FakeGPS

# (str) 包名
package.name = fakegps
package.domain = org.fakegps

# (str) 应用版本号（Buildozer 必填）
version = 0.1

# (str) 源代码目录
source.dir = .
# 注意包含 ttf/otf：中文字体（fonts/NotoSansSC-Regular.otf）必须随 APK 打包
source.include_exts = py,png,jpg,kv,atlas,txt,ttf,otf

# (list) 依赖：python3 + kivy 界面 + pyjnius(调安卓API) + android(权限助手)
# + certifi(安卓 HTTPS 证书，加载地图瓦片/搜索需要)
requirements = python3,kivy==2.2.1,pyjnius,android,certifi

# (str) 横竖屏
orientation = portrait

# 安卓权限：定位相关。无需 ACCESS_MOCK_LOCATION，
# 只要在“开发者选项”把本 App 设为模拟位置应用即可。
android.permissions = ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,INTERNET

# 安卓编译版本
android.api = 31
android.minapi = 21
android.sdk = 31
# NDK 版本：Buildozer 默认 23b 太旧，p4a 要求 ≥ 25（推荐 28c）。
# 25b 在 Buildozer 下载源与 p4a 兼容性上都稳妥。
android.ndk = 25b
android.accept_sdk_license = True

# (int) 目标架构（armeabi-v7a 通用，体积更小；需要 64 位可加 arm64-v8a）
android.archs = armeabi-v7a

# 日志
log_level = 2
warn_on_root = 0
