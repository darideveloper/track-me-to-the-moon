"""Idle detection via pynput; falls back to 'never idle' if unavailable."""
from __future__ import annotations

import threading
import time


class IdleWatcher:
    def __init__(self) -> None:
        self.last_input = time.time()
        self._lock = threading.Lock()
        self._start_listener()

    def _touch(self, *a) -> None:
        with self._lock:
            self.last_input = time.time()

    def _start_listener(self) -> None:
        try:
            from pynput import keyboard, mouse

            kl = keyboard.Listener(on_press=self._touch)
            ml = mouse.Listener(on_move=self._touch, on_click=self._touch, on_scroll=self._touch)
            kl.daemon = ml.daemon = True
            kl.start()
            ml.start()
        except Exception:
            pass  # headless / Wayland: no idle signal, treat as active

    def is_idle(self, after_sec: int) -> bool:
        with self._lock:
            return (time.time() - self.last_input) > after_sec
