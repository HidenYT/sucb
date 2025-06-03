import time
from datetime import timedelta

import requests

from sucb.base import ICircuitBreaker
from sucb.cb import (PercentageBasedCB, PercentageBasedCBSettings, TimeBasedCB,
                     TimeBasedCBSettings)

cb: ICircuitBreaker = TimeBasedCB(
    TimeBasedCBSettings(
        exceptions=(
            requests.ReadTimeout,
            requests.ConnectionError,
            requests.RequestException,
        ),
        open_timeout=0.01,
        half_open_requests=2,
        half_open_error_rate_threshold=0.1,
        closed_error_cnt_threshold=2,
        time_window_width=timedelta(microseconds=1),
    ),
    "http://some-url-ww.example",
)

cb = PercentageBasedCB(
    PercentageBasedCBSettings(
        exceptions=(
            requests.ReadTimeout,
            requests.ConnectionError,
            requests.RequestException,
        ),
        open_timeout=0.01,
        half_open_requests=2,
        half_open_error_rate_threshold=0.5,
        closed_error_rate_threshold=0.5,
        requests_window_width=4,
    ),
    "http://some-url-ww.example",
)


def make_request(cb: ICircuitBreaker, url="http://some-url-ww.example"):
    print("Making request to", url)
    try:
        with cb.make_request():
            requests.get(url)
    except Exception as e:
        print(type(e))
    else:
        print("Okay")


make_request(cb)
time.sleep(0.06)
make_request(cb)
time.sleep(0.06)
make_request(cb)
time.sleep(0.06)
make_request(cb, "http://google.com")
make_request(cb, "http://google.com")
make_request(cb, "http://google.com")
