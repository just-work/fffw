from dataclasses import dataclass, field
from typing import Optional, List, Tuple

from fffw.graph import StreamType
from fffw.graph.meta import Meta
from fffw.wrapper import BaseWrapper


class Stream:
    """ Video or audio stream in input file."""
    def __init__(self, kind: StreamType,
                 meta: Optional[Meta] = None):
        """
        :param kind: stream kind, video or audio
        :param meta: stream metadata
        """
        self._kind = kind
        self._meta = meta
        self.source: Optional[BaseInput] = None
        """ Source file that contains current stream."""
        self.index: Optional[int] = None
        """ Index of current stream in source file."""

    @property
    def name(self):
        return f'{self.source.index}:{self._kind.value}:{self.index}'

    @property
    def kind(self) -> StreamType:
        return self._kind


@dataclass
class BaseInput(BaseWrapper):
    """
    Input command line params generator for FFMPEG.
    """
    input_file: str
    """ Filename or url, value for `-i` argument."""
    streams: Tuple[Stream, ...] = field(default=None)
    """ List of audio and video streams for input file."""
    index: int = field(default=0, init=False)
    """ Internal ffmpeg source file index."""

    def __post_init__(self):
        """ Performs streams enumeration for proper stream id generation."""
        if not self.streams:
            self.streams = (Stream(StreamType.VIDEO), Stream(StreamType.AUDIO))
        video_streams = 0
        audio_streams = 0
        for stream in self.streams:
            if stream.kind == StreamType.VIDEO:
                stream.index = video_streams
                video_streams += 1
            elif stream.kind == StreamType.AUDIO:
                stream.index = audio_streams
                audio_streams += 1
            else:
                raise ValueError(stream.kind)
            stream.source = self


class InputList:
    """ List of inputs in FFMPEG."""

    def __init__(self, *sources: BaseInput) -> None:
        """
        :param sources: list of input files
        """
        self.inputs: List[BaseInput] = []
        self.extend(*sources)

    def append(self, source: BaseInput) -> None:
        """
        Adds new source file to input list.

        :param source: input file
        """
        source.index = len(self.inputs)
        self.inputs.append(source)

    def extend(self, *sources: BaseInput) -> None:
        """
        Adds multiple source files to input list.

        :param sources: list of input files
        """
        for i, source in enumerate(sources, start=len(self.inputs)):
            source.index = i
        self.inputs.extend(sources)
