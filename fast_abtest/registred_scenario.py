from dataclasses import dataclass
from random import randint
from typing import Callable, TypeVar, Generic, Protocol

from typing_extensions import Self

R = TypeVar("R")
R_co = TypeVar("R_co", covariant=True)


class ScenarioHandler(Protocol[R_co]):
    def __call__(self, *args, **kwargs) -> R_co: ...


@dataclass
class _ScenarioVariant(Generic[R]):
    handler: ScenarioHandler[R]
    traffic_percent: int


class ABTestFunction(Protocol[R]):
    def __call__(self, *args, **kwargs) -> R: ...

    def register_variant(self, traffic_percent: int) -> Callable[[ScenarioHandler[R]], ScenarioHandler[R]]: ...


class RegisteredScenario(Generic[R]):
    def __init__(self: Self, main_scenario: _ScenarioVariant[R]) -> None:
        self._variants: dict[str, _ScenarioVariant[R]] = {}
        self._main_scenario = main_scenario

    def register_variant(self: Self, traffic_percent: int) -> Callable[[ScenarioHandler[R]], ScenarioHandler[R]]:
        def add_to_variants(variant_func: ScenarioHandler[R]) -> ScenarioHandler[R]:
            variant_name = f"V{len(self._variants)}"
            self._variants[variant_name] = _ScenarioVariant(handler=variant_func, traffic_percent=tp)
            self._main_scenario.traffic_percent -= tp
            if self._main_scenario.traffic_percent < 0:
                raise ValueError("Total traffic percentage exceeds 100")
            return variant_func

        tp = traffic_percent
        if not 1 <= tp <= 99:
            raise ValueError("traffic_percent must be between 1 and 99")

        return add_to_variants

    def __call__(
        self: Self,
        *args,
        **kwargs,
    ) -> R:
        rand = randint(1, 100)
        current = 0
        for variant in self._variants.values():
            current += variant.traffic_percent
            if rand <= current:
                return variant.handler(*args, **kwargs)

        return self._main_scenario.handler(*args, **kwargs)
