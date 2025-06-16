from time import perf_counter
from typing import Self

from fast_abtest.monitoring.interface import Exporter, MetricLabel
from fast_abtest.registred_scenario import Context


class LatencyMetric:
    def __init__(self: Self, exporter: Exporter) -> None:
        self._start_time: float = 0.0
        self._exporter = exporter

    def on_start(self: Self, context: Context) -> None:
        self._start_time = perf_counter()

    def on_end(self: Self, context: Context, is_error: bool) -> None:
        latency = perf_counter() - self._start_time
        label = MetricLabel(
            metric="latency",
            func=context.scenario,
            variant=context.variant,
            is_error=is_error,
        )
        self._exporter.record(label=label, value=latency)
