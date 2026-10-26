"""
安卓模拟定位核心逻辑（仅在 Android 上生效）。

原理：通过 pyjnius 调用安卓官方 LocationManager.addTestProvider / setTestProviderLocation，
注册一个虚拟的 GPS Provider 并不断推送我们指定的经纬度。
使用前必须：手机「开发者选项 -> 选择模拟位置信息应用」选中本 App。
"""

import time

try:
    from jnius import autoclass
except Exception:  # 桌面环境没有 jnius，忽略，便于在 PC 上调试界面
    autoclass = None


def _get_manager():
    """返回 (LocationManager 实例, LocationManager 类)。"""
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    activity = PythonActivity.mActivity
    context = activity.getApplicationContext()
    LocationManager = autoclass("android.location.LocationManager")
    lm = context.getSystemService(context.LOCATION_SERVICE)
    return lm, LocationManager


def start_mock(lat, lng):
    """创建虚拟 GPS Provider 并推送第一帧定位。

    lat/lng 为浮点经纬度，例如北京天安门：39.9087, 116.3975
    """
    if autoclass is None:
        raise RuntimeError("mock 定位仅在安卓设备上可用")

    lm, LocationManager = _get_manager()
    provider = LocationManager.GPS_PROVIDER

    # 若已存在同名 test provider，先移除，避免崩溃
    try:
        if lm.getProvider(provider) is not None:
            lm.removeTestProvider(provider)
    except Exception:
        pass

    # 参数顺序：name, requiresNetwork, requiresSatellite, requiresCell,
    #           hasMonetaryCost, supportsAltitude, supportsSpeed,
    #           supportsBearing, powerRequirement, accuracy
    lm.addTestProvider(provider, False, False, False, False,
                       True, True, True, 0, 5)
    lm.setTestProviderEnabled(provider, True)
    return set_mock(lat, lng)


def set_mock(lat, lng):
    """推送一次定位（可在定时器里反复调用以模拟移动）。"""
    if autoclass is None:
        raise RuntimeError("mock 定位仅在安卓设备上可用")

    lm, LocationManager = _get_manager()
    provider = LocationManager.GPS_PROVIDER

    Location = autoclass("android.location.Location")
    loc = Location(provider)
    loc.setLatitude(float(lat))
    loc.setLongitude(float(lng))
    loc.setAltitude(0.0)
    loc.setAccuracy(1.0)
    loc.setSpeed(0.0)
    loc.setBearing(0.0)

    now_ms = int(time.time() * 1000)
    loc.setTime(now_ms)
    try:  # API 17+ 才支持
        loc.setElapsedRealtimeNanos(now_ms * 1000000)
    except Exception:
        pass

    lm.setTestProviderLocation(provider, loc)
    return True


def stop_mock():
    """关闭并移除虚拟 Provider。"""
    if autoclass is None:
        return True
    lm, LocationManager = _get_manager()
    provider = LocationManager.GPS_PROVIDER
    try:
        lm.setTestProviderEnabled(provider, False)
        lm.removeTestProvider(provider)
    except Exception:
        pass
    return True
