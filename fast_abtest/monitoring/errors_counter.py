from typing import Self

from fast_abtest.monitoring.interface import MetricLabel, Exporter, BaseMetric
from fast_abtest.registred_scenario import Context


class ErrorsMetric(BaseMetric):
    def __init__(self: Self, exporter: Exporter) -> None:
        super().__init__(exporter)
        self._errors = 0

    def on_end(self: Self, context: Context, is_error: bool) -> None:
        if is_error:
            with self._lock:
                self._errors += 1
            label = MetricLabel(
                metric=self.__class__.__name__,
                func=context.scenario,
                variant=context.variant,
                is_error=True,
            )
            self._exporter.record(label=label, value=1)
