import functools
import time

from .logger import log
from .toast import ToastNotifier

toaster = ToastNotifier()


def log_operation(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        log(f"{func.__name__}({', '.join(map(str, args))}) -> {result} in {time.time() - start:.2f}s")
        return result

    return wrapper


def require_supported(func):
    @functools.wraps(func)
    def wrapper(res, *args, **kwargs):
        from .display import is_supported

        if not is_supported(res):
            raise ValueError(f"{res} is not reported by Windows for this display")
        return func(res, *args, **kwargs)

    return wrapper


def notify_on_change(func):
    @functools.wraps(func)
    def wrapper(res, *args, **kwargs):
        ok = func(res, *args, **kwargs)
        if ok:
            toaster.show_toast("resq", f"Resolution changed to {res}", duration=3)
        return ok

    return wrapper
