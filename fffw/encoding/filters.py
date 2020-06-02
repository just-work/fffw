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
    """
    Formats a tuple as ffmpeg filter parameter.

    :param item: a tuple with filter parameter name and corresponding value
    :returns: formatted parameter value definition
    """
    k, v = item
    return f'{k}={v}'


@dataclass
class Filter(base.Node, Params):
    """
    Base class for ffmpeg filter definitions.

    `VideoFilter` and `AudioFilter` are used to define new filters.
    """
    ALLOWED = ('enabled',)
    """ fields that are allowed to be modified after filter initialization."""

    @property
    def args(self) -> str:
        args = asdict(self)
        return ':'.join(map(as_param, args.items()))


class VideoFilter(Filter):
    """
    Base class for video filters.

    >>> from fffw.wrapper.params import param
    >>> @dataclass
    ... class Deinterlace(VideoFilter):
    ...     filter = 'yadif'
    ...     mode: int = param(default=0)
    ...
    >>>
    """
    kind = base.VIDEO


class AudioFilter(Filter):
    """
    Base class for audio filters.

    >>> from fffw.wrapper.params import param
    >>> @dataclass
    ... class Volume(AudioFilter):
    ...     filter = 'volume'
    ...     volume: float = param(default=1.0)
    ...
    >>>
    """
    kind = base.AUDIO


@dataclass
class Scale(VideoFilter):
    """ Video scaling filter."""
    filter = "scale"

    width: int
    height: int


@dataclass
class Split(Filter):
    # noinspection PyUnresolvedReferences
    """
    Audio or video split filter.

    Splits audio or video stream to multiple output streams (2 by default).
    Unlike ffmpeg `split` filter this one does not allow to pass multiple
    inputs.

    :arg output_count: number of output streams.
    """
    kind: base.StreamType
    output_count: int = 2

    def __post_init__(self) -> None:
        """
        Sets filter name from stream kind and disables filter if `output_count`
        is set to 1 (no real split is preformed).
        """
        self.enabled = self.output_count > 1
        self.filter = 'split' if self.kind == base.VIDEO else 'asplit'
        super().__post_init__()

    @property
    def args(self) -> str:
        """
        :returns: split/asplit filter parameters
        """
        if self.output_count == 2:
            return ''
        return str(self.output_count)


@dataclass
class Concat(Filter):
    # noinspection PyUnresolvedReferences
    """
    Concatenates multiple input stream to a single one.

    :arg kind: stream kind (for proper concatenated streams definitions).
    :arg input_count: number of input streams.
    """
    filter = 'concat'

    kind: base.StreamType
    input_count: int = 2

    def __post_init__(self) -> None:
        """
        Disables filter if input_count is 1 (no actual concatenation is
        performed).
        """
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
    # noinspection PyUnresolvedReferences
    """
    Combines two video streams one on top of another.

    :arg x: horizontal position of top image in bottom one.
    :arg x: vertical position of top image in bottom one.
    """
    input_count = 2
    filter = "overlay"

    x: int
    y: int
