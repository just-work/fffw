from dataclasses import field, dataclass
from typing import NoReturn

from fffw.encoding import outputs
from fffw.graph import base
from fffw.graph.meta import VIDEO, AUDIO, StreamType

__all__ = [
    'AudioCodec',
    'VideoCodec',
    'Copy',
]


class VideoCodec(outputs.Codec):
    """
    Base class for describing video codecs.

    See `fffw.encoding.outputs.Codec` for params definition.

    >>> from dataclasses import dataclass
    >>> from fffw.wrapper import param
    >>> @dataclass
    ... class X264(VideoCodec):
    ...     codec = 'libx264'
    ...     gop: int = param(name='g')
    ...
    >>> codec = X264(bitrate=4000000, gop=25)
    >>> copy = VideoCodec('copy')
    """
    kind = VIDEO


class AudioCodec(outputs.Codec):
    """
    Base class for describing audio codecs.

    See :py:class:`fffw.encoding.outputs.Codec` for params definition.

    >>> from dataclasses import dataclass
    >>> from fffw.wrapper import param
    >>> @dataclass
    ... class FdkAAC(AudioCodec):
    ...     codec = 'libfdk_aac'
    ...     rate: int = param(default=48000, name='r')
    ...
    >>> codec = FdkAAC(bitrate=192000, rate=44100)
    >>> copy = AudioCodec('copy')
    """
    kind = AUDIO


def _not_implemented() -> NoReturn:
    """
    A hack around MyPy dataclass handling.
    """
    raise NotImplementedError()


@dataclass
class Copy(outputs.Codec):
    codec = 'copy'
    kind: StreamType = field(metadata={'skip': True},
                             # There should be no default, but base class
                             # already defines fields with default and thus
                             # dataclass can't be created.
                             default_factory=_not_implemented)

    def connect_edge(self, edge: base.Edge) -> base.Edge:
        if not isinstance(edge.input, base.Source):
            raise ValueError('copy codec can be connected only to source')
        return super().connect_edge(edge)
