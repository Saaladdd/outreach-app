from collections.abc import Callable, Iterable
from typing import TypeVar

T = TypeVar("T")


def dedupe_by(items: Iterable[T], key_fn: Callable[[T], str]) -> list[T]:
    seen: set[str] = set()
    result: list[T] = []
    for item in items:
        key = key_fn(item).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def normalize_domain(domain: str) -> str:
    value = domain.strip().lower()
    for prefix in ("https://", "http://", "www."):
        if value.startswith(prefix):
            value = value[len(prefix) :]
    return value.split("/")[0]
