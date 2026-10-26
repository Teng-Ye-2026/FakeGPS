"""
跨平台中文字体查找工具。

Kivy 默认字体（Roboto）不含中文字形，中文会显示成方块。
本模块按优先级寻找一个可用的 CJK 字体：

  1. 项目自带 fonts/ 目录（打包 APK 时随包携带，PC/安卓统一外观）
  2. Windows 系统字体（PC 预览兜底）
  3. Android 系统字体（安卓兜底）
  4. Roboto（最后兜底，中文仍会显示方块，但至少不崩溃）
"""

import glob
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_FONTS_DIR = os.path.join(_HERE, "fonts")

_FONT_CANDIDATES = [
    # 1) 项目自带字体（优先）
    os.path.join(_FONTS_DIR, "NotoSansSC-Regular.otf"),
    os.path.join(_FONTS_DIR, "SimHei.ttf"),
    os.path.join(_FONTS_DIR, "ChineseFont.ttf"),
    # 2) Windows 系统字体
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simsun.ttc",
    # 3) Android 系统字体（绝大多数设备有 DroidSansFallback）
    "/system/fonts/DroidSansFallback.ttf",
    "/system/fonts/NotoSansSC-Regular.otf",
    "/system/fonts/NotoSansCJK-Regular.ttc",
]


def find_cjk_font():
    """返回可用的中文字体文件路径；找不到则返回 'Roboto'。"""
    for p in _FONT_CANDIDATES:
        try:
            if p and os.path.exists(p):
                return p
        except OSError:
            continue
    # 项目 fonts/ 目录下任意字体兜底
    for pattern in ("*.ttf", "*.otf"):
        try:
            hits = glob.glob(os.path.join(_FONTS_DIR, pattern))
        except OSError:
            hits = []
        if hits:
            return hits[0]
    return "Roboto"
