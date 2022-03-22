from copy import deepcopy
from dataclasses import dataclass, replace
from typing import cast
from unittest import TestCase

from fffw.encoding import inputs, outputs, codecs
from fffw.encoding.complex import FilterComplex
from fffw.encoding.filters import *
from fffw.graph import *
from fffw.graph import base
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

    def transform(self, *metadata: Meta) -> Meta:
        return replace(ensure_audio(*metadata), bitrate=self.bitrate)


class SourceImpl(base.Source):

    @property
    def name(self) -> str:  # pragma: no cover
        return ''


class NodeImpl(base.Node):

    @property
    def args(self) -> str:  # pragma: no cover
        return ''


class DestImpl(base.Dest):
    pass


class GraphBaseTestCase(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.source = SourceImpl(VIDEO)
        self.node = NodeImpl()
        self.another = NodeImpl()
        self.dest = DestImpl()
        self.source_edge = base.Edge(self.source, self.node)
        self.inter_edge = base.Edge(self.node, self.another)
        self.dest_edge = base.Edge(self.another, self.dest)

    def test_node_connect_edge_validation(self):
        """
        Checks edge validation for Node.
        """

        with self.subTest("only edge allowed"):
            with self.assertRaises(TypeError):
                self.node.connect_edge(object())  # type: ignore

        with self.subTest("edge output cross-link"):
            with self.assertRaises(ValueError):
                self.node.connect_edge(self.dest_edge)

        with self.subTest("success"):
            self.node.connect_edge(self.source_edge)

    def test_dest_connect_edge_validation(self):
        """
        Checks edge validation for Dest.
        """
        with self.subTest("only edge allowed"):
            with self.assertRaises(TypeError):
                self.dest.connect_edge(object())  # type: ignore

        with self.subTest("edge output cross-link"):
            with self.assertRaises(ValueError):
                self.dest.connect_edge(self.source_edge)

        with self.subTest("success"):
            self.dest.connect_edge(self.dest_edge)

        with self.subTest("slot is busy"):
            with self.assertRaises(RuntimeError):
                self.dest.connect_edge(self.dest_edge)


class FilterGraphBaseTestCase(TestCase):

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


class FilterGraphTestCase(FilterGraphBaseTestCase):

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
            '[0:v:0][v:scale0]overlay=x=20:y=20[v:overlay0]',
            # split video to two streams
            '[v:overlay0]split[v:split0][v:split1]',
            # each video is scaled to own size
            '[v:split0]scale=w=640:h=480[vout0]',
            '[v:split1]scale=w=1280:h=720[vout1]',

            # split audio to two streams
            '[0:a:0]asplit[aout0][aout1]',

            # logo scaling
            '[1:v:0]scale=w=200:h=50[v:scale0]',
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
            self.assertEqual('[0:v:0]scale=w=640:h=360[vout0]', fc.render())

        with self.subTest("intermediate filter disabled"):
            fc, src, dst = fc_factory()

            src | deint_factory() | Scale(640, 360) > dst.video
            self.assertEqual('[0:v:0]scale=w=640:h=360[vout0]', fc.render())

        with self.subTest("all filters disabled"):
            fc, src, dst = fc_factory()

            tmp = src | deint_factory()
            tmp = tmp | deint_factory()
            tmp | Scale(640, 360) > dst.video
            self.assertEqual('[0:v:0]scale=w=640:h=360[vout0]', fc.render())

        with self.subTest("two filters disabled"):
            fc, src, dst = fc_factory()

            tmp = src | Scale(640, 360)
            tmp = tmp | deint_factory()
            tmp | deint_factory() > dst.video
            self.assertEqual('[0:v:0]scale=w=640:h=360[vout0]', fc.render())

    def test_skip_not_connected_sources(self):
        """ Skip unused sources in filter complex.
        """
        # passing only video to FilterComplex
        self.source | Scale(640, 360) > self.output

        self.assertEqual('[0:v:0]scale=w=640:h=360[vout0]', self.fc.render())

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
         -filter_complex '[0:v:0][1:v]overlay=x=100:y=100' test.mp4
        """
        vs = inputs.Stream(VIDEO, meta=video_meta_data(width=100, height=100))
        self.input_list.append(inputs.input_file('logo.png', vs))
        overlay = self.source | Overlay(
            x=self.video_metadata.width - 2,
            y=self.video_metadata.height - 2)
        vs | overlay
        overlay > self.output

        expected = '[0:v:0][1:v:0]overlay=x=1918:y=1078[vout0]'
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

    def test_concat_scenes(self):
        """
        Concat shifts scenes start/end timestamps.
        """
        video_meta = video_meta_data(duration=1000.0,
                                     frame_count=10000,
                                     frame_rate=10.0)
        vs1 = inputs.Stream(VIDEO, meta=video_meta)
        vs2 = inputs.Stream(VIDEO, meta=video_meta)
        vs3 = inputs.Stream(VIDEO, meta=video_meta)

        c = Concat(VIDEO, input_count=3)
        vs1 | c
        vs2 | c
        vs3 | c
        expected = (
                deepcopy(vs1.meta.scenes) +
                deepcopy(vs2.meta.scenes) +
                deepcopy(vs3.meta.scenes)
        )
        assert len(expected) == 3
        current_duration = TS(0)
        for scene in expected:
            scene.position += current_duration
            current_duration += scene.duration
        self.assertListEqual(c.meta.scenes, expected)

    def test_video_trim_metadata(self):
        # noinspection GrazieInspection
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

    def test_video_trim_end_of_stream(self):
        """
        If Trim ends after stream end, duration is set to min value.
        """
        f = self.source | Trim(VIDEO, start=5.0, end=400.0) | SetPTS(VIDEO)
        f > self.output
        vm = cast(VideoMeta, self.output.codecs[0].get_meta_data())
        self.assertEqual(vm.duration, TS(295.0))

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
        # noinspection GrazieInspection
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
        A filter may be defined that allows to be used with any hardware
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

    def test_upload_filter_clone(self):
        """ While cloning Upload filter should preserve Device instance."""
        cuda = meta.Device(hardware='cuda', name='foo')
        upload = self.source.video | Upload(device=cuda)

        upload = upload.clone(2)[1]
        vm = cast(VideoMeta, upload.meta)
        self.assertEqual(vm.device, cuda)

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

    def test_split_enable(self):
        """
        Disabled split is omitted in filter graph definition.
        """
        split = self.source.video | Split(VIDEO, output_count=1)
        self.assertFalse(split.enabled)
        split.enabled = True
        # you can't explicitly enable a split with single output
        self.assertFalse(split.enabled)

        split = self.source.video | Split(VIDEO, output_count=2)
        self.assertTrue(split.enabled)
        with self.assertRaises(ValueError):
            split.enabled = False

    def test_split_args(self):
        """
        Split args contain only a number of output edges.
        """
        split = self.source.video | Split(VIDEO, output_count=3)
        self.assertEqual(split.args, '3')


class CopyCodecTestCase(FilterGraphBaseTestCase):
    """
    Tests for filter graph behavior with codec=copy.
    """

    def test_copy_codec_kind_required(self):
        """
        As codec is initially added to output file, its kind can't be
        autodetected and thus is required.
        """
        with self.assertRaises(NotImplementedError):
            codecs.Copy()

        self.assertEqual(codecs.Copy(kind=VIDEO).kind, VIDEO)
        self.assertEqual(codecs.Copy(kind=AUDIO).kind, AUDIO)

    def test_copy_codec_filter_forbidden(self):
        """
        Copy codec must use a stream as source, not a filter from graph.
        """
        with self.assertRaises(ValueError):
            self.source.video | Scale(1920, 1080) > codecs.Copy(kind=VIDEO)

        self.assertIsInstance(self.source.video > codecs.Copy(kind=VIDEO),
                              codecs.Copy)

    def test_copy_codec_transient_filter_forbidden(self):
        """
        Copy codec must use a stream as a source, even if temporarily connected
        to a split filter.
        """
        with self.assertRaises(ValueError):
            chain = self.source.video | Scale(1920, 1080) | Split(VIDEO)
            chain > codecs.Copy(kind=VIDEO)

        chain = self.source.video | Split(VIDEO)
        self.assertIsInstance(chain > codecs.Copy(kind=VIDEO), codecs.Copy)

    def test_split_disconnect_on_copy_codec(self):
        """
        Split can remove output edge from itself.
        """
        split = self.source.video | Split(VIDEO, output_count=2)
        s1 = split
        s2 = split | Scale(1920, 1080)

        copy = s1 > codecs.Copy(kind=VIDEO)

        # one output left
        self.assertListEqual(split.outputs, [s2.input])
        # split is disabled because of single output
        self.assertFalse(split.enabled)
        # copy codec is connected to source
        self.assertIs(copy.edge.input, self.source.video)

    def test_split_disconnect_transient(self):
        """
        With multiple splits, copy codec is being disconnected from all of them.
        """
        video = self.source.video
        inter = video | Split(VIDEO, output_count=1)
        split = inter | Split(VIDEO, output_count=2)
        s1 = split
        s2 = split | Scale(1920, 1080)

        copy = s1 > codecs.Copy(kind=VIDEO)

        # one output left
        self.assertListEqual(split.outputs, [s2.input])
        # split is disabled because of single output
        self.assertFalse(split.enabled)

        # intermediate split is still connected to another split
        self.assertIs(inter.output.output, split)
        # copy codec is connected to source
        self.assertIs(copy.edge.input, video)
        # source is still connected to split
        edges = video._outputs
        expected = [copy.edge, inter.input]
        self.assertEqual(len(edges), 2)
        self.assertSetEqual(set(edges), set(expected))

    def test_split_disconnect_on_single_output(self):
        """
        Transitive split disconnection on copy codec.
        """
        split = self.source.video | Split(VIDEO, output_count=2)
        s2 = split | Split(VIDEO, output_count=1)
        s = Scale(1920, 1080)
        split | s

        s2 > codecs.Copy(kind=VIDEO)

        # s2 is now zero-output, so it's also disconnected from split.
        self.assertListEqual(split.outputs, [s.input])

    def test_disconnect_split_without_parent(self):
        """
        If parent node is not connected, split disconnect also works.
        """
        video = self.source.video
        split = video | Split(VIDEO, output_count=1)
        scale = split | Scale(1920, 1080)
        # There is no valid way to use a filter without a connected input,
        # because of StreamValidationMixin that checks stream kind.
        split.inputs[0] = None

        edge = split.disconnect(scale.input)
        self.assertIsNone(edge)

        self.assertListEqual(split.outputs, [])

    def test_end_disconnect_on_source(self):
        """
        Split disconnection ends with Source input node.
        """
        video = self.source.video
        split = video | Split(VIDEO, output_count=1)
        scale = split | Scale(1920, 1080)

        edge = split.disconnect(scale.input)

        self.assertIs(edge.input, video)

    def test_deny_disconnect_from_other_filters(self):
        """
        Disconnect operation is valid only with split filters.
        """
        scale = self.source.video | Scale(1920, 1080)
        split = cast(Split, scale | Split(VIDEO, output_count=1))
        s1 = split | VideoFilter()

        with self.assertRaises(RuntimeError):
            split.disconnect(s1.input)
