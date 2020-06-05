from unittest import TestCase

from fffw.encoding import *
from fffw.encoding.vector import Vector
from fffw.graph import *
from fffw.wrapper import ensure_binary
from tests.test_ffmpeg import Volume


class VectorTestCase(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.video_meta = video_meta_data()
        self.audio_meta = audio_meta_data()
        self.source = input_file('input.mp4',
                                 Stream(VIDEO, self.video_meta),
                                 Stream(AUDIO, self.audio_meta))
        self.output1 = output_file('output1.mp4',
                                   VideoCodec('libx264'),
                                   AudioCodec('aac'))
        self.output2 = output_file('output2.mp5',
                                   VideoCodec('libx265'),
                                   AudioCodec('libfdk_aac'))
        self.vector = Vector(self.source, self.output1, self.output2)

    def test_no_filter_graph(self):
        """ Checks that vector works correctly without filter graph."""
        expected = ensure_binary([
            'ffmpeg',
            '-i', 'input.mp4',
            '-map', '0:v', '-c:v', 'libx264',
            '-map', '0:a', '-c:a', 'aac',
            'output1.mp4',
            '-map', '0:v', '-c:v', 'libx265',
            '-map', '0:a', '-c:a', 'libfdk_aac',
            'output2.mp5'

        ])
        self.assertEqual(expected, self.vector.ffmpeg.get_args())

    def test_same_filter_for_all_streams(self):
        """ Single filter can be applied to each stream in vector."""
        cursor = self.vector.audio.connect(Volume(30))
        cursor.finalize()
        expected = ensure_binary([
            'ffmpeg',
            '-i',
            'input.mp4',
            '-filter_complex',
            '[0:a]volume=30.00[a:volume0];'
            '[a:volume0]asplit[aout0][aout1]',
            '-map', '0:v', '-c:v', 'libx264',
            '-map', '[aout0]', '-c:a', 'aac',
            'output1.mp4',
            '-map', '0:v', '-c:v', 'libx265',
            '-map', '[aout1]', '-c:a', 'libfdk_aac',
            'output2.mp5'])
        self.assertEqual(expected, self.vector.ffmpeg.get_args())

    def test_same_filter_with_mask(self):
        """ Applying filter works with mask."""
        cursor = self.vector.audio.connect(Volume(30), mask=[False, True])
        cursor.finalize()
        expected = ensure_binary([
            'ffmpeg',
            '-i',
            'input.mp4',
            '-filter_complex',
            '[0:a]asplit[a:asplit0][aout0];'
            '[a:asplit0]volume=30.00[aout1]',
            '-map', '0:v', '-c:v', 'libx264',
            '-map', '[aout0]', '-c:a', 'aac',
            'output1.mp4',
            '-map', '0:v', '-c:v', 'libx265',
            '-map', '[aout1]', '-c:a', 'libfdk_aac',
            'output2.mp5'])
        self.assertEqual(expected, self.vector.ffmpeg.get_args())

    def test_same_filter_with_another_mask(self):
        cursor = self.vector.audio.connect(Volume(30), mask=[True, False])
        cursor.finalize()
        expected = ensure_binary([
            'ffmpeg',
            '-i',
            'input.mp4',
            '-filter_complex',
            '[0:a]asplit[a:asplit0][aout0];'
            '[a:asplit0]volume=30.00[aout1]',
            '-map', '0:v', '-c:v', 'libx264',
            '-map', '[aout1]', '-c:a', 'aac',
            'output1.mp4',
            '-map', '0:v', '-c:v', 'libx265',
            '-map', '[aout0]', '-c:a', 'libfdk_aac',
            'output2.mp5'])
        self.assertEqual(expected, self.vector.ffmpeg.get_args())

    def test_multiple_disabled_filters(self):
        cursor = self.vector.audio.connect(Volume(30), mask=[False, False])
        cursor.finalize()
        expected = ensure_binary([
            'ffmpeg',
            '-i',
            'input.mp4',
            '-filter_complex',
            '[0:a]asplit[aout0][aout1]',
            '-map', '0:v', '-c:v', 'libx264',
            '-map', '[aout0]', '-c:a', 'aac',
            'output1.mp4',
            '-map', '0:v', '-c:v', 'libx265',
            '-map', '[aout1]', '-c:a', 'libfdk_aac',
            'output2.mp5'])
        self.assertEqual(expected, self.vector.ffmpeg.get_args())
