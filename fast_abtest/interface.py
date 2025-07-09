from dataclasses import dataclass, field
from threading import Lock
from typing import Protocol, Callable, TypeVar, Generic, Self

from fast_abtest.monitoring.interface import Exporter, Context

R = TypeVar("R")
R_co = TypeVar("R_co", covariant=True)


class ScenarioHandler(Protocol[R_co]):
    __name__: str

    def __call__(self, *args, **kwargs) -> R_co: ...


@dataclass
class _ScenarioVariant(Generic[R]):
    handler: ScenarioHandler[R]
    traffic_percent: int
    threshold: float
    call_count: int = 0
    error_count: int = 0
    is_active: bool = True
    _lock: Lock = field(default_factory=Lock, init=False)

    def increment_call(self: Self) -> None:
        with self._lock:
            self.call_count += 1

    def threshold_exceeded(self: Self) -> bool:
        with self._lock:
            self.error_count += 1
            if self.call_count > 10 and self.error_count / max(self.call_count, 1) > self.threshold:
                self.is_active = False
                return True
        return False


class ABTestFunction(Protocol[R]):
    def __call__(self: Self, *args, **kwargs) -> R: ...

    def register_variant(
        self: Self,
        traffic_percent: int,
        disable_threshold: float = 1.0,
    ) -> Callable[[ScenarioHandler[R]], ScenarioHandler[R]]: ...

    def enable_variant(self: Self, variant_name: str) -> None: ...


class Metric(Protocol):
    def __init__(
        self: Self,
        exporter: Exporter,  # noqa
    ) -> None: ...

    def on_start(self: Self, context: Context) -> Context: ...

    def on_end(self: Self, context: Context, is_error: bool) -> None: ...
