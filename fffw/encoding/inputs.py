from dataclasses import field
from typing import Optional, List, Tuple

from fffw.graph import base
from fffw.graph.meta import Meta
from fffw.wrapper import BaseWrapper, ensure_binary

__all__ = [
    'Input',
    'InputList',
    'Stream',
    'Input',
]


class Stream(base.Source):
    """ Video or audio stream in input file."""

    def __init__(self, kind: base.StreamType, meta: Optional[Meta] = None):
        """
        :param kind: stream kind, video or audio
        :param meta: stream metadata
        """
        super().__init__(None, kind)
        self._meta = meta
        self.source: Optional[Input] = None
        """ Source file that contains current stream."""
        self.index: Optional[int] = None
        """ Index of current stream in source file."""

    @property
    def name(self):
        if self.index == 0:
            return f'{self.source.index}:{self._kind.value}'
        return f'{self.source.index}:{self._kind.value}:{self.index}'

    @property
    def kind(self) -> base.StreamType:
        return self._kind


class Input(BaseWrapper):
    """
    Input command line params generator for FFMPEG.
    """
    """ Filename or url, value for `-i` argument."""
    streams: Tuple[Stream, ...] = field(default=None)
    """ List of audio and video streams for input file."""
    index: int = field(default=0, init=False)
    """ Internal ffmpeg source file index."""

    def __init__(self, *streams: Stream, input_file: str = ''):
        super().__init__()
        self.streams = streams or (Stream(base.VIDEO), Stream(base.AUDIO))
        self.index = 0
        self.input_file = input_file
        self.__link_streams_to_input()

    def __link_streams_to_input(self):
        """
        Add a link to self to input streams and enumerate streams to get
        proper stream index for input.
        """
        video_streams = 0
        audio_streams = 0
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
        self.inputs: List[Input] = []
        self.extend(*sources)

    @property
    def streams(self) -> List[Stream]:
        result = []
        for source in self.inputs:
            result.extend(source.streams)
        return result

    def append(self, source: Input) -> None:
        """
        Adds new source file to input list.

        :param source: input file
        """
        source.index = len(self.inputs)
        self.inputs.append(source)

    def extend(self, *sources: Input) -> None:
        """
        Adds multiple source files to input list.

        :param sources: list of input files
        """
        for i, source in enumerate(sources, start=len(self.inputs)):
            source.index = i
        self.inputs.extend(sources)

    def get_args(self) -> List[bytes]:
        result = []
        for source in self.inputs:
            result.extend(source.get_args())
        return result
