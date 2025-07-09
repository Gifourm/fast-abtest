from random import randint
from typing import Self, Iterable

from fast_abtest.interface import _ScenarioVariant


class VariantSelector[R]:
    def __init__(
        self: Self,
        main_scenario: _ScenarioVariant[R],
        variants: Iterable[_ScenarioVariant[R]],
        idempotent: bool = False,
    ) -> None:
        self._variants = variants
        self._default_variant = main_scenario
        self._idempotent = idempotent

    def select(self: Self) -> _ScenarioVariant[R]:
        if self._idempotent:
            return self._idempotent_select()
        return self._random_select()

    def _random_select(self: Self) -> _ScenarioVariant[R]:
        rand = randint(1, 100)
        current = 0
        for variant in self._variants:
            if not variant.is_active:
                continue

            current += variant.traffic_percent
            if rand <= current:
                variant.increment_call()
                return variant

        return self._default_variant

    def _idempotent_select(self: Self) -> _ScenarioVariant[R]:
        return self._default_variant
