from dataclasses import dataclass, field
from typing import Protocol, Self, Any


@dataclass
class Label:
    metric: str
    func: str
    variant: str
    is_error: bool
    tags: dict = field(default_factory=dict)


class Exporter(Protocol):
    def record(self: Self, label: Label, value: Any): ...
