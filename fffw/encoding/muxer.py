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

    def __init__(self, format, output, **kw):
        self.output = output
        super(Muxer, self).__init__(format=format, **kw)

    def __repr__(self):
        return "<%s>(%s)" % (
            self.output,
            ','.join('%s=%s' % (k, self._args[k]) for k in self._key_mapping
                     if self._args[k])
        )


