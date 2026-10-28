"""At most N analyses run at once. submit() waits until a slot is free."""
from __future__ import annotations

import os
import threading

_MAX = 8


class WorkerPool:
    def __init__(self, size: int):
        if size < 1:
            raise ValueError("pool size")
        self.size = size
        self._sem = threading.Semaphore(size)
        self._meta = threading.Lock()
        self._waiters = 0

    @property
    def waiters(self) -> int:
        with self._meta:
            return self._waiters

    def submit(self, fn) -> None:
        """Block until a slot is free, then run fn on a daemon thread. The slot is held until fn returns."""
        with self._meta:
            self._waiters += 1
        self._sem.acquire()
        with self._meta:
            self._waiters -= 1

        def run() -> None:
            try:
                fn()
            finally:
                self._sem.release()

        threading.Thread(target=run, daemon=True, name="saqr-worker").start()


def worker_count() -> int:
    raw = os.environ.get("SAQR_WORKERS", "2")
    try:
        n = int(raw)
    except ValueError:
        n = 2
    return min(_MAX, max(1, n))


_pool: WorkerPool | None = None
_pool_guard = threading.Lock()


def get_pool() -> WorkerPool:
    global _pool
    with _pool_guard:
        if _pool is None:
            _pool = WorkerPool(worker_count())
        return _pool
