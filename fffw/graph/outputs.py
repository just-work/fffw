import os
from itertools import chain
from typing import List, Tuple, cast, Optional, Any

from fffw.graph import base
from fffw.wrapper import BaseWrapper, ensure_binary

__all__ = [
    'Codec',
    'Output',
    'OutputList'
]


class Codec(base.Dest, BaseWrapper):
    index = cast(int, base.Once('index'))
    """ Index of current codec in ffmpeg output streams."""
    # TODO #9: implement single argument with stream type modifier
    arguments = [
        ('vbitrate', '-b:v '),
        ('abitrate', '-b:a '),
    ]

    def __init__(self, kind: base.StreamType, codec: str = None,
                 **kwargs: Any) -> None:
        super().__init__(kind)
        BaseWrapper.__init__(self, **kwargs)
        self._codec = codec

    @property
    def map(self) -> Optional[base.InputType]:
        """ Returns a source or a filter connected to this codec."""
        if not self.edge:
            return None
        return self.edge.input

    def get_args(self) -> List[bytes]:
        if self.edge is None:
            raise RuntimeError("Codec not connected to source")
        source = self.edge.input
        if isinstance(source, base.Node):
            mapping = self.edge.name
        else:
            mapping = source.name
        args = ['-map', mapping]
        if self._codec:
            args.extend([f'-c:{self.kind.value}', self._codec])
        return ensure_binary(args) + super().get_args()


class Output(BaseWrapper):
    arguments = [
        ('format', '-f '),
    ]

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
            codec = next(filter(lambda c: not c.map, self._codecs))
        except StopIteration:
            codec = Codec(kind)
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
