from threading import Lock
from typing import Self, Iterable

from prometheus_client import Counter, Histogram

from fast_abtest.monitoring.interface import MetricLabel


class PrometheusExporter:
    REQUIRED_LABELS = {"variant", "func", "metric"}

    def __init__(
        self: Self,
        metrics: Iterable[str],
        func_name: str,
        labelnames: Iterable[str],
        port: int,
    ) -> None:
        from prometheus_client import start_http_server

        start_http_server(port)

        self._metrics: dict[str, Counter] = {}
        self._func_name = func_name
        self._histograms: dict[str, Histogram] = {}
        self._lock = Lock()
        self._labelnames = set(labelnames).union(self.REQUIRED_LABELS)
        for metric in metrics:
            self._add_metric(metric)

    def record(self: Self, label: MetricLabel, value: float | int) -> None:
        """Records a metric value with labels.
        Args:
            label: MetricLabel containing required fields (variant, func, metric)
                  and optional tags.
            value: Numeric value to record.
        Note:
            Only tags present in `labelnames` will be used.
        """
        metric_name = f"abtest_{self._func_name}_{label.metric}"
        base_labels = {"variant": label.variant, "func": label.func, "metric": metric_name}
        extra_labels = {k: v for k, v in label.tags.items() if k in self._labelnames}
        missing_labels = {k: "" for k in self._labelnames if k not in base_labels and k not in extra_labels}
        labels = {**base_labels, **extra_labels, **missing_labels}
        if "latency" in metric_name.lower():
            self._histograms[metric_name].labels(**labels).observe(value)
        else:
            self._metrics[metric_name].labels(**labels).inc()

    def _add_metric(
        self: Self,
        metric_name: str,
    ) -> None:
        metric_name = f"abtest_{self._func_name}_{metric_name}"
        with self._lock:
            # if metric_name in (self._histograms if "latency" in metric_name.lower() else self._metrics):
            #     return

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
