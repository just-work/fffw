# coding: utf-8

# $Id: $
from fffw.graph.base import Node, VIDEO, AUDIO


__all__ = [
    'Deint',
    'Scale',
    'Crop',
    'Split',
    'AudioSplit',
    'Overlay'
]


class Deint(Node):
    kind = VIDEO
    name = 'yadif'


class Scale(Node):
    kind = VIDEO
    name = "scale"

    def __init__(self, width, height, enabled=True):
        super(Scale, self).__init__(enabled=enabled)
        self.width = int(width)
        self.height = int(height)

    @property
    def args(self):
        return "=%sx%s" % (self.width, self.height)


class Crop(Node):
    kind = VIDEO
    name = "crop"

    def __init__(self, width, height, left, top, enabled=True):
        super(Crop, self).__init__(enabled=enabled)
        self.width = width
        self.height = height
        self.left = left
        self.top = top

    @property
    def args(self):
        return "=%s:%s:%s:%s" % (self.width, self.height, self.left, self.top)


class Split(Node):
    kind = VIDEO
    name = "split"

    def __init__(self, output_count=2):
        enabled = output_count > 1
        self._output_count = output_count
        super(Split, self).__init__(enabled=enabled)

    @property
    def output_count(self):
        return self._output_count

    @property
    def args(self):
        if self._output_count == 2:
            return ''
        return '=%s' % self._output_count


class AudioSplit(Node):
    kind = AUDIO
    name = "asplit"

    def __init__(self, output_count=2):
        enabled = output_count > 1
        self._output_count = output_count
        super(AudioSplit, self).__init__(enabled=enabled)

    @property
    def output_count(self):
        return self._output_count

    @property
    def args(self):
        if self._output_count == 2:
            return ''
        return '=%s' % self._output_count


class Overlay(Node):
    kind = VIDEO
    input_count = 2
    name = "overlay"

    def __init__(self, left, top, enabled=True):
        super(Overlay, self).__init__(enabled=enabled)
        self.left = int(left)
        self.top = int(top)

    @property
    def args(self):
        return "=x=%s:y=%s" % (self.left, self.top)
