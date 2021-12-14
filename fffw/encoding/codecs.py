from dataclasses import field, dataclass
from typing import NoReturn

from fffw.encoding import outputs, filters
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
        """
        Cuts out a graph path that leads from input stream to copy codec.

        * copy codec cannot be used with filtered frames because they are not
          even decoded
        * when using vectorized processing to construct processing graph,
          intermediate vectors don't know whether their output will be connected
          to a copy codec or to another filter
        * so input streams for complex vectors are connected to split filters
        * to copy codec properly, after all there split filters must be
          disconnected from input stream
        * if there is any another filter except split, it's an error

        :returns: edge pointing to an input stream
        """
        src = edge.input
        # Ensure that edge is connected to a source with only split filters
        # in between.
        while isinstance(src, filters.Split):
            src = src.input.input
        if not isinstance(src, base.Source):
            raise ValueError('copy codec can be connected only to source')
        src = edge.input
        if isinstance(src, filters.Split):
            # Remove current edge from filter graph
            edge = src.disconnect(edge)
        return super().connect_edge(edge)
