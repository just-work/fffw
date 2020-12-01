from dataclasses import dataclass
from typing import Optional, List, Tuple, cast, Iterable, Union, Any

from fffw.encoding import filters, outputs
from fffw.graph import base
from fffw.graph.meta import *
from fffw.wrapper import BaseWrapper, param

__all__ = [
    'Input',
    'InputList',
    'Stream',
    'input_file',
]


class Stream(base.Source):
    """ Video or audio stream in input file."""
    source = cast("Input", base.Once('source'))
    """ Source file that contains current stream."""
    index = cast(int, base.Once('index'))
    """ Index of current stream in source file."""

    def __init__(self, kind: StreamType, meta: Optional[Meta] = None):
        """
        :param kind: stream kind, video or audio
        :param meta: stream metadata
        """
        super().__init__(kind=kind, meta=meta)

    @property
    def name(self) -> str:
        if self.index == 0:
            return f'{self.source.index}:{self._kind.value}'
        return f'{self.source.index}:{self._kind.value}:{self.index}'

    def split(self, count: int = 1) -> List[filters.Filter]:
        """
        Splits input stream to reuse it as input node for multiple output nodes.

        >>> from fffw.graph import meta
        >>> stream = Stream(meta.VIDEO)
        >>> s1, s2 = stream.split(2)
        >>> s1 | filters.Scale(1280, 720)
        >>> s2 | filters.Scale(640, 360)
        """
        split = filters.Split(self.kind, output_count=count)
        self.connect_dest(split)
        return [split] * count

    def connect_input(self, source: str) -> None:
        """
        Marks current stream metadata that it belongs to some input file.

        :param source: source filename
        """
        if self.meta is None:
            return
        if self.meta.streams:
            return
        self.meta.streams = [source]
        for scene in self.meta.scenes:
            scene.stream = source


def default_streams() -> Tuple[Stream, ...]:
    """
    Generates default streams definition for input file

    :returns: a tuple with one video and one audio stream.
    """
    return Stream(VIDEO), Stream(AUDIO)


class FFMPEGIndexDescriptor(base.Once):
    """
    Input index descriptor.

    When an input is added to a FFMPEG instance, it receives an index.
    This index is used to identify streams in filter graph and in metadata.
    """

    def __set__(self, instance: base.Obj, value: Any) -> None:
        super().__set__(instance, value)
        if not isinstance(instance, Input):  # pragma: no cover
            # We can't seal instance type, but restrict using descriptor only
            # with Input subclasses.
            raise TypeError(instance)
        instance.connect_streams()


@dataclass
class Input(BaseWrapper):
    # noinspection PyUnresolvedReferences
    """
    Input command line params generator for FFMPEG.

    :arg fast_seek: seek input file over key frames
    :arg input_file: input file name
    :arg slow_seek: perform whole file decoding and output frames only
        from offset to end of file.
    :arg duration: stop decoding frames after an interval
    """
    index = FFMPEGIndexDescriptor("index")
    """ Internal ffmpeg source file index."""
    streams: Tuple[Stream, ...] = param(default=default_streams, skip=True)
    """ List of audio and video streams for input file."""

    hardware: str = param(name='hwaccel')
    device: str = param(name='hwaccel_device')
    output_format: str = param(name='hwaccel_output_format')
    fast_seek: Union[TS, float, int] = param(name='ss')
    duration: Union[TS, float, int] = param(name='t')
    input_file: str = param(name='i')
    slow_seek: Union[TS, float, int] = param(name='ss')

    def __post_init__(self) -> None:
        """
        Enumerate streams in input file and freeze instance.
        """
        self.__link_streams_to_input()
        super().__post_init__()

    def __or__(self, other: filters.Filter) -> filters.Filter:
        """
        Connect first available stream to a filter.
        """
        if not isinstance(other, filters.Filter):
            return NotImplemented
        return self.get_stream(other.kind) | other

    def __gt__(self, other: outputs.Codec) -> outputs.Codec:
        """
        Connect first available stream to a codec.
        """
        if not isinstance(other, outputs.Codec):
            return NotImplemented
        return self.get_stream(other.kind) > other

    def __link_streams_to_input(self) -> None:
        """
        Add a link to self to input streams and enumerate streams to get
        proper stream index for input.
        """
        video_streams = 0
        audio_streams = 0
        if self.streams is None:
            raise RuntimeError("Streams not initialized")

        for stream in self.streams:
            if stream.kind == VIDEO:
                meta: Optional[VideoMeta] = getattr(stream, 'meta', None)
                if self.hardware and self.device and meta:
                    meta.device = Device(hardware=self.hardware,
                                         name=self.device)
                stream.index = video_streams
                video_streams += 1
            elif stream.kind == AUDIO:
                stream.index = audio_streams
                audio_streams += 1
            else:
                raise ValueError(stream.kind)
            stream.source = self

    @property
    def audio(self) -> Stream:
        return self.get_stream(AUDIO)

    @property
    def video(self) -> Stream:
        return self.get_stream(VIDEO)

    def get_stream(self, kind: StreamType) -> Stream:
        """
        :param kind: desired stream kind
        :return: first available stream of desired kind
        :raises KeyError: if no streams of this kind found.
        """
        for stream in self.streams:
            if stream.kind == kind:
                return stream
        raise KeyError(kind)

    def connect_streams(self) -> None:
        """
        Sets a unique source identifier for each stream metadata in input.
        """
        identity = f'{self.input_file}#{self.index}'
        for stream in self.streams:
            stream.connect_input(identity)


def input_file(filename: str, *streams: Stream, **kwargs: Any) -> Input:
    kwargs['input_file'] = filename
    if streams:
        # skip empty streams list to force Input.streams default_factory
        kwargs['streams'] = streams
    return Input(**kwargs)


class InputList(list):
    """ List of inputs in FFMPEG."""

    def __init__(self, sources: Iterable[Input] = ()) -> None:
        """
        :param sources: list of input files
        """
        super().__init__()
        self.extend(sources)

    @property
    def streams(self) -> List[Stream]:
        result: List[Stream] = []
        for source in self:
            if source.streams is None:
                raise RuntimeError("Source streams not initialized")
            result.extend(source.streams)
        return result

    def append(self, source: Input) -> None:
        """
        Adds new source file to input list.

        :param source: input file
        """
        source.index = len(self)
        super().append(source)

    def extend(self, sources: Iterable[Input]) -> None:
        """
        Adds multiple source files to input list.

        :param sources: list of input files
        """
        for i, source in enumerate(sources, start=len(self)):
            source.index = i
        super().extend(sources)

    def get_args(self) -> List[bytes]:
        result: List[bytes] = []
        for source in self:
            result.extend(source.get_args())
        return result
