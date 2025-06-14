from collections.abc import Iterable, Callable
from dataclasses import dataclass
from typing import Self, TypeVar, ParamSpec
from .metrics import Metric


R = TypeVar("R")
P = ParamSpec("P")
Scenario = TypeVar("Scenario", bound=Callable)


@dataclass
class _ScenarioVariant:
    handler: Callable
    traffic_percent: int


class ab_test:
    def __init__(
        self: Self,
        metrics: Iterable[Metric],
    ) -> None:
        self._metrics = metrics
        self._variants: dict[str, _ScenarioVariant] = {}

    def __call__(self, func: Callable) -> Self:
        self._variants["V0"] = _ScenarioVariant(
            handler=func,
            traffic_percent=100,
        )
        return self

    def register_variant(self: Self, traffic_percent: int) -> Callable[Callable[[Scenario], Scenario]]:
        def __wrapper(func: Scenario) -> Scenario:
            variant_name = f"V{len(self._variants)}"
            self._variants[variant_name] = _ScenarioVariant(
                handler=func,
                traffic_percent=traffic_percent,
            )
            print(f"Func registered: {self._variants}")
            return func

        return __wrapper
