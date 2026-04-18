import ctypes
import sys
import winreg
from pathlib import Path

from .display import apply, current, list_supported, revert as revert_display
from .logger import log
from .models import Config, Resolution

_window_open = False
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE = "resq"
HOTKEY_ACTIONS = {"safe", "preset1", "preset2", "preset3", "settings"}


class Api:
    """Tiny bridge between pywebview and the app config."""

    def __init__(self, cfg: Config, on_save=None):
        self.cfg = cfg
        self.on_save = on_save

    def get_state(self) -> dict:
        try:
            cur = current()
            modes = list(list_supported())
            if not any(mode == cur for mode in modes):
                modes.insert(0, cur)

            return {
                "ok": True,
                "current": self._mode(cur),
                "safe": self._mode(self.cfg.safe_resolution),
                "presets": [
                    {
                        "slot": i,
                        "name": preset.label,
                        "width": preset.width,
                        "height": preset.height,
                        "frequency": preset.refresh,
                        "is_safe": preset.is_safe,
                        "hotkey": self.cfg.hotkeys.get(f"preset{i}", ""),
                    }
                    for i, preset in enumerate(self.cfg.presets[:3], start=1)
                ],
                "guard": {
                    "enabled": self.cfg.safe_boot_guard,
                    "countdown_seconds": self.cfg.safe_boot_timeout,
                },
                "supported_modes": [self._mode(mode) for mode in modes],
            }
        except Exception as err:
            log(f"settings get_state failed: {err}")
            return {"ok": False, "error": str(err)}

    def set_safe_mode(self, width, height, frequency) -> dict:
        try:
            self.cfg.safe_resolution = Resolution(int(width), int(height), int(frequency), "Safe", True)
            self._save()
            return {"ok": True}
        except Exception as err:
            log(f"settings set_safe_mode failed: {err}")
            return {"ok": False, "error": str(err)}

    def apply_mode(self, width, height, frequency) -> dict:
        try:
            apply(Resolution(int(width), int(height), int(frequency)))
            return {"ok": True}
        except Exception as err:
            log(f"settings apply_mode failed: {err}")
            return {"ok": False, "error": str(err)}

    def use_current_as_safe(self) -> dict:
        try:
            cur = current()
            self.cfg.safe_resolution = Resolution(cur.width, cur.height, cur.refresh, "Safe", True)
            self._save()
            return {"ok": True}
        except Exception as err:
            log(f"settings use_current_as_safe failed: {err}")
            return {"ok": False, "error": str(err)}

    def save_preset(self, slot, name, width, height, frequency, is_safe) -> dict:
        try:
            idx = int(slot) - 1
            if idx < 0 or idx >= 3:
                raise ValueError("preset slot must be 1, 2, or 3")

            self.cfg.presets[idx] = Resolution(
                int(width),
                int(height),
                int(frequency),
                str(name or "").strip(),
                bool(is_safe),
            )
            self._save()
            return {"ok": True}
        except Exception as err:
            log(f"settings save_preset failed: {err}")
            return {"ok": False, "error": str(err)}

    def set_guard(self, enabled: bool, countdown_seconds: int) -> dict:
        try:
            seconds = int(countdown_seconds)
            if seconds < 5 or seconds > 30:
                raise ValueError("countdown must be between 5 and 30 seconds")

            self.cfg.safe_boot_guard = bool(enabled)
            self.cfg.safe_boot_timeout = seconds
            self._save()
            return {"ok": True}
        except Exception as err:
            log(f"settings set_guard failed: {err}")
            return {"ok": False, "error": str(err)}

    def capture_preset(self, slot) -> dict:
        try:
            idx = int(slot) - 1
            if idx < 0 or idx >= 3:
                raise ValueError("preset slot must be 1, 2, or 3")

            cur = current()
            old = self.cfg.presets[idx]
            self.cfg.presets[idx] = Resolution(
                cur.width,
                cur.height,
                cur.refresh,
                old.label or f"Preset {idx + 1}",
                True,
            )
            self._save()
            return {"ok": True}
        except Exception as err:
            log(f"settings capture_preset failed: {err}")
            return {"ok": False, "error": str(err)}

    def revert(self) -> dict:
        try:
            revert_display()
            return {"ok": True}
        except Exception as err:
            log(f"settings revert failed: {err}")
            return {"ok": False, "error": str(err)}

    def get_hotkeys(self) -> dict:
        try:
            return {
                "ok": True,
                "hotkeys": {
                    "safe": self.cfg.hotkeys.get("safe", ""),
                    "preset1": self.cfg.hotkeys.get("preset1", ""),
                    "preset2": self.cfg.hotkeys.get("preset2", ""),
                    "preset3": self.cfg.hotkeys.get("preset3", ""),
                    "settings": self.cfg.hotkeys.get("settings", ""),
                },
            }
        except Exception as err:
            log(f"settings get_hotkeys failed: {err}")
            return {"ok": False, "error": str(err)}

    def set_hotkey(self, action: str, combo: str) -> dict:
        try:
            action = str(action or "").strip()
            combo = str(combo or "").strip()
            if action not in HOTKEY_ACTIONS:
                raise ValueError("unknown hotkey action")
            if not combo:
                raise ValueError("hotkey cannot be empty")

            self.cfg.hotkeys[action] = combo
            self._save()
            return {"ok": True}
        except Exception as err:
            log(f"settings set_hotkey failed: {err}")
            return {"ok": False, "error": str(err)}

    def get_launch_settings(self) -> dict:
        try:
            return {
                "ok": True,
                "run_on_startup": self._runs_on_startup(),
                "minimize_to_tray": bool(getattr(self.cfg, "minimize_to_tray", True)),
            }
        except Exception as err:
            log(f"settings get_launch_settings failed: {err}")
            return {"ok": False, "error": str(err)}

    def set_run_on_startup(self, enabled: bool) -> dict:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
                if enabled:
                    exe = sys.executable.replace("python.exe", "pythonw.exe")
                    main = Path(__file__).resolve().parent.parent / "main.py"
                    winreg.SetValueEx(key, RUN_VALUE, 0, winreg.REG_SZ, f'"{exe}" "{main}"')
                else:
                    try:
                        winreg.DeleteValue(key, RUN_VALUE)
                    except FileNotFoundError:
                        pass
            return {"ok": True}
        except Exception as err:
            log(f"settings set_run_on_startup failed: {err}")
            return {"ok": False, "error": str(err)}

    def set_minimize_to_tray(self, enabled: bool) -> dict:
        try:
            self.cfg.minimize_to_tray = bool(enabled)
            self._save()
            return {"ok": True}
        except Exception as err:
            log(f"settings set_minimize_to_tray failed: {err}")
            return {"ok": False, "error": str(err)}

    def _save(self):
        self.cfg.save()
        if self.on_save:
            self.on_save()

    def _runs_on_startup(self) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, RUN_VALUE)
            return True
        except FileNotFoundError:
            return False

    def _mode(self, res: Resolution) -> dict:
        return {
            "width": res.width,
            "height": res.height,
            "frequency": res.refresh,
        }


def open_settings(cfg: Config, on_save=None):
    global _window_open
    if _window_open:
        return

    try:
        import webview
    except Exception as err:
        log(f"pywebview unavailable: {err}")
        ctypes.windll.user32.MessageBoxW(
            None,
            "pywebview is not installed. Run: python -m pip install -r requirements.txt",
            "resq settings",
            0x10,
        )
        return

    _window_open = True
    html_path = Path(__file__).resolve().parent / "ui" / "index.html"
    api = Api(cfg, on_save)

    try:
        for window in list(getattr(webview, "windows", [])):
            try:
                window.destroy()
            except Exception:
                pass

        webview.create_window(
            "resq — settings",
            html_path.as_uri(),
            js_api=api,
            width=560,
            height=720,
            resizable=False,
            frameless=False,
            on_top=True,
        )
        webview.start(func=None)
    except Exception as err:
        log(f"settings webview failed: {err}")
    finally:
        _window_open = False
