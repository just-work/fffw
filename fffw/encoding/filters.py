from dataclasses import dataclass, asdict
from typing import Any, Tuple

from fffw.graph import base
from fffw.wrapper.params import Params

__all__ = [
    'AudioFilter',
    'VideoFilter',
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

    def __post_init__(self) -> None:
        # Dataclass replaces `__init__` method completely so we need to call it
        # manually.
        super().__init__()
        # Freeze filter params only after `__init__`
        super().__post_init__()

    @property
    def args(self) -> str:
        args = asdict(self)
        return ':'.join(map(as_param, args.items()))


class VideoFilter(Filter):
    kind = base.VIDEO


class AudioFilter(Filter):
    kind = base.AUDIO


@dataclass
class Scale(VideoFilter):
    filter = "scale"

    width: int
    height: int


@dataclass
class Split(Filter):
    kind: base.StreamType
    output_count: int = 2

    def __post_init__(self) -> None:
        self.enabled = self.output_count > 1
        self.filter = 'split' if self.kind == base.VIDEO else 'asplit'
        super().__post_init__()

    @property
    def args(self) -> str:
        if self.output_count == 2:
            return ''
        return '%s' % self.output_count


@dataclass
class Concat(Filter):
    filter = 'concat'
    kind: base.StreamType
    input_count: int = 2

    def __post_init__(self) -> None:
        self.enabled = self.input_count > 1
        super().__post_init__()

    @property
    def args(self) -> str:
        if self.kind == base.VIDEO:
            if self.input_count == 2:
                return ''
            return 'n=%s' % self.input_count
        return 'v=0:a=1:n=%s' % self.input_count


@dataclass
class Overlay(VideoFilter):
    input_count = 2
    filter = "overlay"
    x: int
    y: int
