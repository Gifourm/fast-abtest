import inspect
from dataclasses import dataclass, field
from logging import Logger
from random import randint
from threading import Lock
from typing import Callable, TypeVar, Generic, Protocol, Iterable

from typing_extensions import Self

from .metrics import Metric

R = TypeVar("R")
R_co = TypeVar("R_co", covariant=True)


class ScenarioHandler(Protocol[R_co]):
    __name__: str

    def __call__(self, *args, **kwargs) -> R_co: ...


@dataclass
class _ScenarioVariant(Generic[R]):
    handler: ScenarioHandler[R]
    traffic_percent: int
    threshold: float
    call_count: int = 0
    error_count: int = 0
    is_active: bool = True
    _lock: Lock = field(default_factory=Lock, init=False)

    def increment_call(self: Self) -> None:
        with self._lock:
            self.call_count += 1

    def threshold_exceeded(self: Self) -> bool:
        with self._lock:
            self.error_count += 1
            if self.call_count > 10 and self.error_count / max(self.call_count, 1) > self.threshold:
                self.is_active = False
                return True
        return False


class RegisteredScenario(Generic[R]):
    EXCEEDING_THRESHOLD_WARNING = "Variant {} disabled by error rate (error rate: {:.2}"

    def __init__(
        self: Self,
        main_scenario: _ScenarioVariant[R],
        metrics: Iterable[Metric | Callable],
        logger: Logger,
    ) -> None:
        self._variants: list[_ScenarioVariant[R]] = []
        self._metrics = metrics
        self._main_scenario = main_scenario
        self._main_scenario_signature = self._normalize_signature(inspect.signature(self._main_scenario.handler))
        self._is_async = inspect.iscoroutinefunction(self._main_scenario.handler)
        self._logger = logger

    def register_variant(
        self: Self,
        traffic_percent: int,
        disable_threshold: float = 1.0,
    ) -> Callable[[ScenarioHandler[R]], ScenarioHandler[R]]:
        def add_to_variants(variant_func: ScenarioHandler[R]) -> ScenarioHandler[R]:
            variant_func = self._validate_variant_signature(variant_func)
            variant_func = self._validate_sync_type(variant_func)
            scenario_variant = _ScenarioVariant(
                handler=variant_func,
                traffic_percent=tp,
                threshold=threshold,
            )
            self._variants.append(scenario_variant)
            self._main_scenario.traffic_percent -= tp
            self._validate_total_traffic()
            return variant_func

        tp = self._validate_traffic_value(traffic_percent)
        threshold = self._validate_disable_threshold(disable_threshold)
        return add_to_variants

    def enable_variant(self: Self, variant_name: str) -> None:
        for variant in self._variants:
            if variant.handler.__name__ == variant_name:
                variant.is_active = True
                variant.error_count = 0

    def _validate_sync_type(self: Self, func: ScenarioHandler[R]) -> ScenarioHandler[R]:
        if inspect.iscoroutinefunction(func) != self._is_async:
            raise TypeError("All variants must be either async or sync, cannot mix them")
        return func

    def _validate_variant_signature(self: Self, func: ScenarioHandler[R]) -> ScenarioHandler[R]:
        variant_signature = self._normalize_signature(inspect.signature(func))
        if variant_signature != self._main_scenario_signature:
            raise TypeError(
                f"Variant signature must match main scenario. "
                f"Expected: {self._main_scenario_signature}, "
                f"got: {variant_signature}"
            )
        return func

    def _validate_total_traffic(self: Self) -> None:
        if self._main_scenario.traffic_percent < 0:
            raise ValueError("Total traffic percentage exceeds 100")

    @staticmethod
    def _validate_traffic_value(traffic: int) -> int:
        if not 1 <= traffic <= 99:
            raise ValueError("traffic_percent must be between 1 and 99")
        return int(traffic)

    @staticmethod
    def _validate_disable_threshold(threshold: float) -> float:
        if not 0.01 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0.01 and 1.0")
        return float(threshold)

    @staticmethod
    def _normalize_signature(sig: inspect.Signature) -> str:
        params = []
        for name, param in sig.parameters.items():
            if hasattr(param.default, "dependency"):
                dep_repr = f"Depends({param.default.dependency.__name__})"
            else:
                dep_repr = str(param.default)

            params.append(
                f"{name}: {param.annotation}" + (f" = {dep_repr}" if param.default != inspect.Parameter.empty else "")
            )
        return f"({', '.join(params)}) -> {sig.return_annotation}"

    def __call__(
        self: Self,
        *args,
        **kwargs,
    ) -> R:
        rand = randint(1, 100)
        current = 0
        for variant in self._variants:
            if not variant.is_active:
                continue

            current += variant.traffic_percent
            if rand <= current:
                variant.increment_call()
                try:
                    return variant.handler(*args, **kwargs)
                except:
                    if variant.threshold_exceeded():
                        msg = self.EXCEEDING_THRESHOLD_WARNING.format(
                            variant.handler.__name__,
                            variant.error_count / variant.call_count,
                        )
                        self._logger.warning(msg)
                    raise

        return self._main_scenario.handler(*args, **kwargs)
