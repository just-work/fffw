# coding: utf-8

from math import floor, ceil


def xround(val, div, how=None, quality=5):
    """ Округление на стероидах.

    :param val: float, число которое округлять
    :param div: int, точность округления
    (результат будет нацело делиться на него)
    :param how: (None|'ceil'|'floor'), режим округления
        None - округление из школы (в обе стороны)
        ceil - округление вверх
        floor - округление вниз
    :param quality:
        число знаков после запятой, до которого происходит округление исходного
        значения в десятичной СИ до основного округления. Используется для
        борьбы с числами 503.9999999999999994
    """
    val = round(val, quality)
    if how == 'floor':
        return int(floor(val / float(div))) * div
    if how == 'ceil':
        return int(ceil(val / float(div))) * div
    return (int(val + div / 2.0) // div) * div


class Scaler(object):
    """ Хелпер для учета трансформаций изображений и видео."""

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
        """ Учитывает фактический результат обрезки с указанными параметрами
        """
        s = self._clone()
        width = min(self.source_size[0] - left, width)
        height = min(self.source_size[1] - top, height)
        s.source_size = (width, height)
        return s

    def rotate(self, rotation=90):
        """ Учитывает поворот на углы, кратные 90 градусам."""
        s = self._clone()
        if rotation in (0, 180):
            # поворот либо меняет местами высоту или ширину, либо не меняет
            return s
        height, width = self.source_size
        s.source_size = (width, height)
        s.rotation = not s.rotation
        return s

    @property
    def pixel_size(self):
        """ Размер исходного изображения в квадратных пикселях."""
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
        """ Масштабирует изображение "вписывая" его в target_size."""

        sw, sh = self.pixel_size
        tw, th = target_size
        qsize = sw + sh
        if not qsize:
            raise ValueError("Source size is 0x0")
        scale = min(float(tw) / sw, float(th) / sh)

        return self.scale(scale)

    def scale_crop(self, target_size):
        """ Масштабирует изображение покрывая целиком target_size."""

        sw, sh = self.pixel_size
        tw, th = target_size
        qsize = sw + sh
        if not qsize:
            raise ValueError("Source size is 0x0")
        scale = max(float(tw) / sw, float(th) / sh)

        s = self.scale(scale)

        # размер части исходного изображения, "влезшей" в результат
        cw, ch = int(tw / scale), int(th / scale)
        left = max(sw - cw, 0) / 2
        top = max(sh - ch, 0) / 2
        return s, (left, top, cw, ch)

    def scale(self, scale):
        """ Масштабирует изображение кратно значению scale."""
        sw, sh = self.pixel_size

        # В ширину мы округляем "вверх", в высоту - "вниз". Для
        # "нормальных" исходников при этом удастся избежать вертикальных
        # черных полей, а для "повернутых" - не важно.
        (width, height) = (xround(sw * scale, self.accuracy, how='ceil'),
                           xround(sh * scale, self.accuracy, how='floor'))
        s = self._clone()
        s.source_size = (width, height)
        s.par = 1.0
        return s
