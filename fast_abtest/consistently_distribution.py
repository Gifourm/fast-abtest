import asyncio
import inspect
import pickle
from contextlib import AsyncExitStack
from dataclasses import is_dataclass
from inspect import get_annotations
from typing import Self, get_args, get_origin, ForwardRef, Annotated, Any, TYPE_CHECKING, Sequence
import hashlib

if TYPE_CHECKING:
    from fastapi import Request
    from fastapi.dependencies.models import Dependant
if not TYPE_CHECKING:
    Request = Any
    Dependant = Any

from pydantic import BaseModel

from fast_abtest.depends_compatibility import request_ctx
from fast_abtest.interface import ScenarioHandler


class Distributor[R]:
    def __init__(
        self: Self,
        func: ScenarioHandler[R],
        consistency_key: str,
    ) -> None:
        self._main_scenario = func
        self._requires_depends = False
        self._consistency_key = self._find_argument(func, consistency_key, [])

        if self._requires_depends:
            from fastapi.dependencies.utils import get_dependant, solve_dependencies

            self._get_dependant = get_dependant
            self._solve_dependencies = solve_dependencies

        self._has_dependencies = False

    @property
    def has_dependencies(self: Self) -> bool:
        return self._has_dependencies

    @has_dependencies.setter
    def has_dependencies(self: Self, value: bool) -> None:
        self._has_dependencies = value

    def choose_target(self: Self, *args, **kwargs) -> int:
        if self._has_dependencies:
            request = request_ctx.get()
            deps = self._sync_to_async_intercept_dependencies(self._main_scenario, request)
            if self._consistency_key[-1] in deps:
                return self._choose_target_by_key(deps[self._consistency_key[-1]])

        bounded_args = inspect.signature(self._main_scenario).bind(*args, **kwargs)
        bounded_args.apply_defaults()
        key = self._get_nested_value(bounded_args.arguments, self._consistency_key)
        return self._choose_target_by_key(key)

    def _choose_target_by_key(self: Self, key: Any) -> int:
        return self._hash_object_consistent(key, 0, 100)

    @staticmethod
    def _hash_object_consistent(
        obj: Any,
        min_val: int = 0,
        max_val: int = 100,
    ) -> int:
        try:
            obj_bytes = pickle.dumps(obj)
            hash_obj = hashlib.sha256(obj_bytes)
            hash_int = int(hash_obj.hexdigest(), 16)
            normalized = hash_int % (max_val - min_val + 1) + min_val
            return normalized
        except:
            obj_hash = hash(obj)
            normalized = abs(obj_hash) % (max_val - min_val + 1) + min_val
            return normalized

    @staticmethod
    def _get_nested_value(obj: Any, path: list[str]) -> Any:
        current = obj
        for key in path:
            if isinstance(current, Sequence) and current:
                current = current[0]
            if hasattr(current, "__dict__"):
                current = getattr(current, key, None)
            elif isinstance(current, dict):
                current = current.get(key)
            else:
                return None
            if current is None:
                return None
        return current

    def _sync_to_async_intercept_dependencies(
        self: Self,
        func: ScenarioHandler[R],
        request: "Request",
    ) -> dict[str, Any]:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        dependant = self._get_dependant(path=request.scope["path"], call=func)

        async def capture_dependency_values() -> dict[str, Any]:
            captured_values: dict[str, Any] = {}

            async def intercept_dependency(
                sub_dependant: "Dependant",
                values: dict,
            ) -> dict[str, Any]:
                async with AsyncExitStack() as sub_stack:
                    solved = await self._solve_dependencies(
                        request=request,
                        dependant=sub_dependant,
                        async_exit_stack=sub_stack,
                        embed_body_fields=False,
                    )
                    values.update(solved.values)

                    for dep in sub_dependant.dependencies:
                        await intercept_dependency(dep, values)

                return values

            return await intercept_dependency(dependant, captured_values)

        if loop.is_running():
            task = asyncio.create_task(capture_dependency_values())
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, capture_dependency_values())
                return future.result()
        else:
            return loop.run_until_complete(capture_dependency_values())

    def _find_argument(
        self,
        func: ScenarioHandler[R],
        consistency_key: str,
        path_to_param: list[str],
        in_depends_arg: bool = False,
    ) -> list[str]:
        _checked_types = set()

        def find_field_in_type(
            annotation: type,
            target_field: str,
            _path_to_param: list[str],
        ) -> list[str] | None:
            nonlocal _checked_types

            if isinstance(annotation, (str, ForwardRef)):
                return None

            if annotation in _checked_types:
                return None
            _checked_types.add(annotation)

            origin = get_origin(annotation)
            if origin is Annotated:
                annotation = get_args(annotation)[0]

            if self._is_dataclass_or_pydantic(annotation):
                annotations = get_annotations(annotation)
                for field_name, field_type in annotations.items():
                    path = _path_to_param + [field_name]
                    if field_name == target_field:
                        if in_depends_arg:
                            self._requires_depends = True
                        return path
                    if _new_path := find_field_in_type(field_type, target_field, path):
                        return _new_path

            elif origin is not None:
                for arg in get_args(annotation):
                    if _new_path := find_field_in_type(arg, target_field, _path_to_param):
                        return _new_path

            return None

        sig = inspect.signature(func)
        for param in sig.parameters.values():
            if param.name == consistency_key:
                if in_depends_arg or hasattr(param.default, "dependency"):
                    self._requires_depends = True
                return path_to_param + [param.name]

            if param.annotation is not inspect.Parameter.empty:
                if _path := find_field_in_type(
                    param.annotation,
                    consistency_key,
                    [param.name],
                ):
                    if _path[-1] == consistency_key:
                        return path_to_param + _path

            if hasattr(param.default, "dependency"):
                dependency = param.default.dependency
                if isinstance(dependency, type):
                    dependency = dependency.__init__  # type: ignore
                if new_path := self._find_argument(
                    dependency,
                    consistency_key,
                    path_to_param + [param.name],
                    True,
                ):
                    if new_path[-1] == consistency_key:
                        return new_path

        if path_to_param:
            return path_to_param

        raise ValueError(f"The argument {consistency_key} is unreachable from the arguments of the method")

    @staticmethod
    def _is_dataclass_or_pydantic(annotation: type) -> bool:
        try:
            return is_dataclass(annotation) or (isinstance(annotation, type) and issubclass(annotation, BaseModel))
        except TypeError:
            return False
