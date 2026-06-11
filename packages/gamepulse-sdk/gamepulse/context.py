from __future__ import annotations

import locale
import platform
import sys

from gamepulse_core import Platform
from gamepulse_core.schemas import DeviceContext


def _detect_platform() -> Platform:
    system = platform.system().lower()
    return {
        "windows": Platform.WINDOWS,
        "darwin": Platform.MACOS,
        "linux": Platform.LINUX,
    }.get(system, Platform.UNKNOWN)


def build_device_context(app_version: str | None) -> DeviceContext:
    try:
        loc = locale.getlocale()[0]
    except Exception:
        loc = None
    return DeviceContext(
        platform=_detect_platform(),
        os_version=platform.release(),
        locale=loc,
        python_version=sys.version.split()[0],
        app_version=app_version,
    )
