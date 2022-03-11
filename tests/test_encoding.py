from dataclasses import dataclass
from unittest import TestCase

from fffw.graph import StreamType, VIDEO, AUDIO, video_meta_data
from fffw.graph import meta
from fffw.encoding import inputs, outputs, codecs, Upload, VideoCodec, filters


class H264Cuda(codecs.VideoCodec):
    codec = 'h264_nvenc'
    hardware = 'cuda'


class ScaleNPP(filters.Scale):
    filter = 'scale_npp'
    hardware = 'cuda'


class InputsTestCase(TestCase):
    """ Checks ffmpeg inputs configuration."""

    def setUp(self) -> None:
        self.v1 = inputs.Stream(StreamType.VIDEO)
        self.v2 = inputs.Stream(StreamType.VIDEO)
        self.a1 = inputs.Stream(StreamType.AUDIO)
        self.a2 = inputs.Stream(StreamType.AUDIO)
        self.a3 = inputs.Stream(StreamType.AUDIO)
        self.i1 = inputs.Input(streams=(self.v1, self.a1))
        self.i2 = inputs.Input(streams=(self.a2, self.v2, self.a3))

    def test_input_list(self):
        """ Inputs and streams are properly enumerated."""
        il = inputs.InputList((self.i1, self.i2))
        self.assertEqual(il[0].index, 0)
        self.assertEqual(il[1].index, 1)
        self.assertEqual(self.v1.name, '0:v:0')
        self.assertEqual(self.a1.name, '0:a:0')
        self.assertEqual(self.v2.name, '1:v:0')
        self.assertEqual(self.a2.name, '1:a:0')
        self.assertEqual(self.a3.name, '1:a:1')

    def test_default_input(self):
        """
        By default each input has a video and an audio stream without meta.
        """
        source = inputs.Input()
        self.assertEqual(len(source.streams), 2)
        v = source.streams[0]
        self.assertEqual(v.kind, StreamType.VIDEO)
        self.assertIsNone(v._meta)
        a = source.streams[1]
        self.assertEqual(a.kind, StreamType.AUDIO)
        self.assertIsNone(a._meta)

    def test_append_source(self):
        """
        Source file streams receive indices when appended to input list.
        """
        il = inputs.InputList()
        v3 = inputs.Stream(StreamType.VIDEO)

        il.append(inputs.Input(streams=(v3,)))

        self.assertEqual(v3.name, '0:v:0')

    def test_validate_stream_kind(self):
        """
        Stream without proper StreamType can't be added to input.
        """
        # noinspection PyTypeChecker
        self.assertRaises(ValueError, inputs.Input,
                          streams=(inputs.Stream(kind=None),),
                          input_file='input.mp4')

    def test_validate_input_hardware(self):
        """
        Hardware-decoded input could not be passed to CPU codec and so on.
        """
        vs = inputs.Stream(StreamType.VIDEO,
                           meta=video_meta_data(width=640, height=360))
        src = inputs.Input(streams=(vs,),
                           hardware='cuda',
                           device='foo')

        @dataclass
        class X264(VideoCodec):
            codec = 'libx264'
            hardware = None  # cpu only

        with self.assertRaises(ValueError):
            src.video > X264()

        with self.assertRaises(ValueError):
            src.video | filters.Scale(640, 360)

        src.video | ScaleNPP(640, 360) > H264Cuda()


class OutputsTestCase(TestCase):
    def setUp(self) -> None:
        self.video_metadata = meta.video_meta_data(
            width=1920,
            height=1080,
            dar=1.777777778,
            par=1.0,
            duration=300.0,
        )
        self.audio_metadata = meta.audio_meta_data()

        self.source = inputs.Input(
            input_file='input.mp4',
            streams=(inputs.Stream(VIDEO, meta=self.video_metadata),
                     inputs.Stream(AUDIO, meta=self.audio_metadata)))
        self.output = outputs.Output(
            output_file='output.mp4',
            codecs=[H264Cuda(), codecs.AudioCodec('aac')]
        )

    def test_codec_validates_stream_kind(self):
        """
        Video codec raises ValueError if connected to an audio stream.
        """
        with self.assertRaises(ValueError):
            self.source.video > self.output.audio

        self.source.audio > self.output.audio

    def test_codec_validates_hardware_device(self):
        """
        When using hardware-accelerated codec, it accepts only streams uploaded
        to a corresponding hardware.
        """
        with self.assertRaises(ValueError):
            self.source.video > self.output.video

        cuda = meta.Device(hardware='cuda', name='foo')
        hw_stream = self.source.video | Upload(device=cuda)
        hw_stream > self.output.video
