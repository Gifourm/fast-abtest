from collections.abc import Iterable
from functools import wraps
from inspect import iscoroutinefunction, markcoroutinefunction
from typing import Callable

from .metrics import Metric  # type: ignore
from .registred_scenario import (  # type: ignore
    RegisteredScenario,
    ScenarioHandler,
    R,
    _ScenarioVariant,
)
from .interface import ABTestFunction  # type: ignore


def ab_test(metrics: Iterable[Metric]) -> Callable:
    """Decorator for implementing A/B testing of methods.
    Enables easy creation and management of multiple functions variants (A/B/C...)
    with automatic traffic distribution between them.

    Args:
        metrics: Collection of metrics to track (latency, error rate etc.)
    Returns:
        A decorator that converts the original function into an A/B-testable version.
    Example:
        Basic A/B test:
        ```python
        @ab_test(metrics=[Metric.LATENCY, Metric.ERROR_RATE])
        def get_recommendations(user_id: int) -> list[Recommendation]:
            # Main variant (A) - receives remaining traffic percentage
            return generate_recommendations_v1(user_id)

        @get_recommendations.register_variant(traffic_percent=30)
        def get_recommendations_b(user_id: int) -> list[Recommendation]:
            # Alternative variant (B) - receives 30% of traffic
            return generate_recommendations_v2(user_id)
        ```

    Features:
        - Supports unlimited variants (A/B/C/D...)
        - Automatic traffic distribution
        - Protection against exceeding 100% traffic allocation
        - Preserves original function signature
    """

    def _wrapper(func: ScenarioHandler[R]) -> ABTestFunction[R]:
        main_scenario = _ScenarioVariant(handler=func, traffic_percent=100)
        ab_func = RegisteredScenario[R](main_scenario)
        if iscoroutinefunction(func):
            markcoroutinefunction(ab_func)
        return wraps(func)(ab_func)

    return _wrapper
