from dataclasses import dataclass, asdict
from typing import Any, Tuple

from fffw.graph import base

from fffw.graph.base import VIDEO
from fffw.wrapper.params import Params

__all__ = [
    'Filter',
    'Scale',
    'Split',
    'Concat',
    'Overlay',
]


def as_param(item: Tuple[str, Any]) -> str:
    k, v = item
    return f'{k}={v}'


@dataclass
class Filter(Params, base.Node):
    ALLOWED = ('enabled',)

    def __post_init__(self):
        # Dataclass replaces `__init__` method completely so we need to call it
        # manually.
        super().__init__()
        # Freeze filter params only after `__init__`
        super().__post_init__()

    @property
    def args(self) -> str:
        args = asdict(self)
        return ':'.join(map(as_param, args.items()))


@dataclass
class Scale(Filter):
    kind = VIDEO
    filter = "scale"

    width: int
    height: int


@dataclass
class Split(Filter):
    kind: base.StreamType = VIDEO
    output_count: int = 2

    def __post_init__(self) -> None:
        self.enabled = self.output_count > 1
        self.filter = 'split' if self.kind == VIDEO else 'asplit'
        super().__post_init__()

    @property
    def args(self) -> str:
        if self.output_count == 2:
            return ''
        return '%s' % self.output_count


@dataclass
class Concat(Filter):
    filter = 'concat'
    kind: base.StreamType = VIDEO
    input_count: int = 2

    def __post_init__(self) -> None:
        self.enabled = self.input_count > 1
        super().__post_init__()

    @property
    def args(self) -> str:
        if self.kind == VIDEO:
            if self.input_count == 2:
                return ''
            return 'n=%s' % self.input_count
        return 'v=0:a=1:n=%s' % self.input_count


@dataclass
class Overlay(Filter):
    kind = VIDEO
    input_count = 2
    filter = "overlay"
    x: int
    y: int
