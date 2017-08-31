# coding: utf-8

# $Id: $
from fffw.graph.base import Node, VIDEO, AUDIO


__all__ = [
    'Pass',
    'AudioPass',
    'Deint',
    'Scale',
    'SetSAR',
    'Crop',
    'Split',
    'Concat',
    'AudioConcat',
    'Trim',
    'AudioTrim',
    'SetPTS',
    'AudioSetPTS',
    'AudioSplit',
    'Overlay',
    'Volume',
    'Rotate',
    'Drawtext',
    'HWUpload',
    'ScaleNPP',
]


class Pass(Node):
    kind = VIDEO
    enabled = False


class AudioPass(Node):
    kind = AUDIO
    enabled = False


class Deint(Node):
    kind = VIDEO
    name = 'yadif'

    def __init__(self, mode='0', enabled=True):
        super(Deint, self).__init__(enabled=enabled)
        self.mode = mode

    @property
    def args(self):
        return "%s" % self.mode


class Scale(Node):
    kind = VIDEO
    name = "scale"

    def __init__(self, width, height, enabled=True):
        super(Scale, self).__init__(enabled=enabled)
        self.width = int(width)
        self.height = int(height)

    @property
    def args(self):
        return "%sx%s" % (self.width, self.height)


class ScaleNPP(Scale):
    name = 'scale_npp'

    @property
    def args(self):
        return "w=%s:h=%s" % (self.width, self.height)


class SetSAR(Node):
    kind = VIDEO
    name = "setsar"

    def __init__(self, sar, enabled=True):
        super(SetSAR, self).__init__(enabled=enabled)
        self.sar = sar

    @property
    def args(self):
        return "%s" % self.sar


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
        return "%s:%s:%s:%s" % (self.width, self.height, self.left, self.top)


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
        return '%s' % self._output_count


class HWUpload(Node):
    kind = VIDEO
    name = 'hwupload_cuda'


class Concat(Node):
    kind = VIDEO
    name = 'concat'

    def __init__(self, input_count=2):
        enabled = input_count > 1
        self.input_count = input_count
        super(Concat, self).__init__(enabled=enabled)

    @property
    def args(self):
        if self.input_count == 2:
            return ''
        return 'n=%s' % self.input_count


class AudioConcat(Node):
    kind = AUDIO
    name = 'concat'

    def __init__(self, input_count=2):
        enabled = input_count > 1
        self.input_count = input_count
        super(AudioConcat, self).__init__(enabled=enabled)

    @property
    def args(self):
        return 'v=0:a=1:n=%s' % self.input_count


class Trim(Node):
    kind = VIDEO
    name = 'trim'

    def __init__(self, start=None, end=None, enabled=True):
        self.start = start
        self.end = end
        super(Trim, self).__init__(enabled=enabled)

    @property
    def args(self):
        return 'start=%s:end=%s' % (self.start, self.end)


class AudioTrim(Node):
    kind = VIDEO
    name = 'atrim'

    def __init__(self, start=None, end=None, enabled=True):
        self.start = start
        self.end = end
        super(AudioTrim, self).__init__(enabled=enabled)

    @property
    def args(self):
        return 'start=%s:end=%s' % (self.start, self.end)


class SetPTS(Node):
    kind = VIDEO
    name = 'setpts'

    def __init__(self, mode='PTS-STARTPTS', enabled=True):
        self.mode = mode
        super(SetPTS, self).__init__(enabled=enabled)

    @property
    def args(self):
        return self.mode


class AudioSetPTS(Node):
    kind = VIDEO
    name = 'asetpts'

    def __init__(self, mode='PTS-STARTPTS', enabled=True):
        self.mode = mode
        super(AudioSetPTS, self).__init__(enabled=enabled)

    @property
    def args(self):
        return self.mode


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
        return '%s' % self._output_count


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
        return "x=%s:y=%s" % (self.left, self.top)


class Volume(Node):
    kind = AUDIO
    name = 'volume'

    def __init__(self, volume, enabled=True):
        super(Volume, self).__init__(enabled=enabled)
        self.volume = volume

    @property
    def args(self):
        return "%.2f" % self.volume


class Rotate(Node):
    kind = VIDEO
    name = "rotate"

    def __init__(self, degrees=None, output_size=None, enabled=True):
        super(Rotate, self).__init__(enabled=enabled)
        self.degrees = degrees
        self.output_size = output_size

    @property
    def args(self):
        if self.degrees is not None:
            result = "%s*PI/180" % self.degrees
            if self.output_size:
                w, h = self.output_size
                result += ':ow=%s:oh=%s' % (w, h)
            return result
        else:
            raise ValueError(self.degrees)


class Drawtext(Node):
    kind = VIDEO
    name = 'drawtext'

    def __init__(self, text, enabled=True,
                 fontfile='font.ttf',
                 x='(w-text_w)/2',
                 y='(h-text_h)/2',
                 **opts):
        super(Drawtext, self).__init__(enabled=enabled)
        self.opts = dict(opts, fontfile=fontfile, text=text, x=x, y=y)

    @property
    def args(self):
        return ':'.join('%s=%s' % t for t in sorted(self.opts.items()))
