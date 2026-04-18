import ctypes
from ctypes import wintypes

from .decorators import log_operation, notify_on_change, require_supported
from .logger import log
from .models import Resolution

user32 = ctypes.windll.user32

ENUM_CURRENT_SETTINGS = -1
CDS_UPDATEREGISTRY = 0x00000001
CDS_FULLSCREEN = 0x00000004
DISP_CHANGE_SUCCESSFUL = 0

DM_BITSPERPEL = 0x00040000
DM_PELSWIDTH = 0x00080000
DM_PELSHEIGHT = 0x00100000
DM_DISPLAYFREQUENCY = 0x00400000

_prev: Resolution | None = None


class DEVMODE(ctypes.Structure):
    # painful but necessary; dmSize has to be exactly right or Windows shrugs
    _fields_ = [
        ("dmDeviceName", wintypes.WCHAR * 32),
        ("dmSpecVersion", wintypes.WORD),
        ("dmDriverVersion", wintypes.WORD),
        ("dmSize", wintypes.WORD),
        ("dmDriverExtra", wintypes.WORD),
        ("dmFields", wintypes.DWORD),
        ("dmPositionX", wintypes.LONG),
        ("dmPositionY", wintypes.LONG),
        ("dmDisplayOrientation", wintypes.DWORD),
        ("dmDisplayFixedOutput", wintypes.DWORD),
        ("dmColor", wintypes.SHORT),
        ("dmDuplex", wintypes.SHORT),
        ("dmYResolution", wintypes.SHORT),
        ("dmTTOption", wintypes.SHORT),
        ("dmCollate", wintypes.SHORT),
        ("dmFormName", wintypes.WCHAR * 32),
        ("dmLogPixels", wintypes.WORD),
        ("dmBitsPerPel", wintypes.DWORD),
        ("dmPelsWidth", wintypes.DWORD),
        ("dmPelsHeight", wintypes.DWORD),
        ("dmDisplayFlags", wintypes.DWORD),
        ("dmDisplayFrequency", wintypes.DWORD),
        ("dmICMMethod", wintypes.DWORD),
        ("dmICMIntent", wintypes.DWORD),
        ("dmMediaType", wintypes.DWORD),
        ("dmDitherType", wintypes.DWORD),
        ("dmReserved1", wintypes.DWORD),
        ("dmReserved2", wintypes.DWORD),
        ("dmPanningWidth", wintypes.DWORD),
        ("dmPanningHeight", wintypes.DWORD),
    ]


def _dm():
    dm = DEVMODE()
    dm.dmSize = ctypes.sizeof(DEVMODE)
    return dm


def current() -> Resolution:
    dm = _dm()
    ok = user32.EnumDisplaySettingsW(None, ENUM_CURRENT_SETTINGS, ctypes.byref(dm))
    if not ok:
        raise OSError("could not read current display settings")
    return Resolution(dm.dmPelsWidth, dm.dmPelsHeight, dm.dmDisplayFrequency)


def list_supported():
    seen = set()
    i = 0
    while True:
        dm = _dm()
        if not user32.EnumDisplaySettingsW(None, i, ctypes.byref(dm)):
            break
        key = (dm.dmPelsWidth, dm.dmPelsHeight, dm.dmDisplayFrequency)
        if key not in seen:
            seen.add(key)
            yield Resolution(*key)
        i += 1


def is_supported(res: Resolution) -> bool:
    return any(mode == res for mode in list_supported())


@notify_on_change
@log_operation
@require_supported
def apply(res: Resolution) -> bool:
    global _prev

    old = current()
    dm = _dm()
    user32.EnumDisplaySettingsW(None, ENUM_CURRENT_SETTINGS, ctypes.byref(dm))
    dm.dmPelsWidth = int(res.width)
    dm.dmPelsHeight = int(res.height)
    dm.dmDisplayFrequency = int(res.refresh)
    dm.dmFields = DM_PELSWIDTH | DM_PELSHEIGHT | DM_DISPLAYFREQUENCY | DM_BITSPERPEL

    code = user32.ChangeDisplaySettingsW(ctypes.byref(dm), CDS_UPDATEREGISTRY)
    if code == DISP_CHANGE_SUCCESSFUL:
        _prev = old
        return True

    # some drivers only accept transient changes for custom CRU modes
    log(f"persistent apply failed ({code}), trying transient")
    code = user32.ChangeDisplaySettingsW(ctypes.byref(dm), CDS_FULLSCREEN)
    if code == DISP_CHANGE_SUCCESSFUL:
        _prev = old
        return True

    raise OSError(f"windows refused {res}: ChangeDisplaySettingsW returned {code}")


def revert() -> bool:
    if not _prev:
        log("revert requested but no previous resolution is known")
        return False
    return apply(_prev)
