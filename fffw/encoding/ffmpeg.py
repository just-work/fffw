# coding: utf-8

# $Id: $
from fffw.encoding import Muxer
from fffw.encoding.codec import BaseCodec
from fffw.graph import FilterComplex
from fffw.graph.base import VIDEO, AUDIO, SourceFile
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
        ('inputformat', '-f '),
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

    def __init__(self, inputfile=None, **kw):
        super(FFMPEG, self).__init__(**kw)
        self._args['inputfile'] = self.__inputs = []
        self.__outputs = []
        self.__vdest = self.__adest = 0

        if isinstance(inputfile, SourceFile):
            self.add_input(inputfile)
        elif isinstance(inputfile, (list, tuple)):
            for input in inputfile:
                self.add_input(input)
        else:
            assert inputfile is None, "invalid inputfile type"

    def init_filter_complex(self, video_inputs=None, audio_inputs=None,
                            video_outputs=1, audio_outputs=None):
        assert self.__inputs, "no inputs defined yet"
        assert not self.__outputs, "outputs already defined"
        if video_inputs is None:
            video_inputs = sum(map(lambda i: i.video_streams, self.__inputs))
        if audio_inputs is None:
            audio_inputs = sum(map(lambda i: i.audio_streams, self.__inputs))

        if not audio_inputs and audio_outputs is None:
            audio_outputs = 0

        self._args['filter_complex'] = fc = FilterComplex(
            inputs=video_inputs,
            audio_inputs=audio_inputs
        )
        return fc

    @property
    def filter_complex(self):
        """:rtype: FilterComplex"""
        return self._args['filter_complex']

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

    def add_input(self, input):
        """ Добавляет новый входящий файл.

        :type input: graph.base.SourceFile
        """
        assert not self.filter_complex, "filter complex already initialized"
        assert isinstance(input, SourceFile)
        self.__inputs.append(input)

    def add_output(self, muxer, *codecs):
        assert isinstance(muxer, Muxer)
        for c in codecs:
            assert isinstance(c, BaseCodec)
            fc = self.filter_complex
            if not fc:
                continue
            if c.codecname == 'copy':
                continue
            if c.codec_type == VIDEO:
                c.connect(
                    fc.get_video_dest(self.__vdest, create=False))
                self.__vdest += 1
            if c.codec_type == AUDIO:
                try:
                    c.connect(fc.get_audio_dest(self.__adest, create=False))
                    self.__adest += 1
                except IndexError:
                    c.map = '0:a'

        self.__outputs.append((codecs, muxer))

    @property
    def outputs(self):
        return list(self.__outputs)

    def __lt__(self, other):
        """ Добавляет новый входящий файл.

        :type other: graph.base.SourceFile
        """
        return self.add_input(other)

    def __setattr__(self, key, value):
        if key == 'filter_complex':
            raise NotImplementedError("use init_filter_complex instead")
        if key == 'inputfile':
            raise NotImplementedError("use add_input instead")
        return super(FFMPEG, self).__setattr__(key, value)
