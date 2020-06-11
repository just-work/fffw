from dataclasses import dataclass, replace, asdict
from typing import Union, List

from fffw.graph import base
from fffw.graph.meta import Meta, VideoMeta, TS
from fffw.wrapper.params import Params, param

__all__ = [
    'AutoFilter',

    'AudioFilter',
    'VideoFilter',
    'Concat',
    'Overlay',
    'Scale',
    'SetPTS',
    'Split',
    'Trim',
]


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
        """ Formats filter args as k=v pairs separated by colon."""
        args = self.as_pairs()
        result = []
        for key, value in args:
            if key and value:
                result.append(f'{key}={value}')
        return ':'.join(result)

    def split(self, count: int = 1) -> List["Filter"]:
        """
        Adds a split filter to "fork" current node and reuse it as input node
        for multiple destinations.

        >>> d = VideoFilter("deint")
        >>> d1, d2 = d.split(count=2)
        >>> d1 | Scale(1280, 720)
        >>> d2 | Scale(480, 360)

        :returns: a list with `count` copies of Split() filter. These are
        multiple references for the same object, so each element is intended
        to be reused only once.
        """
        split = Split(self.kind, output_count=count)
        self.connect_dest(split)
        return [split] * count

    def clone(self, count: int = 1) -> List["Filter"]:
        """
        Creates multiple copies of self to reuse it as output node for multiple
        sources.

        Any connected input node is being split and connected to a corresponding
        copy of current filter.
        """
        if count == 1:
            return [self]
        result = []
        for _ in range(count):
            result.append(self._clone())

        for i, edge in enumerate(self.inputs):
            if edge is None:
                continue
            # reconnecting incoming edge to split filter
            split = Split(self.kind, output_count=count)
            edge.reconnect(split)
            for dst in result:
                split | dst

        return result

    def _clone(self) -> "Filter":
        """
        Creates a copy of current filter with same parameters.

        Inputs and outputs are not copied.
        """
        kwargs = asdict(self)
        # noinspection PyArgumentList
        return type(self)(**kwargs)  # type: ignore


class VideoFilter(Filter):
    """
    Base class for video filters.

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

    >>> @dataclass
    ... class Volume(AudioFilter):
    ...     filter = 'volume'
    ...     volume: float = param(default=1.0)
    ...
    >>>
    """
    kind = base.AUDIO


@dataclass
class AutoFilter(Filter):
    """
    Base class for stream kind autodetect.
    """

    kind: base.StreamType

    def __post_init__(self) -> None:
        """ Adds audio prefix to filter name for audio filters."""
        if self.kind == base.AUDIO:
            self.filter = f'a{self.filter}'
        super().__post_init__()


@dataclass
class Scale(VideoFilter):
    """ Video scaling filter."""
    filter = "scale"

    width: int = param(name='w')
    height: int = param(name='h')

    def transform(self, *metadata: Meta) -> Meta:
        meta = metadata[0]
        if not isinstance(meta, VideoMeta):
            raise TypeError(meta)
        par = meta.dar / (self.width / self.height)
        return replace(meta, width=self.width, height=self.height, par=par)

    def get_filter_cmd(self, partial: bool = False) -> str:
        return super().get_filter_cmd(partial)


@dataclass
class Split(AutoFilter):
    # noinspection PyUnresolvedReferences
    """
    Audio or video split filter.

    Splits audio or video stream to multiple output streams (2 by default).
    Unlike ffmpeg `split` filter this one does not allow to pass multiple
    inputs.

    :arg kind: stream type.
    :arg output_count: number of output streams.
    """
    filter = 'split'

    output_count: int = 2

    def __post_init__(self) -> None:
        """
        Disables filter if `output_count` equals 1 (no real split is preformed).
        """
        self.enabled = self.output_count > 1
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
class Trim(AutoFilter):
    # noinspection PyUnresolvedReferences
    """
    Cut the input so that the output contains one continuous subpart
    of the input.

    :arg kind: stream kind (for proper concatenated streams definitions).
    :arg start: start time of trimmed output
    :arg end: end time of trimmed output
    """
    filter = 'trim'

    start: Union[int, float, str, TS]
    end: Union[int, float, str, TS]

    def transform(self, *metadata: Meta) -> Meta:
        meta = metadata[0]
        start = self.start if isinstance(self.start, TS) else TS(self.start)
        end = self.end if isinstance(self.end, TS) else TS(self.end)
        return replace(meta, start=start, duration=end)


@dataclass
class SetPTS(AutoFilter):
    """
    Change the PTS (presentation timestamp) of the input frames.

    $  ffmpeg -y -i source.mp4 \
    -vf trim=start=3:end=4,setpts=PTS-STARTPTS -an test.mp4

    Supported cases for metadata handling:

    * "PTS-STARTPTS" - resets stream start to zero.
    """
    RESET_PTS = 'PTS-STARTPTS'
    filter = 'setpts'

    expr: str = param(default=RESET_PTS)

    def transform(self, *metadata: Meta) -> Meta:
        meta = metadata[0]
        expr = self.expr.replace(' ', '')
        if expr == self.RESET_PTS:
            duration = meta.duration - meta.start
            return replace(meta, start=TS(0), duration=duration)
        raise NotImplementedError()

    @property
    def args(self) -> str:
        return self.expr


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

    def transform(self, *metadata: Meta) -> Meta:
        duration = TS(0)
        for meta in metadata:
            duration += meta.duration
        return replace(metadata[0], duration=duration)


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
