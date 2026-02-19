from random import randint
from typing import Self, Iterable

from fast_abtest.consistently_distribution import Distributor
from fast_abtest.interface import _ScenarioVariant


class VariantSelector[R]:
    def __init__(
        self: Self,
        main_scenario: _ScenarioVariant[R],
        variants: Iterable[_ScenarioVariant[R]],
        distributor: Distributor | None = None,
    ) -> None:
        self._variants = variants
        self._default_variant = main_scenario
        self._distributor = distributor

    def select(self: Self, *args, **kwargs) -> _ScenarioVariant[R]:
        if self._distributor:
            target = self._distributor.choose_target(*args, **kwargs)
        else:
            target = randint(0, 100)
        return self._random_select(target)

    def _random_select(self: Self, target: int) -> _ScenarioVariant[R]:
        if target < 0 or target > 100:
            raise ValueError("Target must me between 0 and 100")
        current = 0
        for variant in self._variants:
            if not variant.is_active:
                continue

            current += variant.traffic_percent
            if target <= current:
                variant.increment_call()
                return variant

        return self._default_variant
