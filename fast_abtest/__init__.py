from fast_abtest.decorator import ab_test
from fast_abtest.monitoring import MetricLabel, Metric
from fast_abtest.interface import Exporter, Context, Metric as IMetric
from fast_abtest.config import ABTestConfig, ConfigManager
from fast_abtest.exporter.prometheus import PrometheusExporter as _PrometheusExporter
from fast_abtest.depends_compatibility import enable_dependency_support

__version__ = "0.4.0"
__version_info__ = (0, 4, 0)

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
    "enable_dependency_support",
]

PrometheusExporter = _PrometheusExporter
