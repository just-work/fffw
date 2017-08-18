# coding: utf-8

# $Id: $
from fffw.wrapper import BaseWrapper


__all__ = [
    'Muxer'
]


class Muxer(BaseWrapper):
    arguments = [
        ('format', '-f '),
    ]

    # noinspection PyShadowingBuiltins
    def __init__(self, format, output, **kw):
        self.output = output
        super(Muxer, self).__init__(format=format, **kw)

    def __repr__(self):
        return "<%s>(%s)" % (
            self.output,
            ','.join('%s=%s' % (k, self._args[k]) for k in self._key_mapping
                     if self._args[k])
        )


class HLSMuxer(Muxer):
    arguments = Muxer.arguments + [
        ('method', '-method '),
        ('segment_size', '-hls_time '),
        ('manifest_size', '-hls_list_size '),
        ('segment_list_flags', '-segment_list_flags '),
    ]
