from typing import Self

from fast_abtest.interface import Metric
from fast_abtest.registred_scenario import Context


class MetricRecorder:
    def __init__(
        self: Self,
        metrics: list[Metric],
        context: Context,
    ) -> None:
        self._metrics = metrics
        self._context = context

    def __enter__(self: Self) -> Self:
        for metric in self._metrics:
            metric.on_start(context=self._context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        is_error = exc_type is not None
        for metric in self._metrics:
            metric.on_end(context=self._context, is_error=is_error)
