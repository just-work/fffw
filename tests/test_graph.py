from dataclasses import dataclass, replace
from typing import cast
from unittest import TestCase

from fffw.encoding import inputs, outputs, codecs
from fffw.encoding.complex import FilterComplex
from fffw.encoding.filters import *
from fffw.graph import *
from fffw.wrapper import param


@dataclass
class Deint(VideoFilter):
    filter = 'yadif'
    mode: str = '0'

    @property
    def args(self) -> str:
        return "%s" % self.mode


@dataclass
class ScaleCuda(Scale):
    filter = 'scale_cuda'
    hardware = 'cuda'


@dataclass
class FdkAAC(codecs.AudioCodec):
    codec = 'libfdk_aac'
    bitrate: int = param(name='b', stream_suffix=True)

    def transform(self, metadata: Meta) -> Meta:
        return replace(metadata, bitrate=self.bitrate)


class FilterGraphTestCase(TestCase):

    def setUp(self) -> None:
        super().setUp()
        self.video_metadata = video_meta_data(
            width=1920,
            height=1080,
            dar=1.777777778,
            par=1.0,
            duration=300.0,
            frame_rate=10.0,
            frame_count=3000
        )
        self.source_audio_duration = 200.0
        self.source_sampling_rate = 48000
        self.source_samples_count = (self.source_audio_duration *
                                     self.source_sampling_rate)
        self.source_audio_bitrate = 128000
        self.audio_metadata = audio_meta_data(
            duration=self.source_audio_duration,
            sampling_rate=self.source_sampling_rate,
            samples_count=self.source_samples_count,
            bit_rate=self.source_audio_bitrate,
        )
        self.target_audio_bitrate = 64000

        self.source = inputs.Input(
            input_file='input.mp4',
            streams=(inputs.Stream(VIDEO, meta=self.video_metadata),
                     inputs.Stream(AUDIO, meta=self.audio_metadata)))
        self.output = outputs.output_file(
            'output.mp4',
            codecs.VideoCodec('libx264'),
            FdkAAC(bitrate=self.target_audio_bitrate))
        self.input_list = inputs.InputList((self.source,))
        self.output_list = outputs.OutputList((self.output,))
        self.fc = FilterComplex(self.input_list, self.output_list)

    def test_ensure_video(self):
        """ Test video stream type assertion helper."""
        with self.assertRaises(TypeError):
            ensure_video(self.audio_metadata)
        self.assertIs(ensure_video(self.video_metadata), self.video_metadata)

    def test_ensure_audio(self):
        """ Test audio stream type assertion helper."""
        with self.assertRaises(TypeError):
            ensure_audio(self.video_metadata)
        self.assertIs(ensure_audio(self.audio_metadata), self.audio_metadata)

    def test_filter_graph(self):
        """ Filter complex smoke test and features demo.

        [I-1/Logo]---<Scale>-------
                                  |
        [I-0/input]--<Deint>--<Overlay>--<Split>--<Scale>--[O/480p]
                                            |
                                            ------<Scale>--[O/720p]
        """
        vs = inputs.Stream(VIDEO)
        logo = inputs.input_file('logo.png', vs)
        self.input_list.append(logo)
        out1 = outputs.output_file('out1.mp4')
        self.output_list.append(out1)

        deint = Deint()
        deint.enabled = False  # deinterlace is skipped

        # first video stream is deinterlaced
        next_node = self.source | deint

        left, top = 20, 20  # logo position

        # first overlay input is deinterlaced source (or source itself as
        # deint filter is disabled)
        over = next_node | Overlay(left, top)

        logo_width, logo_height = 200, 50  # logo scaled

        # second input stream is connected to logo scaler, followed by overlay
        # filter
        next_node = vs | Scale(logo_width, logo_height) | over

        # audio is split to two streams
        asplit = self.source | Split(AUDIO)

        for out in self.output_list:
            asplit > out

        # video split to two steams

        # connect split filter to overlayed video stream
        split = next_node | Split(VIDEO)

        # intermediate video stream scaling
        sizes = [(640, 480), (1280, 720)]

        for out, size in zip(self.output_list, sizes):
            # add scale filters to video streams
            w, h = size
            scale = Scale(w, h)
            # connect scaled streams to video destinations
            split | scale > out

        result = self.fc.render()

        expected = ';'.join([
            # overlay logo
            '[0:v][v:scale0]overlay=x=20:y=20[v:overlay0]',
            # split video to two streams
            '[v:overlay0]split[v:split0][v:split1]',
            # each video is scaled to own size
            '[v:split0]scale=w=640:h=480[vout0]',
            '[v:split1]scale=w=1280:h=720[vout1]',

            # split audio to two streams
            '[0:a]asplit[aout0][aout1]',

            # logo scaling
            '[1:v]scale=w=200:h=50[v:scale0]',
        ])

        self.assertEqual(expected.replace(';', ';\n'),
                         result.replace(';', ';\n'))

    def test_disabled_filters(self):
        """ Filter skipping."""

        # noinspection PyShadowingNames
        def fc_factory():
            src = inputs.input_file("input.mp4", inputs.Stream(VIDEO))
            dst = outputs.output_file('output.mp4')
            fc = FilterComplex(inputs.InputList((src,)),
                               outputs.OutputList((dst,)))
            return fc, src, dst

        def deint_factory():
            d = Deint()
            d.enabled = False
            return d

        with self.subTest("last filter disabled"):
            fc, src, dst = fc_factory()

            src | Scale(640, 360) | deint_factory() > dst.video
            self.assertEqual('[0:v]scale=w=640:h=360[vout0]', fc.render())

        with self.subTest("intermediate filter disabled"):
            fc, src, dst = fc_factory()

            src | deint_factory() | Scale(640, 360) > dst.video
            self.assertEqual('[0:v]scale=w=640:h=360[vout0]', fc.render())

        with self.subTest("all filters disabled"):
            fc, src, dst = fc_factory()

            tmp = src | deint_factory()
            tmp = tmp | deint_factory()
            tmp | Scale(640, 360) > dst.video
            self.assertEqual('[0:v]scale=w=640:h=360[vout0]', fc.render())

        with self.subTest("two filters disabled"):
            fc, src, dst = fc_factory()

            tmp = src | Scale(640, 360)
            tmp = tmp | deint_factory()
            tmp | deint_factory() > dst.video
            self.assertEqual('[0:v]scale=w=640:h=360[vout0]', fc.render())

    def test_skip_not_connected_sources(self):
        """ Skip unused sources in filter complex.
        """
        # passing only video to FilterComplex
        self.source | Scale(640, 360) > self.output

        self.assertEqual('[0:v]scale=w=640:h=360[vout0]', self.fc.render())

    def test_scale_changes_metadata(self):
        """
        Scaled stream has changed width and height.

        Reproduce test IRL:

        $ mediainfo -full source.mp4 |egrep -i '(width|height|aspect)'
        Width                                    : 1920
        Height                                   : 1080
        Pixel aspect ratio                       : 1.000
        Display aspect ratio                     : 1.778

        $ ffmpeg -y -i source.mp4 -t 1 -s 640x480 test.mp4

        $ mediainfo -full test.mp4 |egrep -i '(width|height|aspect)'
        Width                                    : 640
        Height                                   : 480
        Pixel aspect ratio                       : 1.333
        Display aspect ratio                     : 1.778
        """
        self.fc.get_free_source(VIDEO) | Scale(640, 480) > self.output

        vm = cast(VideoMeta, self.output.codecs[0].get_meta_data())
        self.assertEqual(vm.width, 640)
        self.assertEqual(vm.height, 480)
        self.assertAlmostEqual(vm.dar, 1.7778, places=4)
        self.assertAlmostEqual(vm.par, 1.3333, places=4)

    def test_overlay_metadata(self):
        """
        overlay takes bottom stream metadata

        $ ffmpeg -y -i source.mp4 -i logo.mp4 -t 1 \
         -filter_complex '[0:v][1:v]overlay=x=100:y=100' test.mp4
        """
        vs = inputs.Stream(VIDEO, meta=video_meta_data(width=100, height=100))
        self.input_list.append(inputs.input_file('logo.png', vs))
        overlay = self.source | Overlay(
            x=self.video_metadata.width - 2,
            y=self.video_metadata.height - 2)
        vs | overlay
        overlay > self.output

        expected = '[0:v][1:v]overlay=x=1918:y=1078[vout0]'
        self.assertEqual(expected, self.fc.render())
        vm = cast(VideoMeta, self.output.codecs[0].get_meta_data())
        self.assertEqual(vm.width, self.video_metadata.width)
        self.assertEqual(vm.height, self.video_metadata.height)

    def test_concat_video_metadata(self):
        """
        Concat filter sums stream duration

        $ ffmpeg -y -i first.mp4 -i second.mp4 -filter_complex concat test.mp4
        """
        video_meta = video_meta_data(duration=1000.0,
                                     frame_count=10000,
                                     frame_rate=10.0)
        vs = inputs.Stream(VIDEO, meta=video_meta)
        self.input_list.append(inputs.input_file('second.mp4', vs))
        concat = vs | Concat(VIDEO)
        self.source | concat

        concat > self.output

        vm = cast(VideoMeta, self.output.codecs[0].get_meta_data())
        self.assertEqual(self.video_metadata.duration + vs.meta.duration,
                         vm.duration)
        self.assertEqual(self.video_metadata.frames + video_meta.frames,
                         vm.frames)

    def test_concat_audio_metadata(self):
        """
        Concat filter sums samples count for audio streams.
        """
        audio_meta = audio_meta_data(duration=1000.0,
                                     sampling_rate=24000,
                                     samples_count=24000 * 1000)
        a = inputs.Stream(AUDIO, meta=audio_meta)
        self.input_list.append(inputs.input_file('second.mp4', a))
        concat = a | Concat(AUDIO)
        self.source | concat

        concat > self.output

        am = cast(AudioMeta, self.output.codecs[-1].get_meta_data())
        self.assertEqual(self.audio_metadata.duration + audio_meta.duration,
                         am.duration)
        self.assertEqual(round(am.duration * audio_meta.sampling_rate),
                         am.samples)

    def test_video_trim_metadata(self):
        """
        Trim filter sets start and changes stream duration.
        $ ffmpeg -y -i source.mp4 -vf trim=start=3:end=4 -an test.mp4

        Note that resulting video has 3 seconds of frozen frame at 00:00:03.000,
        total duration is 4.
        """
        self.source | Trim(VIDEO, start=3.0, end=4.0) > self.output
        vm = cast(VideoMeta, self.output.codecs[0].get_meta_data())
        self.assertEqual(vm.start, TS(3.0))
        self.assertEqual(vm.duration, TS(4.0))
        self.assertEqual(vm.frames, 1.0 * vm.frame_rate)

    def test_audio_trim_metadata(self):
        """
        Trim filter sets start and changes stream duration.
        $ ffmpeg -y -i source.mp4 -af atrim=start=3:end=4 -vn test.mp4

        Note that resulting video has 3 seconds of frozen frame at 00:00:03.000,
        total duration is 4.
        """
        self.source | Trim(AUDIO, start=3.0, end=4.0) > self.output
        am = cast(AudioMeta, self.output.codecs[1].get_meta_data())
        self.assertEqual(am.start, TS(3.0))
        self.assertEqual(am.duration, TS(4.0))
        self.assertEqual(am.samples, 1.0 * am.sampling_rate)

    def test_setpts_metadata(self):
        """
        SetPTS resets PTS and modifies trimmed streams duration.

        $ ffmpeg -y -i source.mp4 \
        -vf trim=start=3:end=4,setpts=PTS-STARTPTS -an test.mp4
        """
        trim = self.source | Trim(VIDEO, start=3.0, end=4.0)
        trim | SetPTS(VIDEO) > self.output
        vm = cast(VideoMeta, self.output.codecs[0].get_meta_data())
        self.assertEqual(vm.start, TS(0))
        self.assertEqual(vm.duration, TS(1.0))

    def test_filter_validates_stream_kind(self):
        """
        Stream kind is validated for filter.
        """
        self.source.video | Trim(VIDEO, start=3.0, end=4.0)
        with self.assertRaises(ValueError):
            self.source.audio | Trim(VIDEO, start=3.0, end=4.0)

    def test_filter_validates_hardware_device(self):
        """
        When using hardware-accelerated filter, it accepts only streams uploaded
        to a corresponding hardware.
        """
        with self.assertRaises(ValueError):
            self.source.video | ScaleCuda(640, 360)

        cuda = meta.Device(hardware='cuda', name='foo')
        self.source.video | Upload(device=cuda) | ScaleCuda(640, 360)

    def test_any_hardware_filter(self):
        """
        A filter may be defined that allows to be ran on any hardware
        """

        @dataclass
        class UniversalFilter(VideoFilter):
            filter = 'filter'
            # not setting hardware - universal filter

        try:
            cuda = meta.Device(hardware='cuda', name='foo')
            s = self.source.video | Split(VIDEO)
            s | UniversalFilter()
            s | Upload(device=cuda) | UniversalFilter()
        except ValueError:  # pragma: no cover
            self.fail("hardware validation unexpectedly failed")

    def test_codec_metadata_transform(self):
        """
        Codecs parameters applied to stream metadata when using transform.
        """
        with self.subTest('codec with transform'):
            self.source.audio > self.output
            am = cast(AudioMeta, self.output.codecs[1].meta)
            self.assertEqual(am.bitrate, self.target_audio_bitrate)

        with self.subTest('no input metadata'):
            no_meta_input = inputs.input_file('input.mp4')
            output = outputs.output_file('output.mp4',
                                         codecs.AudioCodec('aac'))
            no_meta_input.audio > output.audio
            self.assertIsNone(output.codecs[0].meta)

        with self.subTest('no transform'):
            output = outputs.output_file('output.mp4',
                                         codecs.AudioCodec('aac'))
            self.source.audio > output.audio
            am = cast(AudioMeta, output.codecs[0].meta)
            self.assertEqual(am.bitrate, self.audio_metadata.bitrate)
