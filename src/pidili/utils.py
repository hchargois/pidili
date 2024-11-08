import time
from dataclasses import dataclass
from typing import TypeVar, Callable, Generic

T = TypeVar("T")


class timed:
    def __init__(self, logFunc: Callable[[str], None], name: str = ""):
        self.logFunc = logFunc
        self.name = name

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        end = time.perf_counter()
        if self.name:
            self.name += " "
        self.logFunc(f"{self.name}took {1000*(end - self.start):.3f} ms")


Number = TypeVar("Number", int, float)


def clamp(val: Number, low: Number, high: Number) -> Number:
    if val < low:
        return low
    if val > high:
        return high
    return val


@dataclass(slots=True)
class Box(Generic[T]):
    """A mutable container for a single value. Used to work around the
    frozenness of the widgets."""

    value: T | None = None

    def get(self) -> T:
        assert self.value is not None
        return self.value
