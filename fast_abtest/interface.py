from typing import Protocol, Callable, Self, runtime_checkable

from fast_abtest.registred_scenario import R, ScenarioHandler, Context


class ABTestFunction(Protocol[R]):
    def __call__(self: Self, *args, **kwargs) -> R: ...

    def register_variant(
        self: Self,
        traffic_percent: int,
        disable_threshold: float = 1.0,
    ) -> Callable[[ScenarioHandler[R]], ScenarioHandler[R]]: ...

    def enable_variant(self: Self, variant_name: str) -> None: ...


@runtime_checkable
class Metric(Protocol):
    def on_start(self: Self, context: Context) -> Context: ...

    def on_end(self: Self, context: Context, is_error: bool) -> None: ...
