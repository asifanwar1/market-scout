import logging
import queue
import threading
from collections.abc import Callable

STOP_TIMEOUT_SECONDS = 5.0
POLL_SECONDS = 0.5


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
        self._thread = threading.Thread(target=self._loop, name="run-worker", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = STOP_TIMEOUT_SECONDS) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout)
        self._thread = None

    def enqueue(self, run_id: int) -> None:
        self._queue.put(run_id)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                run_id = self._queue.get(timeout=POLL_SECONDS)
            except queue.Empty:
                continue
            try:
                assert self._executor is not None
                self._executor(run_id)
            except Exception:
                logger.exception("Run %s crashed the worker loop", run_id)


worker = RunWorker()
