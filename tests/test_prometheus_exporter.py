import pytest
import requests
from fastapi import FastAPI
from threading import Thread
from fast_abtest import PrometheusExporter, MetricLabel, Metric
from fast_abtest.config import ABTestConfig


@pytest.fixture(scope="module")
def prometheus_exporter():
    exporter = PrometheusExporter(
        metrics=[Metric.CALLS_TOTAL.value.__name__, Metric.ERRORS_TOTAL.value.__name__, Metric.LATENCY.value.__name__],
        func_name="test_metrics",
        labelnames=["endpoint", "status"],
        port=9091,
    )
    yield exporter


@pytest.fixture(scope="module")
def test_app(prometheus_exporter):
    app = FastAPI()

    @app.get("/test")
    async def test_route(status: str = "success"):
        prometheus_exporter.record(
            label=MetricLabel(
                metric=Metric.CALLS_TOTAL.value.__name__,
                func="test_route",
                variant="v1",
                is_error=(status == "error"),
                tags={"endpoint": "/test", "status": status},
            ),
            value=1,
        )
        return {"status": status}

    return app


@pytest.fixture(scope="module")
def test_client(test_app):
    import uvicorn

    server_thread = Thread(
        target=uvicorn.run,
        args=(test_app,),
        kwargs={"host": "localhost", "port": 9090},
        daemon=True,
    )
    server_thread.start()
    yield requests.Session()


def test_exporter_setup(prometheus_exporter):
    """Test the initialization of metrics"""
    for metric in [Metric.ERRORS_TOTAL.value.__name__, Metric.CALLS_TOTAL.value.__name__]:
        assert f"abtest_test_metrics_{metric}" in prometheus_exporter._metrics

    assert f"abtest_test_metrics_{Metric.LATENCY.value.__name__}" in prometheus_exporter._histograms
    assert prometheus_exporter._labelnames == {"variant", "func", "metric", "endpoint", "status"}


def test_record_metric(prometheus_exporter):
    """Test the recording of metrics"""
    base_metric = Metric.CALLS_TOTAL.value.__name__
    metric_name = f"test_metrics_{base_metric}"

    func = "sample_func"
    variant = "A"
    endpoint = "/sample"
    status = "200"

    prometheus_exporter.record(
        label=MetricLabel(
            metric=base_metric,
            func=func,
            variant=variant,
            is_error=False,
            tags={"endpoint": endpoint, "status": status},
        ),
        value=1,
    )

    response = requests.get("http://localhost:9091/metrics")
    result = "abtest_" + metric_name
    assert result in response.text


def test_fastapi_integration(test_client, prometheus_exporter):
    """Test the generation of metrics when calling FastAPI router"""
    response = test_client.get("http://localhost:9090/test?status=success")
    assert response.json()["status"] == "success"

    metrics_response = requests.get("http://localhost:9091/metrics")
    metrics = metrics_response.text

    expected_metric = f"test_metrics_{Metric.CALLS_TOTAL.value.__name__}_total"
    assert expected_metric in metrics and 'status="success"' in metrics
    assert expected_metric in metrics and 'status="error"' not in metrics


def test_missing_labels(prometheus_exporter):
    """Test the handling of the absence of optional labels."""
    base_metric = Metric.CALLS_TOTAL.value.__name__
    prometheus_exporter.record(
        label=MetricLabel(
            metric=base_metric,
            func="no_tags_func",
            variant="B",
            is_error=False,
        ),
        value=1,
    )

    metrics = requests.get("http://localhost:9091/metrics").text
    expected_metric = f"test_metrics_{base_metric}_total"
    assert expected_metric in metrics
    assert "no_tags_func" in metrics
    assert 'endpoint=""' in metrics


def test_invalid_port():
    """Test that ABTestConfig rejects invalid ports"""
    with pytest.raises(ValueError, match="Port must be between 1024 and 65535"):
        ABTestConfig(prometheus_port=99999)

    with pytest.raises(ValueError):
        ABTestConfig(prometheus_port=-1)


def test_valid_port_config():
    """Test that the port is being transmitted correctly through the configurator."""
    config = ABTestConfig(prometheus_port=9091)
    exporter = PrometheusExporter(
        metrics=["test"],
        func_name="test_func",
        labelnames=[],
        port=config.prometheus_port,
    )
    assert exporter._labelnames == {"variant", "func", "metric"}


def test_metrics_format(prometheus_exporter):
    """Test for compliance with the Prometheus format."""
    base_metric = "LatencyMetric"
    metric_name = f"test_metrics_{base_metric}"

    prometheus_exporter.record(
        label=MetricLabel(
            metric=base_metric, func="timed_func", variant="C", is_error=False, tags={"endpoint": "/timed"}
        ),
        value=0.35,
    )

    metrics = requests.get("http://localhost:9091/metrics").text
    bucket = f"{metric_name}_bucket"
    count = f"{metric_name}_count"
    sum_info = f"{metric_name}_sum"
    assert bucket in metrics and 'le="0.5"' in metrics
    assert count in metrics
    assert sum_info in metrics
