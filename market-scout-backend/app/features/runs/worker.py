"""A single background thread that executes queued runs one at a time.

In-process on purpose for now: one worker keeps SQLite write contention low and needs no
extra infrastructure. When the app is deployed this is the piece to swap for a real queue --
callers only use ``enqueue``.
"""
import logging
import queue
import threading
from collections.abc import Callable

logger = logging.getLogger(__name__)


class RunWorker:
    def __init__(self) -> None:
        self._queue: queue.Queue[int] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._executor: Callable[[int], None] | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, executor: Callable[[int], None]) -> None:
        if self.is_running:
            return
        self._executor = executor
        self._stop_event.clear()
        # Daemon: a run in flight when the server stops is picked up as "interrupted" on the
        # next start rather than blocking shutdown.
        self._thread = threading.Thread(target=self._loop, name="run-worker", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout)
        self._thread = None

    def enqueue(self, run_id: int) -> None:
        self._queue.put(run_id)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                run_id = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                assert self._executor is not None
                self._executor(run_id)
            except Exception:
                # execute_run handles its own errors; this only guards the thread itself.
                logger.exception("Run %s crashed the worker loop", run_id)


worker = RunWorker()
