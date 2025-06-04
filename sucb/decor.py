from functools import wraps
from typing import Any, Callable, TypeVar, cast

from sucb.base import BaseCircuitBreaker, CBSettings
from sucb.cb import PercentageBasedCB, PercentageBasedCBSettings

CallableType = TypeVar("CallableType", bound=Callable[..., Any])


def with_cb(
    cb_cls: type[BaseCircuitBreaker] = PercentageBasedCB,
    cb_settings_cls: type[CBSettings] = PercentageBasedCBSettings,
    *args,
    **kwargs,
) -> Callable[[CallableType], CallableType]:
    cb = cb_cls(cb_settings_cls(*args, **kwargs))

    def decor(func: CallableType) -> CallableType:
        @wraps(func)
        @cb.with_cb
        def inner(*args, **kwargs):
            return func(*args, **kwargs)

        return cast(CallableType, inner)

    return decor
