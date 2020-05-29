from fffw.graph import base
from fffw.graph.base import VIDEO

__all__ = [
    'Scale',
    'Split',
    'Concat',
    'Overlay',
]


class Scale(base.Node):
    kind = VIDEO
    filter = "scale"

    def __init__(self, width: int, height: int, enabled: bool = True):
        super(Scale, self).__init__(enabled=enabled)
        self.width = int(width)
        self.height = int(height)

    @property
    def args(self) -> str:
        return "%sx%s" % (self.width, self.height)


class Split(base.Node):

    def __init__(self, kind: base.StreamType = VIDEO, output_count: int = 2):
        enabled = output_count > 1
        self.output_count = output_count
        self.kind = kind
        self.filter = 'split' if kind == VIDEO else 'asplit'
        super(Split, self).__init__(enabled=enabled)

    @property
    def args(self) -> str:
        if self.output_count == 2:
            return ''
        return '%s' % self.output_count


class Concat(base.Node):
    filter = 'concat'

    def __init__(self, kind: base.StreamType = VIDEO, input_count: int = 2):
        enabled = input_count > 1
        self.input_count = input_count
        self.kind = kind
        super(Concat, self).__init__(enabled=enabled)

    @property
    def args(self) -> str:
        if self.kind == VIDEO:
            if self.input_count == 2:
                return ''
            return 'n=%s' % self.input_count
        return 'v=0:a=1:n=%s' % self.input_count


class Overlay(base.Node):
    kind = VIDEO
    input_count = 2
    filter = "overlay"

    def __init__(self, left: int, top: int, enabled: bool = True):
        super(Overlay, self).__init__(enabled=enabled)
        self.left = int(left)
        self.top = int(top)

    @property
    def args(self) -> str:
        return "x=%s:y=%s" % (self.left, self.top)


