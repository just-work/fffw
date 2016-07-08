# coding: utf-8

# $Id: $
from itertools import chain

from fffw.encoding import Muxer
from fffw.encoding.codec import BaseCodec
from fffw.graph import FilterComplex, base
from fffw.wrapper import BaseWrapper, ensure_binary


__all__ = ['FFMPEG']


class FFMPEG(BaseWrapper):
    command = 'ffmpeg'

    # noinspection SpellCheckingInspection
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

        self.__video = base.Input(kind=base.VIDEO)
        self.__audio = base.Input(kind=base.AUDIO)

        if isinstance(inputfile, base.SourceFile):
            self.add_input(inputfile)
        elif isinstance(inputfile, (list, tuple)):
            for i in inputfile:
                self.add_input(i)
        else:
            assert inputfile is None, "invalid inputfile type"

    def init_filter_complex(self):
        # assert self.__inputs, "no inputs defined yet"
        # assert not self.__outputs, "outputs already defined"
        #
        self._args['filter_complex'] = fc = FilterComplex(
            video=self.__video,
            audio=self.__audio
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
            args = list(chain.from_iterable(c.get_args() for c in codecs))
            result.extend(muxer.get_args() + args + [muxer.output])
        return result

    def add_input(self, inputfile):
        """ Добавляет новый входящий файл.

        :type inputfile: graph.base.SourceFile
        """
        assert not self.filter_complex, "filter complex already initialized"
        assert isinstance(inputfile, base.SourceFile)
        self.__inputs.append(inputfile)

        for _ in range(inputfile.video_streams):
            i = len(self.__video.streams)
            self.__video < base.Source('%s:v' % i, base.VIDEO)

        for _ in range(inputfile.audio_streams):
            i = len(self.__audio.streams)
            self.__audio < base.Source('%s:a' % i, base.AUDIO)

    def add_output(self, muxer, *codecs):
        assert isinstance(muxer, Muxer)
        for c in codecs:
            assert isinstance(c, BaseCodec)
            fc = self.filter_complex
            if not fc:
                continue
            if c.codec_type == base.VIDEO:
                try:
                    c.connect(
                        fc.get_video_dest(self.__vdest, create=False))
                    self.__vdest += 1
                except IndexError:
                    c.map = '0:v'
            if c.codec_type == base.AUDIO:
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
