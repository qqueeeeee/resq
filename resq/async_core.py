import asyncio
import threading

import keyboard

from .display import apply
from .logger import log
from .models import Config

_lock = threading.Lock()
_hotkeys = []


async def countdown(seconds: int, on_tick=None, on_done=None):
    for left in range(seconds, 0, -1):
        if on_tick:
            on_tick(left)
        await asyncio.sleep(1)
    if on_done:
        on_done()


async def run_hotkeys(cfg: Config, on_settings=None):
    register_hotkeys(cfg, on_settings)
    while True:
        await asyncio.sleep(3600)


async def run(cfg: Config, on_settings=None):
    await asyncio.gather(countdown(0), run_hotkeys(cfg, on_settings))


def _switch(res):
    try:
        log(f"switching to {res}")
        apply(res)
    except Exception as err:
        log(f"switch failed: {err}")


def register_hotkeys(cfg: Config, on_settings=None):
    global _hotkeys
    with _lock:
        # unhook_all_hotkeys can wipe hooks owned by other apps on some setups
        for hk in _hotkeys:
            try:
                keyboard.remove_hotkey(hk)
            except Exception as err:
                log(f"hotkey cleanup skipped: {err}")
        _hotkeys = []

        _hotkeys.append(keyboard.add_hotkey(cfg.hotkeys["safe"], lambda: _switch(cfg.safe_resolution), suppress=False))
        for i, preset in enumerate(cfg.presets[:3], start=1):
            _hotkeys.append(
                keyboard.add_hotkey(
                    cfg.hotkeys[f"preset{i}"],
                    lambda preset_arg=preset: _switch(preset_arg),
                    suppress=False,
                )
            )

        if on_settings:
            _hotkeys.append(keyboard.add_hotkey(cfg.hotkeys["settings"], on_settings, suppress=False))

        log(f"hotkeys registered: {cfg.hotkeys}")


def start_hotkeys(cfg: Config, on_settings=None):
    register_hotkeys(cfg, on_settings)
    return None


def clear_hotkeys():
    global _hotkeys
    with _lock:
        for hk in _hotkeys:
            try:
                keyboard.remove_hotkey(hk)
            except Exception as err:
                log(f"hotkey cleanup skipped: {err}")
        _hotkeys = []
