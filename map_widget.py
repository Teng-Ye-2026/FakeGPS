"""
OSMMap —— 纯 Python 地图选点控件（Kivy + urllib，无付费依赖）。

默认瓦片源：**高德地图（AutoNavi）**，国内直连、带中文标注、无需 API key。
（可在 TILE_PROVIDERS 里切换回 OpenStreetMap 等。）

功能：
  - 加载在线瓦片地图，点击任意位置 -> 计算经纬度并标记选点
  - 拖动平移、按钮缩放（zoom +/-）、刷新（网络恢复后重试）
  - 地址搜索（Nominatim，OSM 免费地理编码；国内可能需联网到 OSM）
  - 选点坐标通过 selected_lat / selected_lng 暴露给外部
  - 加载中 / 加载失败 有文字提示
"""

import io
import json
import math
import ssl
import threading
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.graphics import Color, Ellipse, PopMatrix, PushMatrix, Rectangle, Translate
from kivy.uix.label import Label
from kivy.uix.widget import Widget

try:
    import certifi
    _CA = certifi.where()
except Exception:
    _CA = None

from font_util import find_cjk_font

_FONT = find_cjk_font()
_UA = "FakeGPS/1.0 (educational use)"

# 瓦片源：高德默认（国内可用、中文标注）。切换时坐标算法不变（均为标准 XYZ 瓦片）。
TILE_PROVIDERS = {
    "amap": lambda z, x, y: (
        "https://wprd0{}.is.autonavi.com/appmaptile?lang=zh_cn&size=1"
        "&style=7&x={}&y={}&z={}".format(((x + y) % 4) + 1, x, y, z)
    ),
    "osm": lambda z, x, y: (
        "https://tile.openstreetmap.org/{}/{}/{}.png".format(z, x, y)
    ),
}
TILE_SOURCE = "amap"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search?format=json&limit=1&q={q}"


# ---------- Web Mercator 坐标换算 ----------
def latlng_to_tile(lat, lng, zoom):
    n = 2.0 ** zoom
    xt = (lng + 180.0) / 360.0 * n
    lat_rad = math.radians(lat)
    yt = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return xt, yt


def tile_to_latlng(xt, yt, zoom):
    n = 2.0 ** zoom
    lng = xt / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * yt / n))))
    return lat, lng


def _https_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    ctx = ssl.create_default_context(cafile=_CA) if _CA else None
    with urllib.request.urlopen(req, timeout=12, context=ctx) as r:
        return r.read()


def _fetch_tile(tx, ty, zoom):
    """下载单张瓦片，返回 Kivy Texture；失败返回 None。"""
    n = 2 ** zoom
    ty = max(0, min(n - 1, ty))
    tx = tx % n
    url = TILE_PROVIDERS[TILE_SOURCE](zoom, tx, ty)
    try:
        data = _https_get(url)
        return CoreImage(io.BytesIO(data), ext="png").texture
    except Exception as e:
        print("tile fetch failed", tx, ty, e)
        return None


