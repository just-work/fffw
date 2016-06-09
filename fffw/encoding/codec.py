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

    def __repr__(self):
        return "<%s>(%s)" % (
            self.codecname,
            ','.join('%s=%s' % (k, self._args[k]) for k in self._key_mapping
                     if self._args[k])
        )

    @property
    def codecname(self):
        return self._args['codec']


class VideoCodec(BaseCodec):
    codec_type = VIDEO
    arguments = [
        ('map', '-map '),
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
    def codecname(self):
        return self._args['vcodec']

class AudioCodec(BaseCodec):
    codec_type = AUDIO
    arguments = [
        ('map', '-map '),
        ('acodec', '-c:a '),
        ('aprofile', '-profile:a '),
        ('abitrate', '-b:a '),
        ('arate', '-ar '),
        ('achannels', '-ac '),
    ]

    @property
    def codecname(self):
        return self._args['acodec']
