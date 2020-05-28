from typing import Optional, List, Tuple, TypeVar, Type, cast, Any

from fffw.graph import base
from fffw.graph.meta import Meta
from fffw.wrapper import BaseWrapper, ensure_binary

__all__ = [
    'Input',
    'InputList',
    'Stream',
    'Input',
]

Obj = TypeVar('Obj')


class Once:
    """ Property that must be set exactly once."""

    def __init__(self, attr_name: str) -> None:
        """
        :param attr_name: instance attribute name
        """
        self.attr_name = attr_name

    def __get__(self, instance: Obj, owner: Type[Obj]) -> Any:
        try:
            return instance.__dict__[self.attr_name]
        except KeyError:
            raise RuntimeError(f"{self.attr_name} is not initialized")

    def __set__(self, instance: Obj, value: Any) -> None:
        if self.attr_name in instance.__dict__:
            raise RuntimeError(f"{self.attr_name} already initialized")
        instance.__dict__[self.attr_name] = value


class Stream(base.Source):
    """ Video or audio stream in input file."""
    source = cast("Input", Once('source'))
    """ Source file that contains current stream."""
    index = cast(int, Once('index'))
    """ Index of current stream in source file."""

    def __init__(self, kind: base.StreamType, meta: Optional[Meta] = None):
        """
        :param kind: stream kind, video or audio
        :param meta: stream metadata
        """
        super().__init__(name=None, kind=kind, meta=meta)

    @property
    def name(self) -> str:
        if self.index == 0:
            return f'{self.source.index}:{self._kind.value}'
        return f'{self.source.index}:{self._kind.value}:{self.index}'


class Input(BaseWrapper):
    """
    Input command line params generator for FFMPEG.
    """
    """ Filename or url, value for `-i` argument."""
    streams = cast(Tuple[Stream, ...], Once("streams"))
    """ List of audio and video streams for input file."""
    index = cast(int, Once("index"))
    """ Internal ffmpeg source file index."""

    def __init__(self, *streams: Stream, input_file: str = ''):
        super().__init__()
        self.streams = streams or (Stream(base.VIDEO), Stream(base.AUDIO))
        self.input_file = input_file
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

    def get_args(self) -> List[bytes]:
        return ensure_binary(["-i", self.input_file])


class InputList:
    """ List of inputs in FFMPEG."""

    def __init__(self, *sources: Input) -> None:
        """
        :param sources: list of input files
        """
        self.__inputs: List[Input] = []
        self.extend(*sources)

    @property
    def inputs(self) -> Tuple[Input, ...]:
        return tuple(self.__inputs)

    @property
    def streams(self) -> List[Stream]:
        result: List[Stream] = []
        for source in self.__inputs:
            if source.streams is None:
                raise RuntimeError("Source streams not initialized")
            result.extend(source.streams)
        return result

    def append(self, source: Input) -> None:
        """
        Adds new source file to input list.

        :param source: input file
        """
        source.index = len(self.__inputs)
        self.__inputs.append(source)

    def extend(self, *sources: Input) -> None:
        """
        Adds multiple source files to input list.

        :param sources: list of input files
        """
        for i, source in enumerate(sources, start=len(self.__inputs)):
            source.index = i
        self.__inputs.extend(sources)

    def get_args(self) -> List[bytes]:
        result = []
        for source in self.__inputs:
            result.extend(source.get_args())
        return result
