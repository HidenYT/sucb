# sucb - Simple user-friendly circuit breaker for Python

Example usage:
```python
import requests
from sucb.cb import PercentageBasedCB, PercentageBasedCBSettings
from sucb.decor import with_cb

cb = PercentageBasedCB(
    PercentageBasedCBSettings(
        # exceptions caught by CB
        exceptions=(
            requests.ReadTimeout,
            requests.ConnectionError,
            requests.RequestException,
        ),
        # error rate in CLOSED to go to OPEN
        closed_error_rate_threshold=0.5,
        # window size for last requests in CLOSED
        requests_window_width=4,
        # how long CB stays OPEN before going to HALF-OPEN
        open_timeout=0.01,
        # how many requests CB sends when HALF-OPEN
        half_open_requests=2,
        # acceptable error rate during HALF-OPEN to go to CLOSED
        half_open_error_rate_threshold=0.5,
    ),
)

# Either use as a context-manager
with cb.make_request():
    requests.get("http://some-url-ww.example")

# Or as a decorator
@cb.with_cb
def get():
    requests.get("http://some-url-ww.example")


# Or as a decorator without creation of a CB object

@with_cb(
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
)
def get():
    requests.get("http://some-url-ww.example")
```
