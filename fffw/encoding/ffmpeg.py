# coding: utf-8

# $Id: $
from fffw.encoding import Muxer
from fffw.encoding.codec import BaseCodec
from fffw.graph import FilterComplex
from fffw.graph.base import VIDEO, AUDIO
from fffw.wrapper import BaseWrapper, ensure_binary

__all__ = [
    'FFMPEG'
]


def flatten(l):
    return [item for sublist in l for item in sublist]


class FFMPEG(BaseWrapper):
    command = 'ffmpeg'
    arguments = [
        ('strict', '-strict '),
        ('realtime', '-re '),
        ('threads', '-threads '),
        ('time_offset', '-ss '),
        ('no_autorotate', '-noautorotate'),
        ('inputfile', '-i '),
        ('presize_offset', '-ss '),
        ('filter_complex', '-filter_complex '),
        ('time_limit', '-t '),
        ('vframes', '-vframes '),
        ('overwrite', '-y '),
        ('verbose', '-v '),
        ('novideo', '-vn '),
        ('noaudio', '-an '),
        ('vfilter', '-vf '),
        ('afilter', '-af '),
        ('metadata', '-metadata '),
        ('map_chapters', '-map_chapters '),
        ('map_metadata', '-map_metadata '),
        ('vbsf', '-bsf:v '),
        ('absf', '-bsf:a '),
        ('format', '-f '),
    ]

    def __init__(self, **kw):
        super(FFMPEG, self).__init__(**kw)
        self.__outputs = []
        self.__dest_count = None
        self.__vdest = self.__adest = 0

    @property
    def filter_complex(self):
        """:rtype: FilterComplex"""
        return self._args['filter_complex']

    @filter_complex.setter
    def filter_complex(self, value):
        assert isinstance(value, FilterComplex)
        assert not self.__outputs
        self._args['filter_complex'] = value
        self.__dest_count = max(len(value.video_outputs),
                                len(value.audio_outputs))

    def get_args(self):
        return ensure_binary(
            [self.command] +
            super(FFMPEG, self).get_args() +
            self.get_output_args())

    def get_output_args(self):
        result = []
        for codecs, muxer in self.__outputs:
            args = flatten(c.get_args() for c in codecs)
            result.extend(muxer.get_args() + args + [muxer.output])
        return result

    def add_output(self, muxer, *codecs):
        assert isinstance(muxer, Muxer)
        for c in codecs:
            assert isinstance(c, BaseCodec)
            if not self.filter_complex:
                continue
            if c.codecname == 'copy':
                continue
            if c.codec_type == VIDEO:
                c.connect(self.filter_complex.video_outputs[self.__vdest])
                self.__vdest += 1
            if c.codec_type == AUDIO:
                try:
                    c.connect(self.filter_complex.audio_outputs[self.__adest])
                    self.__adest += 1
                except IndexError:
                    c.map = '0:a'

        self.__outputs.append((codecs, muxer))

    @property
    def outputs(self):
        return list(self.__outputs)
