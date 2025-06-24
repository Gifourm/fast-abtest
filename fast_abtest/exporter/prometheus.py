from threading import Lock
from typing import Self, Iterable

from prometheus_client import Counter, Histogram

from fast_abtest import MetricLabel
from fast_abtest.interface import Metric


class PrometheusExporter:
    def __init__(
        self: Self,
        metrics: list[Metric],
        lablenames: Iterable[str],
    ) -> None:
        self._metrics: dict[str, Counter] = {}
        self._histograms: dict[str, Histogram] = {}
        for metric in metrics:
            self._add_metric(metric)
        self._lock = Lock()
        self._labelnames = lablenames

    def record(
        self: Self,
        label: MetricLabel,
        value: float | int,
    ) -> None:
        if not all(tag in self._labelnames for tag in label.tags):
            raise ValueError(f"Unknown tags: {label.tags}. Expected: {self._labelnames}")

        labels = {tag: getattr(label, tag, "") for tag in self._labelnames}
        if label.metric.endswith("latency"):
            self._histograms[label.metric].labels(**labels).observe(value)
        else:
            self._metrics[label.metric].labels(**labels).inc()

    def _add_metric(
        self: Self,
        metric: Metric,
    ) -> None:
        metric_name = str(metric)
        with self._lock:
            if metric_name in (self._histograms if "latency" in metric_name.lower() else self._metrics):
                return

            if "latency" in metric_name.lower():
                self._histograms[metric_name] = Histogram(
                    name=metric_name,
                    documentation=f"{metric_name} ('histogram')",
                    buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
                    labelnames=self._labelnames,
                )
            else:
                self._metrics[metric_name] = Counter(
                    name=metric_name,
                    documentation=f"{metric_name} ('counter')",
                    labelnames=self._labelnames,
                )
