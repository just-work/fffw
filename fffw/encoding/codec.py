# coding: utf-8

# $Id: $
from fffw.graph.base import VIDEO, AUDIO, Dest
from fffw.wrapper import BaseWrapper

__all__ = [
    'VideoCodec',
    'AudioCodec'
]


class BaseCodec(BaseWrapper):
    codec_type = None

    def connect(self, dest):
        assert isinstance(dest, Dest), "Codec must connect to Dest"
        self.map = '[%s]' % dest.id


class VideoCodec(BaseCodec):
    codec_type = VIDEO
    arguments = [
        ('map', '-map '),
        ('codec', '-c:v '),
        ('pass', '-pass '),
        ('pix_fmt', '-pix_fmt '),
        ('preset', '-preset '),
        ('tune', '-tune '),
        ('flags', '-flags '),
        ('force_key_frames', '-force_key_frames '),
        ('profile', '-profile:v '),
        ('frames', '-vframes '),
        ('level', '-level '),
        ('crf', '-crf '),
        ('minrate', '-minrate '),
        ('maxrate', '-maxrate '),
        ('bufsize', '-bufsize '),
        ('gop', '-g '),
        ('rate', '-r '),
        ('bitrate', '-b:v '),
        ('aspect', '-aspect '),
        ('novideo', '-vn '),
    ]


class AudioCodec(BaseCodec):
    codec_type = AUDIO
    arguments = [
        ('map', '-map '),
        ('codec', '-c:a '),
        ('profile', '-profile:a '),
        ('bitrate', '-b:a '),
        ('rate', '-ar '),
        ('channels', '-ac '),
        ('noaudio', '-an '),
    ]

