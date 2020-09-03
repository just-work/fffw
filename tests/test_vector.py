from dataclasses import dataclass, replace
from typing import cast, Tuple

from fffw.encoding import *
from fffw.encoding.vector import SIMD, Vector
from fffw.graph import *
from fffw.wrapper import param
from tests.base import BaseTestCase
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


# noinspection PyStatementEffect
class VectorTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.video_meta = video_meta_data(width=1920, height=1080)
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
        self.assert_ffmpeg_args(*arguments)

    @property
    def ffmpeg(self):
        return self.simd.ffmpeg

    def test_vector_kind(self):
        """
        Checks that vector does not return kind if it contains audio and video
        streams.
        """
        v = Vector([VideoFilter(), AudioFilter()])
        self.assertRaises(RuntimeError, getattr, v, 'kind')

    def test_vector_metadata(self):
        """
        Checks that vector outputs metadata for a single stream in it.
        """
        v = self.simd.video | Scale(1280, 720)
        expected = replace(self.video_meta, width=1280, height=720)
        self.assertEqual(v.metadata, expected)

    def test_vector_metadata_for_multiple_streams(self):
        """
        Checks that vector does not return metadata if it contains multiple
        streams.
        """
        v = Vector([VideoFilter(), VideoFilter()])
        self.assertRaises(RuntimeError, getattr, v, 'metadata')

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
        self.assert_simd_args(
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
            'output2.mp5')

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
        # noinspection PyTypeChecker
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
        video_stream = Stream(VIDEO, video_meta_data())
        logo = self.simd < input_file('logo.png', video_stream)
        overlay = logo | Overlay(0, 0)

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
        overlay = logo | Overlay(0, 0)

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

    def test_connect_filter_to_a_vector(self):
        """ Plain filter can be connected to a stream vector."""
        logo = input_file('logo.png', Stream(VIDEO, video_meta_data()))
        self.simd < logo
        overlay = self.simd.video | Overlay(0, 0)
        # checking that Vector.__ror__ works
        logo | Scale(120, 120) | overlay > self.simd

        self.assert_simd_args(
            'ffmpeg',
            '-i', 'input.mp4',
            '-i', 'logo.png',
            '-filter_complex',
            '[v:overlay0]split[vout0][vout1];'
            '[1:v]scale=w=120:h=120[v:scale0];'
            '[0:v][v:scale0]overlay[v:overlay0]',
            '-map', '[vout0]', '-c:v', 'libx264',
            '-map', '0:a', '-c:a', 'aac',
            'output1.mp4',
            '-map', '[vout1]', '-c:v', 'libx265',
            '-map', '0:a', '-c:a', 'libfdk_aac',
            'output2.mp5'
        )

    def test_connect_stream_to_simd(self):
        """ Plain input stream can be connected to a SIMD instance."""
        vstream = Stream(VIDEO, video_meta_data())
        astream = Stream(AUDIO, audio_meta_data())
        preroll = self.simd < input_file('preroll.mp4', vstream, astream)

        vconcat = vstream | Concat(VIDEO, input_count=2)
        aconcat = astream | Concat(AUDIO, input_count=2)
        preroll.video | vconcat | Scale(1820, 720) > self.simd
        preroll.audio | aconcat > self.simd

        self.assert_simd_args(
            'ffmpeg',
            '-i',
            'input.mp4',
            '-i',
            'preroll.mp4',
            '-filter_complex',
            '[v:scale0]split[vout0][vout1];'
            '[1:a][1:a]concat=v=0:a=1:n=2[a:concat0];'
            '[a:concat0]asplit[aout0][aout1];'
            '[v:concat0]scale=w=1820:h=720[v:scale0];'
            '[1:v][1:v]concat[v:concat0]',
            '-map', '[vout0]',
            '-c:v', 'libx264',
            '-map', '[aout0]',
            '-c:a', 'aac',
            'output1.mp4',
            '-map', '[vout1]',
            '-c:v', 'libx265',
            '-map', '[aout1]',
            '-c:a', 'libfdk_aac',
            'output2.mp5'
        )
