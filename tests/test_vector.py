from dataclasses import dataclass
from unittest import TestCase

from fffw.encoding import *
from fffw.encoding.vector import SIMD
from fffw.graph import *
from fffw.wrapper import ensure_binary, param
from tests.test_ffmpeg import Volume


@dataclass
class StubFilter(AudioFilter):
    filter = 'stub'
    p: int = param()


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
        self.simd = SIMD(self.source, self.output1, self.output2)

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
        self.assertEqual(expected, self.simd.ffmpeg.get_args())

    def test_same_filter_for_all_streams(self):
        """ Single filter can be applied to each stream in vector."""
        cursor = self.simd | Volume(30)
        cursor > self.simd
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
        self.assertEqual(expected, self.simd.ffmpeg.get_args())

    def test_same_filter_with_mask(self):
        """ Applying filter works with mask."""
        cursor = self.simd.audio.connect(Volume(30), mask=[False, True])
        cursor > self.simd
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
        self.assertEqual(expected, self.simd.ffmpeg.get_args())

    def test_multiple_disabled_filters(self):
        cursor = self.simd.audio.connect(Volume(30), mask=[False, False])
        cursor > self.simd
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
        self.assertEqual(expected, self.simd.ffmpeg.get_args())

    def test_apply_filter_with_params_vector(self):
        cursor = self.simd.audio.connect(Volume, params=[20, 30])
        cursor > self.simd
        expected = ensure_binary([
            'ffmpeg',
            '-i',
            'input.mp4',
            '-filter_complex',
            '[0:a]asplit[a:asplit0][a:asplit1];'
            '[a:asplit0]volume=20.00[aout0];'
            '[a:asplit1]volume=30.00[aout1]',
            '-map', '0:v', '-c:v', 'libx264',
            '-map', '[aout0]', '-c:a', 'aac',
            'output1.mp4',
            '-map', '0:v', '-c:v', 'libx265',
            '-map', '[aout1]', '-c:a', 'libfdk_aac',
            'output2.mp5'])
        self.assertEqual(expected, self.simd.ffmpeg.get_args())

    def test_apply_filter_with_equal_params(self):
        cursor = self.simd.audio.connect(Volume, params=[30, 30])
        cursor > self.simd
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
        self.assertEqual(expected, self.simd.ffmpeg.get_args())

    def test_split_filter_if_vector_differs(self):
        """
        If source vector has different streams, next filter must be cloned.
        """
        cursor = self.simd.audio.connect(Volume, params=[20, 30])
        cursor = cursor | StubFilter(p=0)
        cursor > self.simd
        expected = ensure_binary([
            'ffmpeg',
            '-i',
            'input.mp4',
            '-filter_complex',
            '[0:a]asplit[a:asplit0][a:asplit1];'
            '[a:asplit0]volume=20.00[a:volume0];'
            '[a:volume0]stub[aout0];'
            '[a:asplit1]volume=30.00[a:volume1];'
            '[a:volume1]stub[aout1]',
            '-map', '0:v', '-c:v', 'libx264',
            '-map', '[aout0]', '-c:a', 'aac',
            'output1.mp4',
            '-map', '0:v', '-c:v', 'libx265',
            '-map', '[aout1]', '-c:a', 'libfdk_aac',
            'output2.mp5'])
        self.assertEqual(expected, self.simd.ffmpeg.get_args())
