import time
from collections import deque
from dataclasses import dataclass
from datetime import timedelta

from sucb.base import State
from sucb.default import DefaultCBSettings, DefaultCircuitBreaker


@dataclass
class TimeBasedCBSettings(DefaultCBSettings):
    closed_error_cnt_threshold: int
    time_window_width: timedelta


class TimeBasedCB(DefaultCircuitBreaker[TimeBasedCBSettings]):
    def __init__(
        self, settings: TimeBasedCBSettings, url: str, state: State = State.CLOSED
    ):
        super().__init__(settings, url, state)
        self._q = deque[float]()
        self._closed_error_cnt_threshold = self._settings.closed_error_cnt_threshold
        self._closed_window_timeout = self._settings.time_window_width.total_seconds()

    def _go_closed_to_open(self) -> bool:
        self._clear_queue()
        return len(self._q) >= self._closed_error_cnt_threshold

    def _on_fail(self) -> None:
        super()._on_fail()
        self._q.append(time.monotonic())

    def _clear_queue(self) -> None:
        now = time.monotonic()
        while self._q and now - self._q[0] > self._closed_window_timeout:
            self._q.popleft()


@dataclass
class PercentageBasedCBSettings(DefaultCBSettings):
    closed_error_rate_threshold: float
    requests_window_width: int


class PercentageBasedCB(DefaultCircuitBreaker[PercentageBasedCBSettings]):
    def __init__(
        self, settings: PercentageBasedCBSettings, url: str, state: State = State.CLOSED
    ):
        super().__init__(settings, url, state)
        self._q = deque[bool]()
        self._closed_error_rate_threshold = self._settings.closed_error_rate_threshold
        self._requests_window_width = self._settings.requests_window_width
        self._closed_errors_cnt = 0

    def _go_closed_to_open(self) -> bool:
        return (
            self._closed_errors_cnt / self._requests_window_width
            >= self._closed_error_rate_threshold
        )

    def _on_fail(self) -> None:
        super()._on_fail()
        self._append_to_queue(False)

    def _on_success(self) -> None:
        super()._on_success()
        self._append_to_queue(True)

    def _append_to_queue(self, val: bool) -> None:
        self._q.append(val)
        if not val:
            self._closed_errors_cnt += 1
        if len(self._q) > self._requests_window_width:
            if not self._q.popleft():
                self._closed_errors_cnt -= 1
