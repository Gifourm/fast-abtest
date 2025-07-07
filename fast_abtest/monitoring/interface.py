from dataclasses import dataclass, field
from threading import Lock
from typing import Protocol, Self, Any

from fast_abtest.registred_scenario import Context


@dataclass
class MetricLabel:
    metric: str
    func: str
    variant: str
    is_error: bool
    tags: dict = field(default_factory=dict)


class Exporter(Protocol):
    def record(self: Self, label: MetricLabel, value: float | int): ...


class BaseMetric:
    def __init__(self: Self, exporter: Exporter) -> None:
        self._exporter = exporter
        self._lock = Lock()

    def on_start(self: Self, context: Context) -> Context:
        return context

    def on_end(self: Self, context: Context, is_error: bool) -> None: ...
