from fast_abtest.decorator import ab_test
from fast_abtest.monitoring import MetricLabel, Metric
from fast_abtest.interface import Exporter, Context, Metric as IMetric
from fast_abtest.config import ABTestConfig, ConfigManager

from fast_abtest.exporter.prometheus import PrometheusExporter as _PrometheusExporter

__version__ = "0.3.0"
__version_info__ = (0, 3, 0)

__all__ = [
    "ab_test",
    "Metric",
    "MetricLabel",
    "Exporter",
    "Context",
    "ABTestConfig",
    "ConfigManager",
    "PrometheusExporter",
    "IMetric",
]

PrometheusExporter = _PrometheusExporter
