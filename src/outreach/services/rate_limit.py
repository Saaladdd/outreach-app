import time
from collections.abc import Callable
from typing import TypeVar

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

T = TypeVar("T")


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {429, 500, 502, 503, 504}
    return isinstance(exc, (httpx.TimeoutException, httpx.NetworkError))


def with_retries(max_attempts: int = 3) -> Callable[[Callable[..., T]], Callable[..., T]]:
    return retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential_jitter(initial=1, max=30),
        reraise=True,
    )


def sleep_between_requests(delay_seconds: float) -> None:
    if delay_seconds > 0:
        time.sleep(delay_seconds)
