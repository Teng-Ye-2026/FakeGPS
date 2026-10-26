"""
FakeGPS —— 安卓虚拟定位 App（Kivy 界面 + 地图选点 + pyjnius 模拟定位）。

两个界面（ScreenManager 切换）：
  - ManualScreen：手动输入经纬度，开始/停止模拟。
  - MapScreen：OSM 地图选点（点击或搜索地址），一键定位到选点。

PC 上运行 `python main.py` 可预览界面；模拟定位功能仅在安卓生效。

中文显示：Kivy 默认字体不含中文字形，这里统一用 font_util 找到的
CJK 字体（优先项目内置 Noto Sans SC），通过 CLabel/CButton/CTextInput
三个子类全局替换默认字体。
"""

from kivy.app import App
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.textinput import TextInput

import gps_mock
from font_util import find_cjk_font
from map_widget import OSMMap

# ---- 中文支持：统一替换 Kivy 默认字体 ----
FONT_PATH = find_cjk_font()


class CLabel(Label):
    """带中文字体的 Label。"""
    font_name = StringProperty(FONT_PATH)


class CButton(Button):
    """带中文字体的 Button。"""
    font_name = StringProperty(FONT_PATH)


class CTextInput(TextInput):
    """带中文字体的 TextInput（含 hint_text）。"""
    font_name = StringProperty(FONT_PATH)


# ---------------- 手动输入界面 ----------------
class ManualScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = "manual"
        self._app = App.get_running_app()

        root = BoxLayout(orientation="vertical", padding=24, spacing=14)
        bar = BoxLayout(size_hint=(1, 0.1))
        bar.add_widget(CLabel(text="手动输入定位", font_size="20sp", bold=True))
        to_map = CButton(text="地图选点")
        to_map.bind(on_press=lambda *a: setattr(self._app.sm, "current", "map"))
        bar.add_widget(to_map)

        self.status = CLabel(text="状态：未启动", size_hint=(1, 0.12),
                             color=(1, 0.8, 0.3, 1))
        self.lat = CTextInput(text="39.9087", hint_text="纬度 Latitude",
                              multiline=False)
        self.lng = CTextInput(text="116.3975", hint_text="经度 Longitude",
                              multiline=False)
        start = CButton(text="开始模拟定位")
        stop = CButton(text="停止模拟")
        start.bind(on_press=self.start)
        stop.bind(on_press=self.stop)

        root.add_widget(bar)
        root.add_widget(self.lat)
        root.add_widget(self.lng)
        root.add_widget(start)
        root.add_widget(stop)
        root.add_widget(self.status)
        self.add_widget(root)

    def start(self, *a):
        self._app.start_mock_at(float(self.lat.text), float(self.lng.text),
                                self.status)

    def stop(self, *a):
        self._app.stop_mock(self.status)


