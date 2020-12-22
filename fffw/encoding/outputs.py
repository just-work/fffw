from dataclasses import dataclass
from itertools import chain
from typing import List, cast, Optional, Iterable, Any

from fffw.graph.meta import AUDIO, VIDEO, StreamType
from fffw.graph import base
from fffw.wrapper import BaseWrapper, ensure_binary, param
from fffw.encoding import mixins
__all__ = [
    'Codec',
    'Output',
    'OutputList',
    'output_file',
]


@dataclass
class Codec(mixins.StreamValidationMixin, base.Dest, BaseWrapper):
    # noinspection PyUnresolvedReferences
    """
    Base class for output codecs.

    :arg codec: ffmpeg codec name.
    :arg bitrate: output bitrate in bps.
    """

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

    def clone(self, count: int = 1) -> List["Codec"]:
        """
        Creates multiple copies of self to reuse it as output node for multiple
        sources.

        Any connected input node is being split and connected to a corresponding
        copy of current filter.
        """
        if count == 1:
            return [self]
        raise RuntimeError("Trying to clone codec, is this intended?")

    def check_buffering(self) -> Optional[List[str]]:
        """
        Check that scenes read from input stream are ordered with ascending
        timestamps.

        :returns: A list of streams needed for this codec or None if metadata
            for codec can't be computed.
        """
        meta = self.get_meta_data()
        if not meta:
            return None
        prev = meta.scenes[0]
        for scene in meta.scenes[1:]:
            if prev.stream == scene.stream and prev.end > scene.start:
                # Previous scene in same stream is located after current, so
                # current decoded scene will be buffered until previous scene is
                # decoded.
                raise BufferError(prev, scene)
            prev = scene
        return meta.streams


@dataclass
class Output(BaseWrapper):
    # noinspection PyUnresolvedReferences
    """
    Base class for ffmpeg output.

    :arg codecs: list of codecs used in output.
    :arg format: output file format.
    :arg output_file: output file name.
    """
    codecs: List[Codec] = param(default=list, skip=True)
    no_video: Optional[bool] = param(name='vn')
    no_audio: Optional[bool] = param(name='an')
    format: str = param(name="f")
    output_file: str = param(name="", skip=True)

    def __lt__(self, other: base.InputType) -> "Output":
        """
        Connects a source or a filter to a first free codec.

        If there is no free codecs, new codec stub is created.
        """
        codec = self.get_free_codec(other.kind)
        other.connect_dest(codec)
        return self

    @property
    def video(self) -> Codec:
        """
        :returns: first video codec not connected to source.

        If no free codecs left, new one codec stub is appended to output.
        """
        return self.get_free_codec(VIDEO)

    @property
    def audio(self) -> Codec:
        """
        :returns: first audio codec not connected to source.

        If no free codecs left, new one codec stub is appended to output.
        """
        return self.get_free_codec(AUDIO)

    def get_free_codec(self, kind: StreamType, create: bool = True
                       ) -> Codec:
        """
        Finds first codec not connected to filter graph or to an input, or
        creates a new unnamed codec stub if no free codecs left.

        :param kind: desired codec stream type
        :param create: create new codec stub
        :return: first free codec or a new codec stub.
        """
        try:
            codec = next(filter(
                lambda c: not c.connected and c.kind == kind, self.codecs))
        except StopIteration:
            if not create:
                raise KeyError(kind)
            codec = Codec()
            codec.kind = kind
            self.codecs.append(codec)
        return codec

    def get_args(self) -> List[bytes]:
        """
        :returns: codec args and output file parameters for ffmpeg
        """
        args = []
        # Check if we need to disable audio or video for output file because no
        # corresponding codecs are found.
        # Skipping `-an` / `-vn` parameters is still supported by  manually
        # setting `no_audio` / `no_video` parameters to `False`.
        for codec in self.codecs:
            if codec.kind == VIDEO:
                self.no_video = False
            if codec.kind == AUDIO:
                self.no_audio = False
            args.extend(codec.get_args())
        if self.no_video is None:
            self.no_video = True
        if self.no_audio is None:
            self.no_audio = True
        args.extend(super().get_args())
        args.append(ensure_binary(self.output_file))
        return args


def output_file(filename: str, *codecs: Codec, **kwargs: Any) -> Output:
    """
    A shortcut to create proper output file.
    :param filename: output file name.
    :param codecs: codec list for this output.
    :param kwargs: output parameters.
    :return: configured ffmpeg output.
    """
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
        if codec.kind == VIDEO:
            codec.index = self.__video_index
            self.__video_index += 1
        else:
            codec.index = self.__audio_index
            self.__audio_index += 1
