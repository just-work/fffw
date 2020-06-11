from dataclasses import dataclass
from typing import cast, Tuple
from unittest import TestCase

from fffw.encoding import *
from fffw.encoding.vector import SIMD, Vector
from fffw.graph import *
from fffw.wrapper import ensure_binary, param
from fffw.wrapper.helpers import ensure_text
from tests.test_ffmpeg import Volume


@dataclass
class StubFilter(AudioFilter):
    filter = 'stub'
    p: int = param()


@dataclass
class SomeFilter(VideoFilter):
    filter = 'some'


@dataclass
class AnotherFilter(VideoFilter):
    filter = 'another'


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

    def assert_simd_args(self, *arguments: str):
        expected = list(arguments)
        args = ensure_text(self.simd.ffmpeg.get_args())
        try:
            idx = expected.index('-filter_complex')
            expected_fc = expected[idx + 1].split(';')
            expected[idx: idx + 2] = []
        except ValueError:
            expected_fc = []
        try:
            idx = args.index('-filter_complex')
            real_fc = args[idx + 1].split(';')
            args[idx:idx + 2] = []
        except ValueError:
            real_fc = []
        self.assertSetEqual(set(expected_fc), set(real_fc))
        self.assertListEqual(expected, args)

    def test_no_filter_graph(self):
        """ Checks that vector works correctly without filter graph."""
        self.assert_simd_args(
            'ffmpeg',
            '-i', 'input.mp4',
            '-map', '0:v', '-c:v', 'libx264',
            '-map', '0:a', '-c:a', 'aac',
            'output1.mp4',
            '-map', '0:v', '-c:v', 'libx265',
            '-map', '0:a', '-c:a', 'libfdk_aac',
            'output2.mp5')

    def test_same_filter_for_all_streams(self):
        """ Single filter can be applied to each stream in vector."""
        cursor = self.simd | Volume(30)
        cursor > self.simd
        self.assert_simd_args(
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
            'output2.mp5')

    def test_same_filter_with_mask(self):
        """ Applying filter works with mask."""
        cursor = self.simd.audio.connect(Volume(30), mask=[False, True])
        cursor > self.simd
        self.assert_simd_args(
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
            'output2.mp5')

    def test_multiple_disabled_filters(self):
        cursor = self.simd.audio.connect(Volume(30), mask=[False, False])
        cursor > self.simd
        self.assert_simd_args(
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
            'output2.mp5')

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
        self.assert_simd_args(
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
            'output2.mp5')

    def test_split_filter_if_vector_differs(self):
        """
        If source vector has different streams, next filter must be cloned.
        """
        cursor = self.simd.audio.connect(Volume, params=[20, 30])
        cursor = cursor | StubFilter(p=0)
        cursor > self.simd
        self.assert_simd_args(
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
            'output2.mp5')

    def test_clone_inputs_for_destination_filter(self):
        """
        If source vector has different streams, next filter must be cloned with
        all connected inputs.
        """
        v = self.simd.video | Vector((SomeFilter(), AnotherFilter()))
        some, other = cast(Tuple[VideoFilter, VideoFilter], v)
        v1 = Vector(some).connect(Scale, params=[(1280, 720), (640, 360)])

        overlay = other | Overlay(0, 0)

        v2 = v1.connect(overlay)

        v2 > self.simd
        self.assert_simd_args(
            'ffmpeg',
            '-i', 'input.mp4',
            '-filter_complex',
            '[0:v]split[v:split0][v:split1];'
            '[v:split0]some[v:some0];'
            '[v:split1]another[v:another0];'
            '[v:some0]split[v:split2][v:split3];'
            '[v:split2]scale=w=1280:h=720[v:scale0];'
            '[v:split3]scale=w=640:h=360[v:scale1];'
            '[v:another0]split[v:split4][v:split5];'
            '[v:split4][v:scale0]overlay[vout0];'
            '[v:split5][v:scale1]overlay[vout1]',
            '-map', '[vout0]', '-c:v', 'libx264',
            '-map', '0:a', '-c:a', 'aac',
            'output1.mp4',
            '-map', '[vout1]', '-c:v', 'libx265',
            '-map', '0:a', '-c:a', 'libfdk_aac',
            'output2.mp5')

    def test_clone_streams(self):
        """
        If necessary, streams may be also split.
        """
        logo = input_file('logo.png', Stream(VIDEO, video_meta_data()))
        self.simd < logo
        overlay = logo.streams[0] | Overlay(0, 0)

        v = self.simd.video.connect(Scale, params=[(1280, 720), (640, 360)])
        v.connect(overlay) > self.simd

        self.assert_simd_args(
            'ffmpeg',
            '-i', 'input.mp4',
            '-i', 'logo.png',
            '-filter_complex',
            '[0:v]split[v:split0][v:split1];'
            '[1:v]split[v:split2][v:split3];'
            '[v:split0]scale=w=1280:h=720[v:scale0];'
            '[v:split1]scale=w=640:h=360[v:scale1];'
            '[v:split2][v:scale0]overlay[vout0];'
            '[v:split3][v:scale1]overlay[vout1]',
            '-map', '[vout0]', '-c:v', 'libx264',
            '-map', '0:a', '-c:a', 'aac',
            'output1.mp4',
            '-map', '[vout1]', '-c:v', 'libx265',
            '-map', '0:a', '-c:a', 'libfdk_aac',
            'output2.mp5'
        )

    def test_overlay_with_mask(self):
        """
        Overlay may be applied conditionally.
        """
        logo = input_file('logo.png', Stream(VIDEO, video_meta_data()))
        self.simd < logo
        overlay = logo.streams[0] | Overlay(0, 0)

        self.simd.video.connect(overlay, mask=[True, False]) > self.simd

        self.assert_simd_args(
            'ffmpeg',
            '-i', 'input.mp4',
            '-i', 'logo.png',
            '-filter_complex',
            '[0:v]split[v:split0][vout0];'
            '[1:v][v:split0]overlay[vout1]',
            '-map', '[vout1]', '-c:v', 'libx264',
            '-map', '0:a', '-c:a', 'aac',
            'output1.mp4',
            '-map', '[vout0]', '-c:v', 'libx265',
            '-map', '0:a', '-c:a', 'libfdk_aac',
            'output2.mp5'
        )

    def test_preroll_with_mask(self):
        """
        Concat filter may be applied conditionally.
        """
        vstream = Stream(VIDEO, video_meta_data())
        astream = Stream(AUDIO, audio_meta_data())
        preroll = input_file('preroll.mp4', vstream, astream)
        self.simd < preroll

        vconcat = vstream | Concat(VIDEO, input_count=2)
        aconcat = astream | Concat(AUDIO, input_count=2)

        self.simd.video.connect(vconcat, mask=[True, False]) > self.simd
        self.simd.audio.connect(aconcat, mask=[True, False]) > self.simd

        self.assert_simd_args(
            'ffmpeg',
            '-i', 'input.mp4',
            '-i', 'preroll.mp4',
            '-filter_complex',
            '[0:v]split[v:split0][vout0];'
            '[0:a]asplit[a:asplit0][aout0];'
            '[1:v][v:split0]concat[vout1];'
            '[1:a][a:asplit0]concat=v=0:a=1:n=2[aout1]',
            '-map', '[vout1]', '-c:v', 'libx264',
            '-map', '[aout1]', '-c:a', 'aac',
            'output1.mp4',
            '-map', '[vout0]', '-c:v', 'libx265',
            '-map', '[aout0]', '-c:a', 'libfdk_aac',
            'output2.mp5')
