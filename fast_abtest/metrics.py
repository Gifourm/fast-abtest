from enum import Enum


class Metric(Enum):
    LATENCY: latency_metric
    ERROR_RATE: error_rate_metric