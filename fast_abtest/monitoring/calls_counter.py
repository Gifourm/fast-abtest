from typing import Self

from fast_abtest.monitoring.interface import Exporter, MetricLabel, BaseMetric
from fast_abtest.registred_scenario import Context


class CallsMetric(BaseMetric):
    def __init__(self: Self, exporter: Exporter) -> None:
        super().__init__(exporter)
        self._calls = 0

    def on_start(self: Self, context: Context) -> Context:
        with self._lock:
            self._calls += 1
        label = MetricLabel(
            metric=self.__class__.__name__,
            func=context.scenario,
            variant=context.variant,
            is_error=False,
        )
        self._exporter.record(label=label, value=1)
        return context
