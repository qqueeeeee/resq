import ctypes
import queue
import sys
import time
import traceback
from pathlib import Path

from resq.async_core import clear_hotkeys, register_hotkeys
from resq.guard import SafeBootGuard
from resq.logger import init_log, log
from resq.models import Config
from resq.settings import open_settings
from resq.tray import create_icon, update_menu

ROOT = Path(__file__).resolve().parent
VERSION = "0.1.0"
ERROR_ALREADY_EXISTS = 183
MUTEX_NAME = "resq_single_instance"

kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32


def message_box(text: str, title: str = "resq"):
    user32.MessageBoxW(None, text, title, 0x10)


def acquire_single_instance():
    # keeps double-click spam from starting two tray icons
    handle = kernel32.CreateMutexW(None, True, MUTEX_NAME)
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        message_box("resq is already running")
        kernel32.CloseHandle(handle)
        return None
    return handle


def log_startup(cfg: Config):
    try:
        is_admin = bool(shell32.IsUserAnAdmin())
    except Exception:
        is_admin = False

    log(f"resq version: {VERSION}")
    log(f"python: {sys.version}")
    log(f"cwd: {Path.cwd()}")
    log(f"admin: {is_admin}")
    log(
        "config: "
        f"safe={cfg.safe_resolution}, "
        f"presets={len(cfg.presets)}, "
        f"guard_enabled={cfg.safe_boot_guard}"
    )


def run_app():
    debug = "--debug" in sys.argv
    init_log(str(ROOT / "resq.log"), debug=debug)
    log("=== resq starting ===")

    mutex = acquire_single_instance()
    if not mutex:
        return 1

    app_queue = queue.Queue()
    cfg = Config.load(str(ROOT / "config.json"))
    log_startup(cfg)
    icon = None

    def enqueue_settings():
        app_queue.put(("settings", cfg))

    def enqueue_quit():
        app_queue.put(("quit", None))

    def on_config_changed():
        try:
            register_hotkeys(cfg, enqueue_settings)
            if icon:
                update_menu(icon, cfg, enqueue_settings, enqueue_quit)
        except Exception as err:
            log(f"config refresh failed: {err}", "error")

    def cleanup():
        log("cleanup requested")
        clear_hotkeys()
        if icon:
            try:
                icon.stop()
            except Exception as err:
                log(f"tray stop failed: {err}", "warning")
        try:
            kernel32.ReleaseMutex(mutex)
            kernel32.CloseHandle(mutex)
        except Exception:
            pass

    try:
        SafeBootGuard(cfg).check_and_guard()
        register_hotkeys(cfg, enqueue_settings)
        icon = create_icon(cfg, enqueue_settings, enqueue_quit)
        icon.run_detached()

        # pywebview really wants the main thread, pystray really does not care
        while True:
            try:
                signal, payload = app_queue.get(timeout=0.2)
            except queue.Empty:
                time.sleep(0.02)
                continue

            if signal == "settings":
                open_settings(payload, on_config_changed)
            elif signal == "quit":
                break
    except KeyboardInterrupt:
        log("keyboard interrupt")
    finally:
        cleanup()

    return 0


def main():
    try:
        return run_app()
    except Exception:
        tb = traceback.format_exc()
        try:
            log(f"fatal exception:\n{tb}", "error")
        except Exception:
            pass
        message_box("resq crashed. Check resq.log for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
