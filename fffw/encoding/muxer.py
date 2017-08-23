# coding: utf-8

# $Id: $
from fffw.wrapper import BaseWrapper


__all__ = [
    'Muxer'
]


class Muxer(BaseWrapper):
    format = None

    # noinspection PyShadowingBuiltins
    def __init__(self, output, **kw):
        self.output = output
        super(Muxer, self).__init__(**kw)

    def __repr__(self):
        return "<%s>(%s)" % (
            self.output,
            self.get_opts()
        )

    def get_args(self):
        return ['-f', self.format] + super(Muxer, self).get_args()

    def get_opts(self):
        """ Возвращает настройки муксера в виде опций через двоеточие"""
        return ':'.join('%s=%s' % (self.key_to_opt(k), self._args[k])
                        for k in self._args_order if self._args[k])

    def key_to_opt(self, k):
        return self._key_mapping[k].strip('- ')


class HLSMuxer(Muxer):
    format = 'hls'

    arguments = [
        ('method', '-method '),
        ('segment_size', '-hls_time '),
        ('manifest_size', '-hls_list_size '),
    ]


class TeeMuxer(Muxer):
    format = 'tee'

    def __init__(self, *muxers):
        self.muxers = []
        super(TeeMuxer, self).__init__(muxers)

    @property
    def output(self):
        return '|'.join(['[f={format}{opts}]{output}'.format(
            format=m.format, opts=self._format_opts(m.get_opts()),
            output=m.output) for m in self.muxers])

    @output.setter
    def output(self, muxers):
        for m in muxers:
            assert isinstance(m, Muxer)
        self.muxers = muxers

    def get_args(self):
        return super(TeeMuxer, self).get_args()

    @staticmethod
    def _format_opts(opts):
        return (':' + opts) if opts else ''
