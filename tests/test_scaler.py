from unittest import TestCase
from fffw.scaler import Scaler


class ScalerTestCase(TestCase):
    """ Tests for scaling helpers class."""

    def test_scaler(self):
        """ Scaler smoke test and feature demo

        * Source video 1280x960, square pixels
        * Scaled to 640x480 then cropped on top/bottom to 640x360
        * Scaled to 480x360 to fit to  640x360
        """
        scaler = Scaler((1280, 960), accuracy=1)
        fit = scaler.scale_fit((640, 360))
        crop, fields = scaler.scale_crop((640, 360))

        self.assertTupleEqual(fit.source_size, (480, 360))
        self.assertTupleEqual(crop.source_size, (640, 480))
        self.assertTupleEqual(fields, (0, 120, 1280, 720))

    def test_accuracy(self):
        """ Resulting dimensions are dividable to 16."""
        scaler = Scaler((1280, 720), accuracy=16)
        fit = scaler.scale_fit((640, 360))
        self.assertTupleEqual(fit.source_size, (640, 352))

    def test_rotation(self):
        """ Rotation handling."""
        scaler = Scaler((1280, 720), rotation=90)
        fit = scaler.scale_fit((360, 640))
        self.assertTupleEqual(fit.source_size, (360, 640))

    def test_pixel_aspect_ratip(self):
        """ Non-square pixels support."""
        scaler = Scaler((720, 720), par=16./9.)
        fit = scaler.scale_fit((640, 360))
        self.assertTupleEqual(fit.source_size, (640, 360))
