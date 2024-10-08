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
        # Running parent method for side effects like stream validation, like if
        # Copy is compatible with filter graph.
        super().connect_edge(edge)

        # Ensure that between source stream and copy codec there is no
        # processing filters. Only split filter is allowed.
        src = self._validate_filter_chain(edge)

        if edge.input is src:
            # Copy codec is being connected directly to Source, no more actions
            # are needed.
            return edge

        # There are some Splits between Source and Copy. Current edge is not
        # needed anymore because new Edge will be added directly to the Source.
        # Recursively removing it from Splits chain.
        self._remove_edge(edge)
        # Connecting Copy to a Source directly using new node.
        src.connect_dest(self)
        return self.edge

    def _remove_edge(self, edge: base.Edge) -> None:
        """
        Remove edge mentions from graph and current instance like it never
        existed.

        This method is used for reconnecting Copy codec from an end of Split
        filter chain directly to Source.
        """
        # Remove and edge from existing Split filter chain
        split = edge.input
        if not isinstance(split, filters.Split):  # pragma: no cover
            # Method is only called from connect_edge() in case of split
            # filter presence.
            raise TypeError("Can't disconnect and edge from real filter")
        split.disconnect(edge)
        # As the Edge is thrown away, forgot about it.
        self._edge = None

    @staticmethod
    def _validate_filter_chain(edge: base.Edge) -> base.Source:
        """
        Ensures that Copy codec is being connected to a filter chain that
        contains only Split filters.

        :returns: Source stream passed to Copy codec.
        """
        src = edge.input
        # Ensure that edge is connected to a source with only split filters
        # in between.
        while isinstance(src, filters.Split):
            edge = src.input
            if edge is None:
                raise RuntimeError("Input edge not connected")
            src = edge.input
        if not isinstance(src, base.Source):
            raise ValueError('copy codec can be connected only to source')
        return src
