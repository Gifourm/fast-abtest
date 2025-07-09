from contextvars import ContextVar
from time import perf_counter
from typing import Self

from fast_abtest.monitoring.interface import Exporter, MetricLabel, BaseMetric
from fast_abtest.registred_scenario import Context


class LatencyMetric(BaseMetric):
    def __init__(self: Self, exporter: Exporter) -> None:
        super().__init__(exporter)
        self._start_time: ContextVar[float] = ContextVar("start_time")

    def on_start(self: Self, context: Context) -> Context:
        self._start_time.set(perf_counter())
        return context

    def on_end(self: Self, context: Context, is_error: bool) -> None:
        latency = perf_counter() - self._start_time.get()
        label = MetricLabel(
            metric=self.__class__.__name__,
            func=context.scenario,
            variant=context.variant,
            is_error=is_error,
        )
        self._exporter.record(label=label, value=latency)
