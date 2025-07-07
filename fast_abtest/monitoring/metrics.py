from enum import Enum
from typing import Self

from fast_abtest.monitoring.calls_counter import CallsMetric
from fast_abtest.monitoring.errors_counter import ErrorsMetric
from fast_abtest.monitoring.latency import LatencyMetric


class Metric(Enum):
    LATENCY = LatencyMetric
    CALLS_TOTAL = CallsMetric
    ERRORS_TOTAL = ErrorsMetric

    def __str__(self: Self) -> str:
        return str(self.value)
