# coding: utf-8

# $Id: $
from fffw.wrapper import BaseWrapper


__all__ = [
    'Muxer'
]


class Muxer(BaseWrapper):

    # noinspection PyShadowingBuiltins
    def __init__(self, format, output, **kw):
        self.output = output
        self.format = format
        super(Muxer, self).__init__(format=format, **kw)

    def __repr__(self):
        return "<%s>(%s)" % (
            self.output,
            self.get_opts()
        )

    def get_args(self):
        return ['-f', self.format] + super(Muxer, self).get_args()

    def get_opts(self):
        """ Возвращает настройки муксера в виде опций через двоеточие"""
        return ':'.join('%s=%s' % (self._key_mapping[k].strip('- '), self._args[k]) for k in self._key_mapping
                        if self._args[k])


class HLSMuxer(Muxer):
    arguments = Muxer.arguments + [
        ('method', '-method '),
        ('segment_size', '-hls_time '),
        ('manifest_size', '-hls_list_size '),
    ]


class TeeMuxer(Muxer):
    def __init__(self, *muxers):
        self.muxers = []
        super(TeeMuxer, self).__init__('tee', muxers)

    @property
    def output(self):
        return '|'.join(['[f={format}:{args}]{output}'.format(
            format=m.format, args=m.get_opts(), output=m.output)
            for m in self.muxers])

    @output.setter
    def output(self, muxers):
        for m in muxers:
            assert isinstance(m, Muxer)
        self.muxers = muxers

    def get_args(self):
        return super(TeeMuxer, self).get_args()


