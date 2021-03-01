from dataclasses import dataclass, replace, asdict, field, fields
from typing import Union, List, cast

from fffw.graph import base
from fffw.encoding import mixins
from fffw.graph.meta import Meta, VideoMeta, TS, Scene, VIDEO, AUDIO, AudioMeta
from fffw.graph.meta import StreamType, Device
from fffw.wrapper.params import Params, param

__all__ = [
    'AutoFilter',
    'AudioFilter',
    'VideoFilter',
    'Concat',
    'Format',
    'Overlay',
    'Scale',
    'SetPTS',
    'Split',
    'Trim',
    'Upload',
    'ensure_video',
    'ensure_audio',
]


def ensure_video(meta: Meta, *_: Meta) -> VideoMeta:
    """
    Checks that first passed stream is a video stream

    :returns: first passed stream
    """
    if not isinstance(meta, VideoMeta):
        raise TypeError(meta)
    return meta


def ensure_audio(meta: Meta, *_: Meta) -> AudioMeta:
    """
    Checks that first passed stream is a audio stream

    :returns: first passed stream
    """
    if not isinstance(meta, AudioMeta):
        raise TypeError(meta)
    return meta


@dataclass
class Filter(mixins.StreamValidationMixin, base.Node, Params):
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
        skip = [f.name for f in fields(self) if not f.init]
        kwargs = {k: v for k, v in asdict(self).items() if k not in skip}
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
    kind = VIDEO


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
    kind = AUDIO


@dataclass
class AutoFilter(Filter):
    """
    Base class for stream kind autodetect.
    """

    kind: StreamType = field(metadata={'skip': True})
    """ 
    Stream kind used to generate filter name. Required. Not used as filter 
    parameter.
    """

    # `field` is used here to tell MyPy that there is no default for `kind`
    # because `default=MISSING` is valuable for MyPY.

    def __post_init__(self) -> None:
        """ Adds audio prefix to filter name for audio filters."""
        if self.kind == AUDIO:
            self.filter = f'a{self.filter}'
        super().__post_init__()


@dataclass
class Scale(VideoFilter):
    # noinspection PyUnresolvedReferences
    """
    Video scaling filter.

    :arg width: resulting video width
    :arg height: resulting video height
    """
    filter = "scale"
    hardware = None  # cpu only

    width: int = param(name='w')
    height: int = param(name='h')

    def transform(self, *metadata: Meta) -> Meta:
        meta = ensure_video(*metadata)
        par = meta.dar / (self.width / self.height)
        return replace(meta, width=self.width, height=self.height, par=par)


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
    Cuts the input so that the output contains one continuous subpart
    of the input.

    :arg kind: stream kind (for proper concatenated streams definitions).
    :arg start: start time of trimmed output
    :arg end: end time of trimmed output
    """
    filter = 'trim'

    start: Union[int, float, str, TS]
    end: Union[int, float, str, TS]

    def __post_init__(self) -> None:
        if not isinstance(self.start, (TS, type(None))):
            self.start = TS(self.start)
        if not isinstance(self.end, (TS, type(None))):
            self.end = TS(self.end)
        super().__post_init__()

    def transform(self, *metadata: Meta) -> Meta:
        """
        Computes metadata for trimmed stream.

        :param metadata: single incoming stream metadata.
        :returns: metadata with initial start (this is fixed with SetPTS) and
            duration set to trim end. Scenes list is intersected with trim
            interval, scene borders are aligned to trim borders.
        """
        meta = metadata[0]
        scenes = []
        streams: List[str] = []
        start = self.start or TS(0)
        end = min(meta.duration, self.end or TS(0))
        for scene in meta.scenes:
            if scene.stream and (not streams or streams[0] != scene.stream):
                # Adding an input stream without contiguous duplicates.
                streams.append(scene.stream)

            # intersect scene with trim interval
            start = cast(TS, max(self.start, scene.position))
            end = cast(TS, min(self.end, scene.position + scene.duration))

            if start < end:
                # If intersection is not empty, add intersection to resulting
                # scenes list.
                # This will allow to detect buffering when multiple scenes are
                # reordered in same file: input[3:4] + input[1:2]
                offset = start - scene.position
                scenes.append(Scene(
                    stream=scene.stream,
                    start=scene.start + offset,
                    position=scene.position + offset,
                    duration=end - start))

        kwargs = {
            'start': start,
            'duration': end,
            'scenes': scenes,
            'streams': streams
        }
        interval = cast(TS, end) - cast(TS, start)
        if isinstance(meta, AudioMeta):
            kwargs['samples'] = round(meta.sampling_rate * interval)
        if isinstance(meta, VideoMeta):
            kwargs['frames'] = round(meta.frame_rate * interval)
        return replace(meta, **kwargs)


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

    kind: StreamType
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
        if self.kind == VIDEO:
            if self.input_count == 2:
                return ''
            return 'n=%s' % self.input_count
        return 'v=0:a=1:n=%s' % self.input_count

    def transform(self, *metadata: Meta) -> Meta:
        """
        Compute metadata for concatenated streams.

        :param metadata: concatenated streams metadata
        :returns: Metadata for resulting stream with duration set to a sum of
            stream durations. Scenes and streams are also concatenated.
        """
        duration = TS(0)
        scenes = []
        streams: List[str] = []
        frames: int = 0
        for meta in metadata:
            for scene in meta.scenes:
                scenes.append(Scene(
                    stream=scene.stream,
                    duration=scene.duration,
                    start=scene.start,
                    position=scene.position + duration,
                ))
            duration += meta.duration
            for stream in meta.streams:
                if not streams or streams[-1] != stream:
                    # Add all streams for each concatenated metadata and remove
                    # contiguous duplicates.
                    streams.append(stream)
            if isinstance(meta, VideoMeta):
                frames += meta.frames
        kwargs = dict(duration=duration, scenes=scenes, streams=streams)
        meta = metadata[0]
        if isinstance(meta, AudioMeta):
            # Recompute samples and sampling rate: sampling rate from first
            # input, samples count corresponds duration.
            kwargs['samples'] = round(meta.sampling_rate * duration)
        if isinstance(meta, VideoMeta):
            # Sum frames count from all input streams
            kwargs['frames'] = frames
        return replace(metadata[0], **kwargs)


@dataclass
class Overlay(VideoFilter):
    # noinspection PyUnresolvedReferences
    """
    Combines two video streams one on top of another.

    :arg x: horizontal position of top image in bottom one.
    :arg y: vertical position of top image in bottom one.
    """
    input_count = 2
    filter = "overlay"

    x: int
    y: int


@dataclass
class Format(VideoFilter):
    """
    Converts pixel format of video stream
    """
    filter = 'format'
    format: str = param(name='pix_fmts')


@dataclass
class Upload(VideoFilter):
    """
    Uploads a stream to a hardware device
    """
    filter = 'hwupload'
    extra_hw_frames: int = param(default=64, init=False)
    device: Device = param(skip=True)

    def __post_init__(self) -> None:
        if isinstance(self.device, dict):
            # deserialize back after filter cloning
            self.device = Device(**self.device)
        super().__post_init__()

    def transform(self, *metadata: Meta) -> VideoMeta:
        """ Marks a stream as uploaded to a device."""
        meta = ensure_video(*metadata)
        return replace(meta, device=self.device)
