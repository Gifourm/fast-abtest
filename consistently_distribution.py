import inspect
from inspect import get_annotations
from dataclasses import is_dataclass
from typing import Self, get_args, get_origin, ForwardRef, Annotated

from pydantic import BaseModel

from fast_abtest.interface import R, ScenarioHandler


class Distributor:
    def __init__(
        self: Self,
        func: ScenarioHandler[R],
        consistency_key: str,
    ) -> None:
        self._consistency_key = self._find_argument(func, consistency_key)

    @staticmethod
    def is_dataclass_or_pydantic(annotation: type) -> bool:
        try:
            return is_dataclass(annotation) or (isinstance(annotation, type) and issubclass(annotation, BaseModel))
        except TypeError:
            return False

    def _find_argument(
        self,
        func: ScenarioHandler[R],
        consistency_key: str,
    ) -> bool:
        _checked_types = set()

        def find_field_in_type(annotation: type, target_field: str) -> bool:
            nonlocal _checked_types

            if isinstance(annotation, (str, ForwardRef)):
                return False

            if annotation in _checked_types:
                return False
            _checked_types.add(annotation)

            origin = get_origin(annotation)
            if origin is Annotated:
                annotation = get_args(annotation)[0]

            if self.is_dataclass_or_pydantic(annotation):
                annotations = get_annotations(annotation)
                for field_name, field_type in annotations.items():
                    if field_name == target_field:
                        return True
                    if find_field_in_type(field_type, target_field):
                        return True

            elif origin is not None:
                for arg in get_args(annotation):
                    if find_field_in_type(arg, target_field):
                        return True

            return False

        sig = inspect.signature(func)
        for param in sig.parameters.values():
            if hasattr(param.default, "dependency"):
                dependency = param.default.dependency
                if isinstance(dependency, type):
                    dependency = dependency.__init__  # type: ignore
                if self._find_argument(dependency, consistency_key):
                    return True

            if param.name == consistency_key:
                return True

            if param.annotation is not inspect.Parameter.empty and find_field_in_type(
                param.annotation,
                consistency_key,
            ):
                return True

        return False
