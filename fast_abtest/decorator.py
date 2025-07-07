from collections.abc import Iterable
from enum import Enum
from functools import wraps
from inspect import iscoroutinefunction, markcoroutinefunction
from logging import Logger, getLogger
from typing import Callable

from fast_abtest.exporter import PrometheusExporter
from .config import ConfigManager
from .interface import ABTestFunction, Metric, R, ScenarioHandler, _ScenarioVariant  # type: ignore
from .monitoring.interface import Exporter
from .monitoring.metrics import Metric as MetricEnum
from .registred_scenario import (  # type: ignore
    RegisteredScenario,
)


def _get_metric_class_name(metric: type[Metric] | MetricEnum):
    if isinstance(metric, Enum):
        return metric.value.__name__
    return metric.__class__.__name__


def _create_registered_scenario(
    func: ScenarioHandler[R],
    metrics: Iterable[type[Metric]],
    exporter: type[Exporter],
    logger: Logger,
) -> RegisteredScenario[R]:
    config = ConfigManager.get_config()
    main_scenario = _ScenarioVariant(
        handler=func,
        traffic_percent=100,
        threshold=1.0,
    )
    metric_names = [_get_metric_class_name(metric) for metric in metrics]
    initialized_exporter = exporter(
        metrics=metric_names,
        labelnames=config.default_labels,
        port=config.prometheus_port,
    )
    initialized_metrics = [metric(initialized_exporter) for metric in metrics]
    return RegisteredScenario[R](main_scenario, initialized_metrics, logger)


def ab_test(
    metrics: Iterable[type[Metric] | MetricEnum],
    exporter: type[Exporter] = PrometheusExporter,
    logger: Logger = getLogger(__name__),
) -> Callable[[ScenarioHandler[R]], ABTestFunction[R]]:
    """Decorator for implementing A/B testing of methods.
    Enables easy creation and management of multiple functions variants (A/B/C...)
    with automatic traffic distribution between them.

    Args:
        metrics: Collection of metrics to track (Metric.LATENCY, Metric.CALLS_TOTAL etc.)
        exporter: A class that implements the Exporter interface for uploading metrics
        (PrometheusExporter, ConsoleExporter, or custom exporter)
        logger: Custom Logger instance
    Returns:
        A decorator that converts the original function into an A/B-testable class version.
        The class supports following methods:
        def register_variant(
            self: Self,
            traffic_percent: int,  # The percentage of traffic redirected to the variant. 1 <= tp <= 99
            disable_threshold: float = 1.0,  # Error rate threshold leading to termination of redirection
        ) -> Callable[[ScenarioHandler[R]], ScenarioHandler[R]]:

        def enable_variant(
            self: Self,
            variant_name: str  # Name of the disabled variant
        ) -> None:

    Examples:
        Basic A/B test:
        ```
        @ab_test(metrics=[Metric.LATENCY, Metric.ERROR_RATE])
        def get_recommendations(user_id: int) -> list[Recommendation]:
            # Main variant (A) - receives remaining traffic percentage
            return generate_recommendations_v1(user_id)

        @get_recommendations.register_variant(traffic_percent=30)
        def get_recommendations_b(user_id: int) -> list[Recommendation]:
            # Alternative variant (B) - receives 30% of traffic
            return generate_recommendations_v2(user_id)
        ```

        FastAPI endpoint with A/B testing (correct order):
        ```
        from fastapi import FastAPI, Depends

        app = FastAPI()

        # Correct: @app.get must come BEFORE @ab_test
        @app.get("/recommendations")
        @ab_test(metrics=[Metric.LATENCY])
        async def get_recommendations(user_id: int):
            return generate_recommendations_v1(user_id)

        @get_recommendations.register_variant(traffic_percent=30)
        async def get_recommendations_b(user_id: int):
            return generate_recommendations_v2(user_id)
        ```

        With dependencies:
        ```python
        @app.post("/items")
        @ab_test(metrics=[Metric.ERROR_RATE])
        def create_item(
            item: Item,
            user: User = Depends(get_current_user)
        ):
            return create_item_v1(item, user)

        @create_item.register_variant(traffic_percent=50)
        def create_item_b(item: Item, user: User = Depends(get_current_user)):
            return create_item_v2(item, user)
        ```

    Important:
        - For FastAPI compatibility, @ab_test MUST be placed between
          the function definition and route decorator (@app.get, @app.post etc.)
        - Wrong order will disable A/B testing functionality:
          ```python
          @ab_test(metrics=[])  # This won't work as expected
          @app.get("/wrong")  # Incorrect: route decorator should be the first one
          def bad_order_example(): ...
          ```

    Features:
        - Supports unlimited variants (A/B/C/D...)
        - Automatic traffic distribution
        - Protection against exceeding 100% traffic allocation
        - Preserves original function signature
        - Fully compatible with FastAPI route decorators and dependencies
        - Works with both sync and async endpoints
    """

    def _wrapper(func: ScenarioHandler[R]) -> ABTestFunction[R]:
        ab_func = _create_registered_scenario(func, metrics, exporter, logger)
        if iscoroutinefunction(func):
            markcoroutinefunction(ab_func)
        return wraps(func)(ab_func)

    return _wrapper
