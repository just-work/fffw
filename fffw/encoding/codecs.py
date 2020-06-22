from fffw.graph.meta import VIDEO, AUDIO
from fffw.encoding import outputs

__all__ = [
    'AudioCodec',
    'VideoCodec',
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
