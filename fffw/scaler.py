from math import floor, ceil


def xround(val, div, how=None, quality=5):
    """ Number rounding with steroids.

    :param val: float, a number to round
    :param div: int, accuracy. Resulting value will be dividable to this.
    :param how: (None|'ceil'|'floor'), round mode
        None - classic rounding, up or down
        ceil - round up
        floor - round down
    :param quality:
        number of digits after comma used to truncate numbers like
        503.9999999999999994 before main rounding.
    """
    val = round(val, quality)
    if how == 'floor':
        return int(floor(val / float(div))) * div
    if how == 'ceil':
        return int(ceil(val / float(div))) * div
    return (int(val + div / 2.0) // div) * div


class Scaler:
    """ Image and video dimensions transformation helpers."""

    def __init__(self, source_size, par=1.0, rotation=0, accuracy=2):
        self.rotation = rotation in (90, 270)
        w, h = source_size
        self.source_size = (h, w) if self.rotation else (w, h)
        self.accuracy = accuracy
        self.par = par

    def _clone(self):
        return Scaler(self.source_size, par=self.par, rotation=self.rotation,
                      accuracy=self.accuracy)

    def crop(self, left, top, width, height):
        """ Returns new scaler with cut dimensions.
        """
        s = self._clone()
        width = min(self.source_size[0] - left, width)
        height = min(self.source_size[1] - top, height)
        s.source_size = (width, height)
        return s

    def rotate(self, rotation=90):
        """ Retuns new scaler with 90-degree rotation."""
        s = self._clone()
        if rotation in (0, 180):
            # width and height are swapped or not
            return s
        height, width = self.source_size
        s.source_size = (width, height)
        s.rotation = not s.rotation
        return s

    @property
    def pixel_size(self):
        """ Source image size in square pixels."""
        sw, sh = self.source_size
        sw = int(sw * self.par)
        return sw, sh

    @property
    def aspect(self):
        width, height = self.source_size
        if height:
            return round(float(width) / float(height), 3)
        return 0.0

    def scale_fit(self, target_size):
        """
        Scales source image fitting it to
        target_size.

        One or both of resulting dimensions is equal to corresponding target
        dimension, another is less.
        """

        sw, sh = self.pixel_size
        tw, th = target_size
        qsize = sw + sh
        if not qsize:
            raise ValueError("Source size is 0x0")
        scale = min(float(tw) / sw, float(th) / sh)

        return self.scale(scale)

    def scale_crop(self, target_size):
        """ Scales source image to target_size with cutting borders.

        One of resulting dimensions is equal to corresponding target dimension,
        another was greated initially, but was cut to target dimension.
        """

        sw, sh = self.pixel_size
        tw, th = target_size
        qsize = sw + sh
        if not qsize:
            raise ValueError("Source size is 0x0")
        scale = max(float(tw) / sw, float(th) / sh)

        s = self.scale(scale)

        # source image part size, cut to target size
        cw, ch = int(tw / scale), int(th / scale)
        left = max(sw - cw, 0) / 2
        top = max(sh - ch, 0) / 2
        return s, (left, top, cw, ch)

    def scale(self, scale):
        """
        Scales source image with a scale.

        scaled dimension is source dimension multiplied by scale.
        """
        sw, sh = self.pixel_size

        # Usually for horizontal video we round width "up" and height "down".
        # For valid sources it eliminates thin black margins on top/down, for
        # horizontal sources it is not so important.
        (width, height) = (xround(sw * scale, self.accuracy, how='ceil'),
                           xround(sh * scale, self.accuracy, how='floor'))
        s = self._clone()
        s.source_size = (width, height)
        s.par = 1.0
        return s