# ---------------- 地图选点界面 ----------------
class MapScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.name = "map"
        self._app = App.get_running_app()

        root = BoxLayout(orientation="vertical", spacing=8, padding=8)

        # 顶部栏
        bar = BoxLayout(size_hint=(1, 0.08))
        back = CButton(text="手动输入")
        back.bind(on_press=lambda *a: setattr(self._app.sm, "current", "manual"))
        bar.add_widget(back)
        bar.add_widget(CLabel(text="地图选点", font_size="18sp", bold=True))

        # 搜索栏
        search_row = BoxLayout(size_hint=(1, 0.08), spacing=8)
        self.search_input = CTextInput(
            hint_text="输入地址搜索，如：上海东方明珠", multiline=False)
        search_btn = CButton(text="搜索", size_hint=(0.3, 1))
        search_btn.bind(on_press=self.do_search)
        search_row.add_widget(self.search_input)
        search_row.add_widget(search_btn)

        # 地图
        self.map = OSMMap(size_hint=(1, 0.66))
        self.map._on_pick = self.on_pick

        # 底部栏
        bottom = BoxLayout(size_hint=(1, 0.18), spacing=8)
        self.coord_label = CLabel(
            text="点击地图选择位置，或搜索地址", size_hint=(0.4, 1),
            color=(0.9, 0.9, 0.9, 1))
        refresh = CButton(text="刷新", size_hint=(0.12, 1))
        refresh.bind(on_press=lambda *a: self.map.load_tiles_async())
        zoom_in = CButton(text="放大 +", size_hint=(0.12, 1))
        zoom_out = CButton(text="缩小 -", size_hint=(0.12, 1))
        zoom_in.bind(on_press=lambda *a: self.map.zoom_by(1))
        zoom_out.bind(on_press=lambda *a: self.map.zoom_by(-1))

        self.status = CLabel(text="状态：未启动", size_hint=(1, 0.06),
                             color=(1, 0.8, 0.3, 1))

        go = CButton(text="定位到这里")
        go.bind(on_press=self.locate_here)
        stop = CButton(text="停止")
        stop.bind(on_press=lambda *a: self._app.stop_mock(self.status))

        ctrl = BoxLayout(size_hint=(1, 0.1), spacing=8)
        ctrl.add_widget(go)
        ctrl.add_widget(stop)

        bottom.add_widget(self.coord_label)
        bottom.add_widget(refresh)
        bottom.add_widget(zoom_in)
        bottom.add_widget(zoom_out)

        root.add_widget(bar)
        root.add_widget(search_row)
        root.add_widget(self.map)
        root.add_widget(bottom)
        root.add_widget(self.status)
        root.add_widget(ctrl)
        self.add_widget(root)

    def on_pick(self, lat, lng):
        self.coord_label.text = "已选点：{:.5f}, {:.5f}".format(lat, lng)

    def do_search(self, *a):
        q = self.search_input.text.strip()
        if not q:
            return
        self.coord_label.text = "搜索中…"
        self.map.search(q, on_result=self.on_search_result)

    def on_search_result(self, r):
        if r:
            self.coord_label.text = "已选点：{:.5f}, {:.5f}".format(r[0], r[1])
        else:
            self.coord_label.text = "未找到结果"

    def locate_here(self, *a):
        if self.map.selected_lat is None:
            self.status.text = "请先在地图上选点"
            self.status.color = (1, 0.4, 0.4, 1)
            return
        self._app.start_mock_at(self.map.selected_lat,
                                self.map.selected_lng, self.status)


# ---------------- App ----------------
class FakeGPSApp(App):
    def build(self):
        self._event = None
        self._target_lat = None
        self._target_lng = None

        # 申请定位权限（安卓）。PC 上 android 模块不存在，忽略。
        try:
            from android.permissions import request_permissions, Permission
            request_permissions(
                [Permission.ACCESS_FINE_LOCATION,
                 Permission.ACCESS_COARSE_LOCATION])
        except Exception:
            pass

        self.sm = ScreenManager()
        self.sm.add_widget(ManualScreen())
        self.sm.add_widget(MapScreen())
        return self.sm

    def start_mock_at(self, lat, lng, status):
        try:
            self._target_lat = lat
            self._target_lng = lng
            gps_mock.start_mock(lat, lng)
            if self._event:
                self._event.cancel()
            self._event = Clock.schedule_interval(self._tick, 1.0)
            status.text = "模拟中：{:.5f}, {:.5f}".format(lat, lng)
            status.color = (0.4, 1, 0.4, 1)
        except Exception as e:
            status.text = "错误：{}".format(e)
            status.color = (1, 0.4, 0.4, 1)

    def _tick(self, dt):
        try:
            gps_mock.set_mock(self._target_lat, self._target_lng)
        except Exception:
            pass

    def stop_mock(self, status):
        try:
            if self._event:
                self._event.cancel()
                self._event = None
            gps_mock.stop_mock()
            status.text = "状态：已停止"
            status.color = (1, 0.8, 0.3, 1)
        except Exception as e:
            status.text = "错误：{}".format(e)
            status.color = (1, 0.4, 0.4, 1)


if __name__ == "__main__":
    FakeGPSApp().run()
