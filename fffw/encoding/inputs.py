from dataclasses import dataclass
from typing import Optional, List, Tuple, cast, Iterable, Union, Any

from fffw.encoding import filters
from fffw.graph import base
from fffw.graph.meta import Meta, TS
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

    def __init__(self, kind: base.StreamType, meta: Optional[Meta] = None):
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

        >>> stream = Stream(base.VIDEO)
        >>> s1, s2 = stream.split(2)
        >>> s1 | filters.Scale(1280, 720)
        >>> s2 | filters.Scale(640, 360)
        """
        split = filters.Split(self.kind, output_count=count)
        self.connect_dest(split)
        return [split] * count


def default_streams() -> Tuple[Stream, ...]:
    """
    Generates default streams definition for input file

    :returns: a tuple with one video and one audio stream.
    """
    return Stream(base.VIDEO), Stream(base.AUDIO)


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
    index = cast(int, base.Once("index"))
    """ Internal ffmpeg source file index."""
    streams: Tuple[Stream, ...] = param(default=default_streams, skip=True)
    """ List of audio and video streams for input file."""

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
            if stream.kind == base.VIDEO:
                stream.index = video_streams
                video_streams += 1
            elif stream.kind == base.AUDIO:
                stream.index = audio_streams
                audio_streams += 1
            else:
                raise ValueError(stream.kind)
            stream.source = self


def input_file(filename: str, *streams: Stream, **kwargs: Any) -> Input:
    kwargs['input_file'] = filename
    if streams:
        for i, stream in enumerate(streams):
            if stream.meta and not stream.meta.stream:
                stream.meta.stream = f'{filename}#{i}'
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