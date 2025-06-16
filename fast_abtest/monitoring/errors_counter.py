from typing import Self

from fast_abtest.monitoring.interface import Exporter, Label
from fast_abtest.registred_scenario import Context


class ErrorsMetric:
    def __init__(self: Self, exporter: Exporter) -> None:
        self._exporter = exporter

    def on_start(self: Self, context: Context) -> None: ...

    def on_end(self: Self, context: Context, is_error: bool) -> None:
        if is_error:
            label = Label(
                metric="errors_total",
                func=context.scenario,
                variant=context.variant,
                is_error=True,
            )
            self._exporter.record(label=label, value=1)
