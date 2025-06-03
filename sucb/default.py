import time
from dataclasses import dataclass
from typing import TypeVar

from sucb.base import BaseCircuitBreaker, CBSettings, State


@dataclass
class DefaultCBSettings(CBSettings):
    open_timeout: float
    half_open_requests: int
    half_open_error_rate_threshold: float


DefaultSettingsType = TypeVar("DefaultSettingsType", bound=DefaultCBSettings)


class DefaultCircuitBreaker(BaseCircuitBreaker[DefaultSettingsType]):
    def __init__(
        self, settings: DefaultSettingsType, url: str, state: State = State.CLOSED
    ):
        super().__init__(settings, url, state)
        self._open_time: float | None = None
        self._half_open_requests_count = 0
        self._half_open_failed_cnt = 0
        self._open_timeout = settings.open_timeout
        self._half_open_requests_needed = settings.half_open_requests
        self._half_open_error_rate_threshold = settings.half_open_error_rate_threshold

    def _go_open_to_half_open(self) -> bool:
        if self._open_time is None:
            raise RuntimeError("Invalid state: _time_open is None in OPEN state")
        now = time.monotonic()
        return now - self._open_time >= self._open_timeout

    def _go_half_open_to_open(self) -> bool:
        if self._half_open_requests_count != self._half_open_requests_needed:
            return False
        error_rate = self._half_open_failed_cnt / self._half_open_requests_needed
        return error_rate > self._half_open_error_rate_threshold

    def _go_half_open_to_closed(self) -> bool:
        if self._half_open_requests_count != self._half_open_requests_needed:
            return False
        error_rate = self._half_open_failed_cnt / self._half_open_requests_needed
        return error_rate <= self._half_open_error_rate_threshold

    def _on_state_changed(self) -> None:
        if self._state is State.OPEN:
            self._open_time = time.monotonic()

    def _on_fail(self) -> None:
        if self._state is State.HALF_OPEN:
            self._half_open_failed_cnt += 1
            self._half_open_requests_count += 1

    def _on_success(self) -> None:
        if self._state is State.HALF_OPEN:
            self._half_open_requests_count += 1
