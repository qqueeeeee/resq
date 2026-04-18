import json
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_HOTKEYS = {
    "safe": "win+alt+r",
    "preset1": "win+alt+1",
    "preset2": "win+alt+2",
    "preset3": "win+alt+3",
    "settings": "win+alt+c",
}


@dataclass
class Resolution:
    width: int
    height: int
    refresh: int = 60
    label: str = ""
    is_safe: bool = False

    def __str__(self):
        name = f" ({self.label})" if self.label else ""
        return f"{self.width}x{self.height}@{self.refresh}Hz{name}"

    def __eq__(self, other):
        if not isinstance(other, Resolution):
            return False
        return (
            self.width == other.width
            and self.height == other.height
            and self.refresh == other.refresh
        )

    def to_dict(self):
        data = asdict(self)
        if not data["label"]:
            data.pop("label")
        if not data["is_safe"]:
            data.pop("is_safe")
        return data

    @classmethod
    def from_dict(cls, data):
        if isinstance(data, cls):
            return data
        return cls(
            width=int(data.get("width", 1920)),
            height=int(data.get("height", 1080)),
            refresh=int(data.get("refresh", 60)),
            label=data.get("label", ""),
            is_safe=bool(data.get("is_safe", False)),
        )


@dataclass
class Config:
    safe_resolution: Resolution
    presets: list[Resolution]
    hotkeys: dict[str, str]
    safe_boot_guard: bool = True
    safe_boot_timeout: int = 10
    minimize_to_tray: bool = True
    path: str = "config.json"

    def save(self, path: str | None = None):
        config_path = Path(path or self.path)
        with config_path.open("w", encoding="utf-8") as file:
            json.dump(self.to_dict(), file, indent=4)
            file.write("\n")

    def to_dict(self):
        return {
            "safe_resolution": self.safe_resolution.to_dict(),
            "presets": [p.to_dict() for p in self.presets],
            "hotkeys": self.hotkeys,
            "safe_boot_guard": self.safe_boot_guard,
            "safe_boot_timeout": self.safe_boot_timeout,
            "minimize_to_tray": self.minimize_to_tray,
        }

    @classmethod
    def default(cls, path: str = "config.json"):
        safe = Resolution(1920, 1080, 60, "Safe", True)
        presets = [
            Resolution(2560, 1080, 60, "Ultrawide"),
            Resolution(1920, 1080, 144, "144Hz", True),
            Resolution(1280, 720, 60, "720p", True),
        ]
        return cls(safe, presets, DEFAULT_HOTKEYS.copy(), True, 10, True, path)

    @classmethod
    def load(cls, path: str = "config.json"):
        config_path = Path(path)
        if not config_path.exists():
            cfg = cls.default(str(config_path))
            cfg.save()
            return cfg

        with config_path.open(encoding="utf-8") as file:
            data = json.load(file)

        safe = Resolution.from_dict(data.get("safe_resolution", {}))
        safe.is_safe = True
        if not safe.label:
            safe.label = "Safe"

        raw_presets = data.get("presets", [])
        presets = []
        defaults = cls.default().presets
        for i, raw in enumerate(raw_presets):
            res = Resolution.from_dict(raw)
            if "is_safe" not in raw and i < len(defaults):
                # old configs did not have this field, keep the sane default
                res.is_safe = defaults[i].is_safe
            presets.append(res)
        while len(presets) < 3:
            presets.append(defaults[len(presets)])
        presets = presets[:3]

        hotkeys = DEFAULT_HOTKEYS.copy()
        hotkeys.update(data.get("hotkeys", {}))
        hotkeys = {k: v.replace("windows+", "win+") for k, v in hotkeys.items()}

        return cls(
            safe_resolution=safe,
            presets=presets,
            hotkeys=hotkeys,
            safe_boot_guard=bool(data.get("safe_boot_guard", True)),
            safe_boot_timeout=int(data.get("safe_boot_timeout", 10)),
            minimize_to_tray=bool(data.get("minimize_to_tray", True)),
            path=str(config_path),
        )

    def is_known_safe(self, res: Resolution) -> bool:
        if res == self.safe_resolution:
            return True
        return any(preset == res and preset.is_safe for preset in self.presets)

    def is_risky(self, res: Resolution) -> bool:
        return any(preset == res and not preset.is_safe for preset in self.presets)

    def guard_label(self, res: Resolution) -> str:
        if res == self.safe_resolution:
            return "safe resolution"
        for preset in self.presets:
            if preset == res:
                return "risky custom preset" if not preset.is_safe else "normal preset"
        return "normal Windows mode"
