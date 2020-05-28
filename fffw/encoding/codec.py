import abc
from typing import List

from fffw.graph import base
from fffw.wrapper import BaseWrapper

__all__ = [
    'VideoCodec',
    'AudioCodec',
]


class BaseCodec(BaseWrapper, base.Node, metaclass=abc.ABCMeta):
    """
    Abstract base class for codec nodes.
    """
    codec_type: base.StreamType

    arguments = [('map', '-map ')]

    @property
    def enabled(self) -> bool:
        return True

    @enabled.setter
    def enabled(self, value: bool) -> None:
        raise RuntimeError("codecs can't be disabled")

    @property
    @abc.abstractmethod
    def codec_name(self) -> str:
        raise NotImplementedError()

    @property
    def map(self) -> str:
        return self._args['map']

    @map.setter
    def map(self, value: str) -> None:
        self._args['map'] = value

    def render(self, partial: bool = False) -> List[str]:
        """ codec output node is already rendered in filter graph."""
        return []

    def connect(self, dest: base.Dest) -> None:
        """ Connects destination to codec node."""
        assert isinstance(dest, base.Dest), "Codec connects to Dest"
        self.map = f'[{dest.name}]'

    def __repr__(self) -> str:
        return "<%s>(%s)" % (
            self.codec_name,
            ','.join('%s=%s' % (k, self._args[k]) for k in self._key_mapping
                     if self._args[k])
        )

    def connect_edge(self, edge: base.Edge
                     ) -> base.Edge:
        """ Connects source to codec through an edge."""
        src = edge.input
        assert isinstance(src, base.Source), "Codec connects to Source"
        assert src.name, "Source file has not stream of desired type"
        if self.map:
            # normal Node can connect with source single time only,
            # BaseCodec can connect multiple times via "-map" arguments

            # FIXME: GH/JW #2 this should return base.Edge. See Source._edge
            # noinspection PyTypeChecker
            return None  # type: ignore
        self.map = src.name
        return edge


class VideoCodec(BaseCodec):
    codec_type = base.VIDEO
    arguments = [
        ('map', '-map '),
        ('vbsf', '-bsf:v '),
        ('vcodec', '-c:v '),
        ('pass', '-pass '),
        ('pix_fmt', '-pix_fmt '),
        ('preset', '-preset '),
        ('tune', '-tune '),
        ('flags', '-flags '),
        ('force_key_frames', '-force_key_frames '),
        ('vprofile', '-profile:v '),
        ('level', '-level '),
        ('crf', '-crf '),
        ('minrate', '-minrate '),
        ('maxrate', '-maxrate '),
        ('bufsize', '-bufsize '),
        ('gop', '-g '),
        ('vrate', '-r '),
        ('vbitrate', '-b:v '),
        ('vaspect', '-aspect '),
        ('reframes', '-refs '),
        ('mbd', '-mbd '),
        ('trellis', '-trellis '),
        ('cmp', '-cmp '),
        ('subcmp', '-subcmp '),
        ('x265', '-x265-params '),
    ]

    @property
    def codec_name(self) -> str:
        return self._args['vcodec']


class AudioCodec(BaseCodec):
    codec_type = base.AUDIO
    arguments = [
        ('map', '-map '),
        ('absf', '-bsf:a '),
        ('acodec', '-c:a '),
        ('aprofile', '-profile:a '),
        ('abitrate', '-b:a '),
        ('arate', '-ar '),
        ('achannels', '-ac '),
    ]

    @property
    def codec_name(self) -> str:
        return self._args['acodec']
