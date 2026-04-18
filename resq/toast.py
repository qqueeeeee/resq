from .logger import log


class ToastNotifier:
    def __init__(self):
        try:
            from win10toast import ToastNotifier as WinToast

            self._toast = WinToast()
        except Exception as err:
            self._toast = None
            log(f"toast disabled: {err}")

    def show_toast(self, title: str, message: str, duration: int = 3):
        if not self._toast:
            log(f"notify: {title} - {message}")
            return

        try:
            self._toast.show_toast(title, message, duration=duration, threaded=True)
        except Exception as err:
            log(f"toast failed: {err}")
