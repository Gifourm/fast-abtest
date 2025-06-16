from typing import Self

from fast_abtest.monitoring.interface import Exporter, Label
from fast_abtest.registred_scenario import Context


class CallsMetric:
    def __init__(self: Self, exporter: Exporter) -> None:
        self._exporter = exporter

    def on_start(self: Self, context: Context) -> None:
        label = Label(
            metric="calls_total",
            func=context.scenario,
            variant=context.variant,
            is_error=False,
        )
        self._exporter.record(label=label, value=1)

    def on_end(self: Self, context: Context, is_error: bool) -> None: ...
