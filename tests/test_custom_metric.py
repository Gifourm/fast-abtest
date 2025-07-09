import pytest
from typing import Any
from fast_abtest import ab_test, Exporter, Context, Metric
from fast_abtest.config import ABTestConfig
from fast_abtest.monitoring import MetricLabel


class CustomMetric:
    def __init__(self, exporter: Exporter):
        self._exporter = exporter
        self.start_context = None
        self.end_calls = 0

    def on_start(self, context: Context) -> Context:
        self.start_context = context
        return context

    def on_end(self, context: Context, is_error: bool) -> None:
        self.end_calls += 1
        self._exporter.record(
            label=MetricLabel(
                metric=self.__class__.__name__,
                func=context.scenario,
                variant=context.variant,
                is_error=is_error,
                tags={"custom_tag": "test"},
            ),
            value=1.0,
        )


@pytest.fixture
def custom_metric_class():
    return CustomMetric


@pytest.fixture
def test_config():
    return ABTestConfig(prometheus_port=9093)


def test_custom_metric_integration(custom_metric_class, test_config) -> None:
    """Test the integration of a custom metric with a decorator."""

    @ab_test(metrics=[custom_metric_class])
    def test_function():
        return "success"

    result = test_function()
    assert result == "success"

    metric_instance = test_function._metric_recorder._metrics[0]
    assert metric_instance.start_context is not None
    assert metric_instance.end_calls == 1


def test_custom_metric_with_fastapi(custom_metric_class, test_config):
    """Test the operation in the asynchronous FastAPI endpoint."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()

    @app.get("/test")
    @ab_test(metrics=[custom_metric_class])
    async def test_endpoint():
        return {"status": "ok"}

    client = TestClient(app)
    response = client.get("/test")
    assert response.status_code == 200

    metric_instance = test_endpoint._metric_recorder._metrics[0]
    assert metric_instance.end_calls == 1
    assert "test_endpoint" in str(metric_instance.start_context.scenario)


def test_custom_metric_with_exporter(custom_metric_class, test_config):
    """Test the custom metric is used correctly by the exporter."""

    class MockExporter:
        def __init__(self):
            self.recorded = []

        def record(self, label: MetricLabel, value: float | int) -> None:
            self.recorded.append((label, value))

    mock_exporter = MockExporter()
    metric = custom_metric_class(mock_exporter)
    test_context = Context(scenario="test", variant="A", timestamp=123)

    metric.on_start(test_context)
    metric.on_end(test_context, is_error=False)

    assert len(mock_exporter.recorded) == 1
    label, value = mock_exporter.recorded[0]
    assert label.metric == "CustomMetric"
    assert value == 1.0


def test_metric_names_uniqueness():
    """Test the possibility of creating multiple branches of variants without label conflict"""

    @ab_test(metrics=[Metric.LATENCY])
    def func1():
        pass

    @ab_test(metrics=[Metric.LATENCY])
    def func2():
        pass

    assert func1._metric_recorder._metrics[0]._exporter._func_name == "func1"
    assert func2._metric_recorder._metrics[0]._exporter._func_name == "func2"
    assert any("func1_Latency" in metric for metric in func1._metric_recorder._metrics[0]._exporter._histograms)
    assert any("func2_Latency" in metric for metric in func2._metric_recorder._metrics[0]._exporter._histograms)
