from dataclasses import dataclass
from unittest import expectedFailure

from fffw.encoding import filters, codecs, ffmpeg, inputs, outputs
from fffw.graph import *
from fffw.wrapper import ensure_binary, param
from tests.base import BaseTestCase


@dataclass
class FFMPEG(ffmpeg.FFMPEG):
    realtime: bool = param(name='re')


@dataclass
class X264(codecs.VideoCodec):
    codec = 'libx264'


@dataclass
class AAC(codecs.AudioCodec):
    codec = 'aac'


@dataclass
class SetSAR(filters.VideoFilter):
    filter = "setsar"
    sar: float

    @property
    def args(self) -> str:
        return "%s" % self.sar


@dataclass
class Volume(filters.AudioFilter):
    filter = 'volume'
    volume: float

    @property
    def args(self) -> str:
        return "%.2f" % self.volume


class FFMPEGTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        vm = video_meta_data(duration=3600.0)
        am = audio_meta_data(duration=3600.0)
        self.source = inputs.input_file(
            'source.mp4',
            inputs.Stream(VIDEO, vm),
            inputs.Stream(AUDIO, am))

        self.logo = inputs.input_file(
            'logo.png',
            inputs.Stream(VIDEO, video_meta_data()))

        vm = video_meta_data(duration=10.0)
        am = audio_meta_data(duration=10.0)
        self.preroll = inputs.input_file(
            'preroll.mp4',
            inputs.Stream(VIDEO, vm),
            inputs.Stream(AUDIO, am))

        self.video_codec = X264(bitrate=3600000)
        self.audio_codec = AAC(bitrate=192000)

        self.output = outputs.output_file(
            'output.mp4',
            self.video_codec,
            self.audio_codec)

        self.ffmpeg = FFMPEG()

    def test_ffmpeg(self):
        """ Smoke test and feature demo."""
        ff = self.ffmpeg
        ff.loglevel = 'info'
        ff.realtime = True
        self.source.fast_seek = 123.2
        self.source.duration = TS(123.2)
        ff < self.source

        cv0 = self.video_codec
        ca0 = self.audio_codec
        ca1 = codecs.AudioCodec('libmp3lame', bitrate=394000)

        asplit = ff.audio | filters.Split(AUDIO)

        ff.video | filters.Scale(640, 360) > cv0

        asplit.connect_dest(ca0)
        asplit.connect_dest(ca1)

        out0 = self.output
        out1 = outputs.output_file('/tmp/out.mp3', ca1)

        ff > out0
        ff > out1

        self.assert_ffmpeg_args(
            'ffmpeg',
            '-loglevel', 'info',
            '-re',
            '-ss', '123.2',
            '-t', '0:02:03.2',
            '-i', 'source.mp4',
            '-filter_complex',
            '[0:v]scale=w=640:h=360[vout0];[0:a]asplit[aout0][aout1]',

            '-map', '[vout0]', '-c:v', 'libx264', '-b:v', '3600000',
            '-map', '[aout0]', '-c:a', 'aac', '-b:a', '192000',

            'output.mp4',

            '-map', '[aout1]', '-c:a', 'libmp3lame', '-b:a', '394000',
            '-vn',
            '/tmp/out.mp3'
        )

    def test_bypass_with_filter_complex(self):
        """ Audio stream bypass mode."""
        ff = self.ffmpeg
        ff < self.source

        ff.video | filters.Scale(640, 360) > self.video_codec

        ff > self.output

        self.assert_ffmpeg_args(
            'ffmpeg',
            '-i', 'source.mp4',
            '-filter_complex',
            '[0:v]scale=w=640:h=360[vout0]',
            '-map', '[vout0]', '-c:v', 'libx264', '-b:v', '3600000',
            '-map', '0:a', '-c:a', 'aac', '-b:a', '192000',
            'output.mp4'
        )

    def test_no_audio_if_no_codecs_found(self):
        """ If no audio codecs specified, set -an flag for an output."""
        ff = self.ffmpeg
        ff < self.source

        output = outputs.output_file('out.mp4', codecs.VideoCodec('libx264'))
        ff.video | filters.Scale(640, 360) > output
        ff > output

        self.assert_ffmpeg_args(
            'ffmpeg',
            '-i', 'source.mp4',
            '-filter_complex',
            '[0:v]scale=w=640:h=360[vout0]',
            '-map', '[vout0]', '-c:v', 'libx264',
            '-an',
            'out.mp4'
        )

    def test_bypass_without_filter_complex(self):
        """ inputs.Stream bypass with filter_complex missing."""
        ff = self.ffmpeg
        ff < self.source
        ff > self.output

        self.assert_ffmpeg_args(
            'ffmpeg',
            '-i', 'source.mp4',
            '-map', '0:v', '-c:v', 'libx264', '-b:v', '3600000',
            '-map', '0:a', '-c:a', 'aac', '-b:a', '192000',
            'output.mp4'
        )

    def test_input_stream_naming(self):
        """ inputs.Input stream naming test."""

        ff = self.ffmpeg
        ff < self.logo
        ff < self.source

        cv0 = self.video_codec
        ca0 = self.audio_codec

        overlay = filters.Overlay(0, 0)
        ff.video | filters.Scale(640, 360) | overlay
        ff.video | filters.Scale(1280, 720) | overlay
        ff.audio | Volume(-20) > ca0
        overlay > cv0

        ff > self.output

        self.assert_ffmpeg_args(
            'ffmpeg',
            '-i', 'logo.png',
            '-i', 'source.mp4',
            '-filter_complex',
            '[0:v]scale=w=640:h=360[v:scale0];'
            '[v:scale0][v:scale1]overlay[vout0];'
            '[1:v]scale=w=1280:h=720[v:scale1];'
            '[1:a]volume=-20.00[aout0]',
            '-map', '[vout0]', '-c:v', 'libx264', '-b:v', '3600000',
            '-map', '[aout0]', '-c:a', 'aac', '-b:a', '192000',
            'output.mp4'
        )

    def test_handle_codec_copy(self):
        """ vcodec=copy connects source directly to muxer."""
        ff = self.ffmpeg
        ff < self.source

        cv0 = codecs.VideoCodec('copy')
        ca0 = codecs.AudioCodec('aac', bitrate=128000)

        ff.audio | Volume(20) > ca0

        ff > outputs.output_file('/tmp/out.flv', cv0, ca0)
        self.assert_ffmpeg_args(
            'ffmpeg',
            '-i', 'source.mp4',
            '-filter_complex',
            '[0:a]volume=20.00[aout0]',
            '-map', '0:v',
            '-c:v', 'copy',
            '-map', '[aout0]',
            '-c:a', 'aac', '-b:a', '128000',
            '/tmp/out.flv'
        )

    def test_reuse_input_files(self):
        """ Reuse input files multiple times."""
        ff = self.ffmpeg
        ff < self.source
        v = self.source.streams[0]
        a = self.source.streams[1]

        ff > self.output

        cv1 = codecs.VideoCodec('copy')
        ca1 = codecs.AudioCodec('copy')
        out1 = outputs.output_file('/tmp/out1.flv', cv1, ca1)
        v > cv1
        a > ca1
        ff > out1
        self.assert_ffmpeg_args(
            'ffmpeg',
            '-i', 'source.mp4',
            '-map', '0:v',
            '-c:v', 'libx264', '-b:v', '3600000',
            '-map', '0:a',
            '-c:a', 'aac', '-b:a', '192000',
            'output.mp4',
            '-map', '0:v',
            '-c:v', 'copy',
            '-map', '0:a',
            '-c:a', 'copy',
            '/tmp/out1.flv',
        )

    def test_handle_codec_copy_with_other_filters(self):
        """ vcodec=copy with separate transcoded output."""
        ff = self.ffmpeg
        ff < self.source

        cv0 = codecs.VideoCodec('copy')
        ca0 = codecs.AudioCodec('copy')
        ff > outputs.output_file('/tmp/copy.flv', cv0, ca0)

        cv1 = codecs.VideoCodec('libx264')
        ca1 = codecs.AudioCodec('aac')
        self.source.streams[0] | filters.Scale(640, 360) > cv1
        self.source.streams[1] > ca1

        ff > outputs.output_file('/tmp/out.flv', cv1, ca1)

        expected = [
            'ffmpeg',
            '-i', 'source.mp4',
            '-filter_complex',
            '[0:v]scale=w=640:h=360[vout0]',
            '-map', '0:v',
            '-c:v', 'copy',
            '-map', '0:a',
            '-c:a', 'copy',
            '/tmp/copy.flv',
            '-map', '[vout0]',
            '-c:v', 'libx264',
            '-map', '0:a',
            '-c:a', 'aac',
            '/tmp/out.flv'

        ]
        self.assertEqual(ensure_binary(expected), ff.get_args())

    def test_transcoding_without_graph(self):
        """ Transcoding works without filter graph."""
        ff = self.ffmpeg
        ff < self.source
        ff > outputs.output_file('/dev/null', format='null')
        self.assert_ffmpeg_args(
            'ffmpeg',
            '-i', 'source.mp4',
            '-vn', '-an',
            '-f', 'null',
            '/dev/null'
        )

    # TODO #19 reimplement TeeMuxer
    @expectedFailure
    def test_tee_muxer(self):
        """ tee muxer args."""
        ff = FFMPEG('/tmp/input.mp4')

        cv0 = codecs.VideoCodec('libx264')
        ca0 = codecs.AudioCodec('aac')
        out0 = HLSMuxer('http://ya.ru/1.m3u8', segment_size=2)

        out1 = HLSMuxer('http://ya.ru/2.m3u8', manifest_size=5)
        ff.add_output(TeeMuxer(out0, out1), cv0, ca0)

        expected = [
            'ffmpeg',
            '-i', '/tmp/input.mp4',
            '-map', '0:v',
            '-c:v', 'libx264',
            '-map', '0:a',
            '-c:a', 'aac',
            '-f', 'tee',
            '[f=hls:hls_time=2]http://ya.ru/1.m3u8|'
            '[f=hls:hls_list_size=5]http://ya.ru/2.m3u8'
        ]
        self.assertEqual(ff.get_args(), ensure_binary(expected))

    def test_concat(self):
        """ Concat source files."""
        ff = self.ffmpeg
        ff < self.preroll
        ff < self.source

        preroll_ready = ff.video | filters.Scale(640, 480) | SetSAR(1)
        concat = filters.Concat(VIDEO)
        preroll_ready | concat
        ff.video | concat

        concat > self.video_codec

        aconcat = filters.Concat(AUDIO)
        ff.audio | aconcat
        ff.audio | aconcat

        aconcat > self.audio_codec
        ff > self.output

        self.assert_ffmpeg_args(
            'ffmpeg',
            '-i', 'preroll.mp4',
            '-i', 'source.mp4',
            '-filter_complex',
            "[0:v]scale=w=640:h=480[v:scale0];"
            "[v:scale0]setsar=1[v:setsar0];"
            "[v:setsar0][1:v]concat[vout0];"
            "[0:a][1:a]concat=v=0:a=1:n=2[aout0]",
            '-map', '[vout0]', '-c:v', 'libx264', '-b:v', '3600000',
            '-map', '[aout0]', '-c:a', 'aac', '-b:a', '192000',
            'output.mp4'
        )

    def test_detect_trim_buffering(self):
        """
        When trim and concat filters are used for editing timeline, buffering
        may occur if order of scenes in output file does not match order of same
        scenes in input file.
        """
        cases = [
            (False, [1.0, 2.0], [2.0, 3.0]),
            (True, [2.0, 3.0], [1.0, 2.0]),
            (True, [2.0, 3.0], [2.0, 4.0]),
        ]
        for case in cases:
            with self.subTest(case):
                raises, first, second = case
                ff = FFMPEG()
                s1 = inputs.Stream(VIDEO, self.source.streams[0].meta)
                s2 = inputs.Stream(VIDEO, self.source.streams[1].meta)

                ff < inputs.input_file('input.mp4', s1, s2)
                split = ff.video | filters.Split(VIDEO)
                t1 = split | filters.Trim(VIDEO, *first)
                p1 = t1 | filters.SetPTS(VIDEO)
                t2 = split | filters.Trim(VIDEO, *second)
                p2 = t2 | filters.SetPTS(VIDEO)

                concat = p1 | filters.Concat(VIDEO)
                output = outputs.output_file('output.mp4',
                                             codecs.VideoCodec('libx264'))
                p2 | concat > output

                ff > output
                try:
                    ff.check_buffering()
                except BufferError as e:
                    self.assertTrue(raises, e)
                else:
                    self.assertFalse(raises)

    def test_detect_concat_buffering(self):
        """
        When single source is used for multiple outputs, and one of outputs
        has a preroll, buffering occurs, because to output first frame for a
        non-preroll output, we need to buffer all preroll frames.
        """

        cases = [
            (False, True, True),  # preroll + source / preroll + source
            (False, True, False),  # preroll + source / preroll
            (True, False, True),  # preroll + source / source
        ]
        for case in cases:
            with self.subTest(case):
                raises, split_pre, split_src = case
                ff = FFMPEG()
                s1 = inputs.Stream(VIDEO, self.source.streams[0].meta)
                s2 = inputs.Stream(VIDEO, self.source.streams[1].meta)
                ff < inputs.input_file('preroll.mp4', s1)
                ff < inputs.input_file('source.mp4', s2)
                sf1 = s1 | filters.Split(VIDEO, output_count=int(split_pre) + 1)
                sf2 = s2 | filters.Split(VIDEO, output_count=int(split_src) + 1)

                c1 = sf1 | filters.Concat(VIDEO, input_count=2)
                sf2 | c1

                c2 = filters.Concat(VIDEO,
                                    input_count=int(split_pre) + int(split_src))
                if split_pre:
                    sf1 | c2
                if split_src:
                    sf2 | c2

                o1 = outputs.output_file("o1.mp4", codecs.VideoCodec("libx264"))
                o2 = outputs.output_file("o2.mp4", codecs.VideoCodec("libx264"))

                c1 > o1
                c2 > o2

                ff > o1
                ff > o2
                try:
                    ff.check_buffering()
                except BufferError as e:
                    self.assertTrue(raises, e)
                else:
                    self.assertFalse(raises)

    def test_fix_preroll_buffering_with_trim(self):
        """
        We can fix buffering occured from preroll by using trim filter.
        """
        ff = self.ffmpeg
        ff < self.preroll
        ff < self.source

        output = outputs.output_file('original.mp4',
                                     codecs.VideoCodec("libx264"))
        original = outputs.output_file('original.mp4',
                                       codecs.VideoCodec("libx264"))

        preroll_stream = self.preroll.streams[0]
        source_stream = self.source.streams[0]

        concat = preroll_stream | filters.Concat(VIDEO)
        source_stream | concat

        split = concat | filters.Split(VIDEO)

        split > output

        pd = preroll_stream.meta.duration
        sd = source_stream.meta.duration
        trim = split | filters.Trim(VIDEO, start=pd, end=pd + sd)

        trim | filters.SetPTS(VIDEO) > original

        ff > original
        ff > output

        ff.check_buffering()
