from typing import Protocol, Callable, Self

from fast_abtest.registred_scenario import R, ScenarioHandler


class ABTestFunction(Protocol[R]):
    def __call__(self: Self, *args, **kwargs) -> R: ...

    def register_variant(
        self: Self,
        traffic_percent: int,
        disable_threshold: float = 1.0,
    ) -> Callable[[ScenarioHandler[R]], ScenarioHandler[R]]: ...

    def enable_variant(self: Self, variant_name: str) -> None: ...
