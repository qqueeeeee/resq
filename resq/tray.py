from pathlib import Path

import pystray
from PIL import Image, ImageDraw

from .display import apply, current
from .logger import log
from .models import Config, Resolution


def _icon_img():
    path = Path("icon.png")
    if path.exists():
        try:
            return Image.open(path).convert("RGBA")
        except Exception as err:
            log(f"icon.png failed, drawing fallback: {err}")

    img = Image.new("RGBA", (64, 64), "#1a1a1f")
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((8, 10, 56, 54), radius=7, fill="#2d2d35", outline="#e8e8f0")
    draw.text((18, 23), "rq", fill="#e8e8f0")
    return img


def _try_apply(res: Resolution):
    try:
        apply(res)
    except Exception as err:
        log(f"tray apply failed for {res}: {err}")


def _menu(cfg: Config, on_settings, on_quit):
    try:
        cur = current()
        cur_text = f"Current: {cur.width}x{cur.height}@{cur.refresh}Hz"
    except Exception:
        cur_text = "Current: unknown"

    items = [
        pystray.MenuItem(cur_text, None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(f"Safe Resolution: {cfg.safe_resolution}", lambda *args: _try_apply(cfg.safe_resolution)),
        pystray.Menu.SEPARATOR,
    ]

    for i, preset in enumerate(cfg.presets[:3], start=1):
        tag = "risky" if not preset.is_safe else "normal"
        items.append(
            pystray.MenuItem(
                f"Preset {i}: {preset} [{tag}]",
                lambda *args, preset_arg=preset: _try_apply(preset_arg),
            )
        )

    items.extend(
        [
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Settings", lambda *args: on_settings()),
            pystray.MenuItem("Quit", lambda *args: on_quit()),
        ]
    )
    return pystray.Menu(*items)


def create_icon(cfg: Config, on_settings, on_quit):
    return pystray.Icon("resq", _icon_img(), "resq", _menu(cfg, on_settings, on_quit))


def update_menu(icon, cfg: Config, on_settings, on_quit):
    icon.menu = _menu(cfg, on_settings, on_quit)
    try:
        icon.update_menu()
    except Exception:
        pass
