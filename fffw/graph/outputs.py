import os
from dataclasses import dataclass
from itertools import chain
from typing import List, Tuple, cast, Optional, Any

from fffw.graph import base
from fffw.wrapper import BaseWrapper, ensure_binary, param

__all__ = [
    'Output',
    'OutputList'
]


@dataclass
class Codec(base.Dest, BaseWrapper):
    index = cast(int, base.Once('index'))
    """ Index of current codec in ffmpeg output streams."""

    codec: str = param(name='c', stream_suffix=True)
    bitrate: int = param(default=0, name='b', stream_suffix=True)

    @property
    def map(self) -> Optional[str]:
        """
        :returns: `-map` argument value depending of a node or a source
        connected to codec.
        """
        if self.edge is None:
            raise RuntimeError("Codec not connected to source")
        source = self.edge.input
        # Source input has name generated from input file index, stream
        # specifier and stream index. Node has no attribute index, so we use
        # Dest name ("[vout0]") as map argument. See also `Node.get_filter_args`
        return getattr(source, 'name', self.name)

    @property
    def connected(self) -> bool:
        """
        :return: True if codec is already connected to a node or a source.
        """
        return bool(self.edge)

    def get_args(self) -> List[bytes]:
        args = ['-map', self.map]
        return ensure_binary(args) + super().get_args()


@dataclass
class OutputParams:
    """ Output file parameters"""
    format: str = param(name="f")


class Output(OutputParams, BaseWrapper):

    def __init__(self, output_file: str, *codecs: Codec, **kwargs: Any) -> None:
        ext = os.path.splitext(output_file)[-1].lstrip('.')
        kwargs.setdefault('format', ext)
        super().__init__(**kwargs)
        self._output_file = output_file
        self._codecs = list(codecs)

    def __lt__(self, other: base.InputType) -> Codec:
        """
        Connects a source or a filter to a first free codec.

        If there is no free codecs, new codec stub is created.
        """
        codec = self.get_free_codec(other.kind)
        other.connect_dest(codec)
        return codec

    @property
    def codecs(self) -> Tuple[Codec, ...]:
        return tuple(self._codecs)

    @property
    def video(self) -> Codec:
        return self.get_free_codec(base.VIDEO)

    @property
    def audio(self) -> Codec:
        return self.get_free_codec(base.AUDIO)

    def get_free_codec(self, kind: base.StreamType) -> Codec:
        try:
            codec = next(filter(lambda c: not c.connected, self._codecs))
        except StopIteration:
            codec = Codec()
            codec.kind = kind
            self._codecs.append(codec)
        return codec

    def get_args(self) -> List[bytes]:
        args = (
                list(chain(*(codec.get_args() for codec in self._codecs))) +
                super().get_args() +
                ensure_binary([self._output_file])
        )
        return args


class OutputList:
    """ Supports unique output streams names generation."""

    def __init__(self, *outputs: Output) -> None:
        """
        :param outputs: list of output files
        """
        self.__outputs: List[Output] = []
        self.__video_index = 0
        self.__audio_index = 0
        self.extend(*outputs)

    @property
    def outputs(self) -> Tuple[Output, ...]:
        return tuple(self.__outputs)

    @property
    def codecs(self) -> List[Codec]:
        result: List[Codec] = []
        for output in self.__outputs:
            result.extend(output.codecs)
        return result

    def append(self, output: Output) -> None:
        """
        Adds new output file to output list.

        :param output: output file
        """
        for codec in output.codecs:
            self.__set_index(codec)
        self.__outputs.append(output)

    def extend(self, *outputs: Output) -> None:
        """
        Adds multiple output files to output list.

        :param outputs: list of output files
        """
        for codec in chain(*map(lambda output: output.codecs, outputs)):
            self.__set_index(codec)
        self.__outputs.extend(outputs)

    def get_args(self) -> List[bytes]:
        result = []
        for source in self.__outputs:
            result.extend(source.get_args())
        return result

    def __set_index(self, codec: Codec) -> None:
        if codec.kind == base.VIDEO:
            codec.index = self.__video_index
            self.__video_index += 1
        else:
            codec.index = self.__audio_index
            self.__audio_index += 1
