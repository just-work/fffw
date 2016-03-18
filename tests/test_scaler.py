# coding: utf-8

# $Id: $
from unittest import TestCase
from fffw.scaler import Scaler


class ScalerTestCase(TestCase):

    def testScaler(self):
        """ Тест на работоспособность и пример использования.

        * Исходное видео 1280x960, с квадратными пикселями
        * масштрабируется до 640x480, потом обрезается сверху/снизу до 640x360
        * масштабируется до 480x360, чтобы "втиснуться" в 640x360
        """
        scaler = Scaler((1280, 960), accuracy=1)
        fit = scaler.scale_fit((640, 360))
        crop, fields = scaler.scale_crop((640, 360))

        self.assertTupleEqual(fit.source_size, (480, 360))
        self.assertTupleEqual(crop.source_size, (640, 480))
        self.assertTupleEqual(fields, (0, 120, 1280, 720))

    def testAccuracy(self):
        """ Вычисление размеров результата с округлением до блоков
        по 16 пикселей."""
        scaler = Scaler((1280, 720), accuracy=16)
        fit = scaler.scale_fit((640, 360))
        self.assertTupleEqual(fit.source_size, (640, 352))

    def testRotation(self):
        """ Учет поворота исходного изображения."""
        scaler = Scaler((1280, 720), rotation=90)
        fit = scaler.scale_fit((360, 640))
        self.assertTupleEqual(fit.source_size, (360, 640))

    def testPixelAspectRatio(self):
        """ Учет неквадратных пикселей исходного изображения."""
        scaler = Scaler((720, 720), par=16./9.)
        fit = scaler.scale_fit((640, 360))
        self.assertTupleEqual(fit.source_size, (640, 360))







