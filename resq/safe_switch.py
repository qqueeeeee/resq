from contextlib import contextmanager

from .display import apply, current
from .models import Resolution


class SafeSwitch:
    """Switches to a resolution and jumps back if the wrapped work blows up."""

    def __init__(self, res: Resolution):
        self.res = res
        self.prev = None

    def __enter__(self):
        self.prev = current()
        apply(self.res)
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type and self.prev:
            apply(self.prev)
        return False


@contextmanager
def temp_resolution(res: Resolution):
    prev = current()
    apply(res)
    try:
        yield
    finally:
        apply(prev)