class OSMMap(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.grid = 3
        self.tile = 256
        self.zoom = 15
        self.center_lat = 39.9087     # 默认：北京天安门
        self.center_lng = 116.3975
        self.selected_lat = None
        self.selected_lng = None

        self.pan_x = 0.0
        self.pan_y = 0.0
        self._tiles = []
        self._tl_x = 0
        self._tl_y = 0

        self._down = None
        self._last = None
        self._panning = False

        # 加载状态提示（覆盖在地图上方，不影响触摸穿透）
        self.overlay = Label(
            text="地图加载中…", font_name=_FONT, font_size="16sp",
            color=(1, 1, 1, 1), size_hint=(None, None), size=(300, 40),
            pos_hint={"center_x": 0.5, "top": 1.0})
        self.add_widget(self.overlay)

        self.bind(size=self._on_size)
        self.load_tiles_async()

    # ---------- 瓦片加载 ----------
    def load_tiles_async(self):
        self.overlay.text = "地图加载中…"
        ctx, cty = [int(v) for v in latlng_to_tile(
            self.center_lat, self.center_lng, self.zoom)]
        tl_x = ctx - self.grid // 2
        tl_y = cty - self.grid // 2
        jobs = [(tl_x + c, tl_y + r)
                for r in range(self.grid) for c in range(self.grid)]

        def worker(job):
            return (job[0], job[1], _fetch_tile(job[0], job[1], self.zoom))

        def done(fut):
            try:
                tiles = fut.result()
            except Exception as e:
                print("tile load error", e)
                tiles = []
            self._tiles = tiles
            self._tl_x, self._tl_y = tl_x, tl_y
            if not tiles or all(t is None for t in tiles):
                self.overlay.text = "地图加载失败：请检查网络后点「刷新」"
            else:
                self.overlay.text = ""
            Clock.schedule_once(lambda dt: self.redraw())

        executor = ThreadPoolExecutor(max_workers=9)
        fut = executor.submit(lambda: [worker(j) for j in jobs])
        fut.add_done_callback(done)

    # ---------- 绘制 ----------
    def redraw(self):
        self.canvas.clear()
        T = self.tile
        G = self.grid
        with self.canvas:
            PushMatrix()
            Translate(self.pan_x, self.pan_y)
            for (tx, ty, tex) in self._tiles:
                if tex is None:
                    continue
                x = (tx - self._tl_x) * T
                y = (self._tl_y + G - (ty + 1)) * T
                Color(1, 1, 1, 1)
                Rectangle(texture=tex, pos=(x, y), size=(T, T))
            if self.selected_lat is not None:
                sftx, sfty = latlng_to_tile(
                    self.selected_lat, self.selected_lng, self.zoom)
                mx = (sftx - self._tl_x) * T
                my = (self._tl_y + G - sfty) * T
                r = 9
                Color(1, 0.1, 0.1, 1)
                Ellipse(pos=(mx - r, my - r), size=(2 * r, 2 * r))
                Rectangle(pos=(mx - 1.5, my - 18), size=(3, 14))
                Rectangle(pos=(mx - 9, my - 1.5), size=(18, 3))
            PopMatrix()

    def _on_size(self, *a):
        self.redraw()

    # ---------- 坐标换算：屏幕像素 -> 经纬度 ----------
    def pixel_to_latlng(self, local_x, local_y):
        T = self.tile
        G = self.grid
        base_x = local_x - self.pan_x
        base_y = local_y - self.pan_y
        ftx = self._tl_x + base_x / T
        fty = self._tl_y + G - base_y / T
        return tile_to_latlng(ftx, fty, self.zoom)

    def select_latlng(self, lat, lng):
        self.selected_lat = lat
        self.selected_lng = lng
        self.redraw()

    # ---------- 平移 / 缩放 / 刷新 / 搜索 ----------
    def recenter(self, lat, lng):
        self.center_lat = lat
        self.center_lng = lng
        self.pan_x = self.pan_y = 0.0
        self.load_tiles_async()

    def zoom_by(self, delta):
        self.zoom = max(1, min(19, self.zoom + delta))
        self.pan_x = self.pan_y = 0.0
        self.load_tiles_async()

    def search(self, query, on_result=None):
        """地址搜索 -> 居中并选点。结果通过 on_result((lat,lng)|None) 回调。"""
        def run():
            try:
                url = NOMINATIM_URL.format(q=urllib.parse.quote(query))
                data = json.loads(_https_get(url).decode("utf-8"))
                if data:
                    lat = float(data[0]["lat"])
                    lng = float(data[0]["lon"])
                    Clock.schedule_once(lambda dt: self.recenter(lat, lng))
                    Clock.schedule_once(
                        lambda dt: self.select_latlng(lat, lng))
                    if on_result:
                        Clock.schedule_once(lambda dt: on_result((lat, lng)))
                elif on_result:
                    Clock.schedule_once(lambda dt: on_result(None))
            except Exception as e:
                print("search error", e)
                if on_result:
                    Clock.schedule_once(lambda dt: on_result(None))
        threading.Thread(target=run, daemon=True).start()

    # ---------- 触摸交互 ----------
    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        self._down = (touch.x, touch.y)
        self._last = (touch.x, touch.y)
        self._panning = False
        return True

    def on_touch_move(self, touch):
        if self._down is None:
            return False
        dx = touch.x - self._last[0]
        dy = touch.y - self._last[1]
        if not self._panning:
            if math.hypot(touch.x - self._down[0],
                          touch.y - self._down[1]) > 10:
                self._panning = True
        if self._panning:
            self.pan_x += dx
            self.pan_y += dy
            self._last = (touch.x, touch.y)
            self.redraw()
        return True

    def on_touch_up(self, touch):
        if self._down is None:
            return False
        if not self._panning:
            lx, ly = self.to_widget(touch.x, touch.y)
            lat, lng = self.pixel_to_latlng(lx, ly)
            self.select_latlng(lat, lng)
            if self._on_pick:
                self._on_pick(lat, lng)
        else:
            cx = self.width / 2.0
            cy = self.height / 2.0
            lat, lng = self.pixel_to_latlng(cx, cy)
            self.recenter(lat, lng)
        self._down = None
        return True

    _on_pick = None  # 外部可设置：def callback(lat, lng)
