import threading
from pathlib import Path
from urllib.parse import quote

from .display import apply, current
from .logger import log
from .models import Config


class GuardApi:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.window = None
        self.done = threading.Event()

    def keep(self):
        log("startup resolution kept")
        self._close()
        return {"ok": True}

    def revert_now(self):
        try:
            log(f"startup guard reverting to {self.cfg.safe_resolution}")
            apply(self.cfg.safe_resolution)
            return {"ok": True}
        except Exception as err:
            log(f"startup guard revert failed: {err}", "error")
            return {"ok": False, "error": str(err)}
        finally:
            self._close()

    def _close(self):
        self.done.set()
        if self.window:
            try:
                self.window.destroy()
            except Exception:
                pass


class SafeBootGuard:
    """Startup panic button for when CRU leaves Windows in a bad mode."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.cur = None

    def check_and_guard(self):
        if not self.cfg.safe_boot_guard:
            return

        self.cur = current()
        status = self.cfg.guard_label(self.cur)
        if not self.cfg.is_risky(self.cur):
            return

        log(f"risky startup resolution detected: {self.cur} ({status})")
        thread = threading.Thread(target=self._run_guard, name="resq-guard", daemon=True)
        thread.start()
        thread.join()

    def _run_guard(self):
        try:
            import webview
        except Exception as err:
            log(f"pywebview unavailable for guard: {err}", "error")
            return

        api = GuardApi(self.cfg)
        html_path = Path(__file__).resolve().parent / "ui" / "guard.html"
        mode = quote(f"{self.cur.width}x{self.cur.height} @ {self.cur.refresh}Hz")
        url = f"{html_path.as_uri()}?res={mode}&timeout={int(self.cfg.safe_boot_timeout)}"

        try:
            api.window = webview.create_window(
                "resq guard",
                url,
                js_api=api,
                width=430,
                height=160,
                resizable=False,
                frameless=True,
                on_top=True,
            )
            webview.start(func=None)
            api.done.set()
        except Exception as err:
            log(f"guard webview failed: {err}", "error")
            api.done.set()
