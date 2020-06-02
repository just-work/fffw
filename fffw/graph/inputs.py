from dataclasses import dataclass
from typing import Optional, List, Tuple, cast, Iterable, Union, Any

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


@dataclass
class Input(BaseWrapper):
    """
    Input command line params generator for FFMPEG.
    """
    index = cast(int, base.Once("index"))
    """ Internal ffmpeg source file index."""
    streams: Tuple[Stream, ...] = param(
        default=lambda: (Stream(base.VIDEO), Stream(base.AUDIO)), skip=True)
    """ List of audio and video streams for input file."""

    fast_seek: Union[TS, float, int] = param(name='ss')
    input_file: str = param(name='i')
    slow_seek: Union[TS, float, int] = param(name='ss')
    duration: Union[TS, float, int] = param(name='t')

    def __post_init__(self) -> None:
        super().__post_init__()
        self.__link_streams_to_input()

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
