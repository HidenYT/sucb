from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, Callable, Generic, Iterator, TypeVar, cast


class State(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CBException(Exception):
    pass


class ICircuitBreaker(ABC):
    @contextmanager
    @abstractmethod
    def make_request(self) -> Iterator[None]:
        pass


CallableType = TypeVar("CallableType", bound=Callable[..., Any])


class ICircuitBreakerDecorator(ABC):
    @abstractmethod
    def with_cb(self, func: CallableType) -> CallableType:
        pass


@dataclass
class CBSettings:
    exceptions: tuple[type[Exception], ...]


SettingsType = TypeVar("SettingsType", bound=CBSettings)


class BaseCircuitBreaker(
    ICircuitBreaker,
    ICircuitBreakerDecorator,
    Generic[SettingsType],
):
    def __init__(self, settings: SettingsType, state: State = State.CLOSED):
        self._settings = settings
        self._state = state

    def _set_state(self) -> None:
        match self._state:
            case State.CLOSED:
                if self._go_closed_to_open():
                    print("Circuit breaker state OPEN")
                    self._state = State.OPEN
            case State.OPEN:
                if self._go_open_to_half_open():
                    print("Circuit breaker state HALF OPEN")
                    self._state = State.HALF_OPEN
            case State.HALF_OPEN:
                if self._go_half_open_to_open():
                    print("Circuit breaker state OPEN")
                    self._state = State.OPEN
                    return
                if self._go_half_open_to_closed():
                    print("Circuit breaker state CLOSED")
                    self._state = State.CLOSED
                    return
                print("Circuit breaker stays HALF OPEN")
        self._on_state_changed()

    @contextmanager
    def make_request(self) -> Iterator[None]:
        self._set_state()
        if self._state is State.OPEN:
            raise CBException
        try:
            yield
        except self._settings.exceptions:
            self._on_fail()
            raise
        else:
            self._on_success()

    def with_cb(self, func: CallableType) -> CallableType:
        @wraps(func)
        def inner(*args, **kwargs):
            with self.make_request():
                return func(*args, **kwargs)

        return cast(CallableType, inner)

    @abstractmethod
    def _go_closed_to_open(self) -> bool:
        pass

    @abstractmethod
    def _go_open_to_half_open(self) -> bool:
        pass

    @abstractmethod
    def _go_half_open_to_open(self) -> bool:
        pass

    @abstractmethod
    def _go_half_open_to_closed(self) -> bool:
        pass

    @abstractmethod
    def _on_state_changed(self) -> None:
        pass

    @abstractmethod
    def _on_fail(self) -> None:
        pass

    @abstractmethod
    def _on_success(self) -> None:
        pass
