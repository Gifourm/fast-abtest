from typing import Protocol, Callable

from fast_abtest.registred_scenario import R, ScenarioHandler


class ABTestFunction(Protocol[R]):
    def __call__(self, *args, **kwargs) -> R: ...

    def register_variant(self, traffic_percent: int) -> Callable[[ScenarioHandler[R]], ScenarioHandler[R]]: ...
