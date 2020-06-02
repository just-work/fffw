from dataclasses import dataclass
from itertools import chain
from typing import List, cast, Optional, Iterable, Any

from fffw.graph import base
from fffw.wrapper import BaseWrapper, ensure_binary, param

__all__ = [
    'Codec',
    'Output',
    'OutputList',
    'output_file',
]


@dataclass
class Codec(base.Dest, BaseWrapper):
    index = cast(int, base.Once('index'))
    """ Index of current codec in ffmpeg output streams."""

    codec: str = param(name='c', stream_suffix=True)
    bitrate: int = param(default=0, name='b', stream_suffix=True)

    def __post_init__(self) -> None:
        if self.codec is None:
            self.codec = self.__class__.codec
        super().__post_init__()

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
class Output(BaseWrapper):
    codecs: List[Codec] = param(skip=True)
    format: str = param(name="f")
    output_file: str = param(name="")

    def __lt__(self, other: base.InputType) -> Codec:
        """
        Connects a source or a filter to a first free codec.

        If there is no free codecs, new codec stub is created.
        """
        codec = self.get_free_codec(other.kind)
        other.connect_dest(codec)
        return codec

    @property
    def video(self) -> Codec:
        return self.get_free_codec(base.VIDEO)

    @property
    def audio(self) -> Codec:
        return self.get_free_codec(base.AUDIO)

    def get_free_codec(self, kind: base.StreamType) -> Codec:
        try:
            codec = next(filter(lambda c: not c.connected, self.codecs))
        except StopIteration:
            codec = Codec()
            codec.kind = kind
            self.codecs.append(codec)
        return codec

    def get_args(self) -> List[bytes]:
        args = (
                list(chain(*(codec.get_args() for codec in self.codecs))) +
                super().get_args()
        )
        return args


def output_file(filename: str, *codecs: Codec, **kwargs: Any) -> Output:
    return Output(output_file=filename, codecs=list(codecs), **kwargs)


class OutputList(list):
    """ Supports unique output streams names generation."""

    def __init__(self, outputs: Iterable[Output] = ()) -> None:
        """
        :param outputs: list of output files
        """
        super().__init__()
        self.__video_index = 0
        self.__audio_index = 0
        self.extend(outputs)

    @property
    def codecs(self) -> List[Codec]:
        result: List[Codec] = []
        for output in self:
            result.extend(output.codecs)
        return result

    def append(self, output: Output) -> None:
        """
        Adds new output file to output list.

        :param output: output file
        """
        for codec in output.codecs:
            self.__set_index(codec)
        super().append(output)

    def extend(self, outputs: Iterable[Output]) -> None:
        """
        Adds multiple output files to output list.

        :param outputs: list of output files
        """
        for codec in chain(*map(lambda output: output.codecs, outputs)):
            self.__set_index(codec)
        super().extend(outputs)

    def get_args(self) -> List[bytes]:
        result: List[bytes] = []
        for source in self:
            result.extend(source.get_args())
        return result

    def __set_index(self, codec: Codec) -> None:
        if codec.kind == base.VIDEO:
            codec.index = self.__video_index
            self.__video_index += 1
        else:
            codec.index = self.__audio_index
            self.__audio_index += 1
