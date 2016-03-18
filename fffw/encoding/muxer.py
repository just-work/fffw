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


