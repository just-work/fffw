from dataclasses import dataclass
from unittest import TestCase, expectedFailure

from fffw.graph import *
from fffw.encoding import filters, codecs, ffmpeg
from fffw.wrapper import ensure_binary, param


@dataclass
class FFMPEG(ffmpeg.FFMPEG):
    realtime: bool = param(name='re')


@dataclass
class X264(codecs.VideoCodec):
    codec: str = codecs.codec_name('libx264')


@dataclass
class AAC(codecs.AudioCodec):
    codec: str = codecs.codec_name('aac')


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


class FFMPEGTestCase(TestCase):

    def test_ffmpeg(self):
        """ Smoke test and feature demo."""
        ff = FFMPEG(loglevel='info', realtime=True)
        ff < Input(input_file='/tmp/input.mp4')

        cv0 = X264(bitrate=700000)
        ca0 = AAC(bitrate=128000)
        ca1 = codecs.AudioCodec('libmp3lame', bitrate=394000)

        asplit = ff.audio | filters.Split(AUDIO)

        ff.video | filters.Scale(640, 360) > cv0

        asplit.connect_dest(ca0)
        asplit.connect_dest(ca1)

        out0 = Output('/tmp/out.flv', cv0, ca0)
        out1 = Output('/tmp/out.mp3', ca1)

        ff.add_output(out0)
        ff.add_output(out1)

        expected = [
            'ffmpeg',
            '-loglevel', 'info',
            '-re',
            '-i', '/tmp/input.mp4',
            '-filter_complex',
            '[0:v]scale=width=640:height=360[vout0];[0:a]asplit[aout0][aout1]',

            '-map', '[vout0]', '-c:v', 'libx264', '-b:v', '700000',
            '-map', '[aout0]', '-c:a', 'aac', '-b:a', '128000',

            '-f', 'flv',
            '/tmp/out.flv',

            '-map', '[aout1]', '-c:a', 'libmp3lame', '-b:a', '394000',
            '-f', 'mp3',
            '/tmp/out.mp3'
        ]
        self.assertEqual(ff.get_args(), ensure_binary(expected))

    def test_bypass_with_filter_complex(self):
        """ Audio stream bypass mode."""
        ff = FFMPEG('/tmp/input.mp4')
        cv0 = X264(bitrate=700000)
        ca0 = AAC(bitrate=128000)

        ff.video | filters.Scale(640, 360) > cv0

        ff > Output('/tmp/out.flv', cv0, ca0)

        expected = [
            'ffmpeg',
            '-i', '/tmp/input.mp4',
            '-filter_complex',
            '[0:v]scale=width=640:height=360[vout0]',
            '-map', '[vout0]', '-c:v', 'libx264', '-b:v', '700000',
            '-map', '0:a', '-c:a', 'aac', '-b:a', '128000',
            '-f', 'flv',
            '/tmp/out.flv'
        ]
        self.assertEqual(ff.get_args(), ensure_binary(expected))

    def test_bypass_without_filter_complex(self):
        """ Stream bypass with filter_complex missing."""
        ff = FFMPEG('/tmp/input.mp4')

        cv0 = X264(bitrate=700000)
        ca0 = AAC(bitrate=128000)
        ff > Output('/tmp/out.flv', cv0, ca0)

        expected = [
            'ffmpeg',
            '-i', '/tmp/input.mp4',
            '-map', '0:v', '-c:v', 'libx264', '-b:v', '700000',
            '-map', '0:a', '-c:a', 'aac', '-b:a', '128000',
            '-f', 'flv',
            '/tmp/out.flv'
        ]
        self.assertEqual(ff.get_args(), ensure_binary(expected))

    def test_input_stream_naming(self):
        """ Input stream naming test."""

        ff = FFMPEG()
        ff < Input(Stream(VIDEO), input_file='/tmp/input.jpg')
        ff < Input(input_file='/tmp/input.mp4')

        cv0 = X264(bitrate=700000)
        ca0 = AAC(bitrate=128000)

        overlay = filters.Overlay(0, 0)
        ff.video | filters.Scale(640, 360) | overlay
        ff.video | filters.Scale(1280, 720) | overlay
        ff.audio | Volume(-20) > ca0
        overlay > cv0

        out0 = Output('/tmp/out.flv', cv0, ca0)
        ff.add_output(out0)

        expected = [
            'ffmpeg',
            '-i', '/tmp/input.jpg',
            '-i', '/tmp/input.mp4',
            '-filter_complex',
            (
                '[0:v]scale=width=640:height=360[v:scale0];'
                '[v:scale0][v:scale1]overlay=x=0:y=0[vout0];'
                '[1:v]scale=width=1280:height=720[v:scale1];'
                '[1:a]volume=-20.00[aout0]'),
            '-map', '[vout0]', '-c:v', 'libx264', '-b:v', '700000',
            '-map', '[aout0]', '-c:a', 'aac', '-b:a', '128000',
            '-f', 'flv',
            '/tmp/out.flv'
        ]
        self.assertEqual(ff.get_args(), ensure_binary(expected))

    def test_handle_codec_copy(self):
        """ vcodec=copy connects source directly to muxer."""
        ff = FFMPEG('/tmp/input.mp4')

        cv0 = codecs.VideoCodec('copy')
        ca0 = codecs.AudioCodec('aac', bitrate=128000)

        ff.audio | Volume(20) > ca0

        out0 = Output('/tmp/out.flv', cv0, ca0)
        ff.add_output(out0)
        expected = [
            'ffmpeg',
            '-i', '/tmp/input.mp4',
            '-filter_complex',
            '[0:a]volume=20.00[aout0]',
            '-map', '0:v',
            '-c:v', 'copy',
            '-map', '[aout0]',
            '-c:a', 'aac', '-b:a', '128000',
            '-f', 'flv',
            '/tmp/out.flv'
        ]
        self.assertEqual(ff.get_args(), ensure_binary(expected))

    def test_reuse_input_files(self):
        """ Reuse input files multiple times."""
        v = Stream(VIDEO)
        a = Stream(AUDIO)
        ff = FFMPEG(Input(v, a, input_file='/tmp/input.mp4'))
        cv0 = codecs.VideoCodec('copy')
        ca0 = codecs.AudioCodec('copy')
        out0 = Output('/tmp/out0.flv', cv0, ca0)
        ff > out0

        cv1 = codecs.VideoCodec('copy')
        ca1 = codecs.AudioCodec('copy')
        out1 = Output('/tmp/out1.flv', cv1, ca1)
        v > cv1
        a > ca1
        ff > out1
        expected = [
            'ffmpeg',
            '-i', '/tmp/input.mp4',
            '-map', '0:v',
            '-c:v', 'copy',
            '-map', '0:a',
            '-c:a', 'copy',
            '-f', 'flv',
            '/tmp/out0.flv',
            '-map', '0:v',
            '-c:v', 'copy',
            '-map', '0:a',
            '-c:a', 'copy',
            '-f', 'flv',
            '/tmp/out1.flv',
        ]
        self.assertEqual(ff.get_args(), ensure_binary(expected))

    def test_handle_codec_copy_with_other_filters(self):
        """ vcodec=copy with separate transcoded output."""
        v = Stream(VIDEO)
        a = Stream(AUDIO)
        ff = FFMPEG(Input(v, a, input_file='/tmp/input.mp4'))

        cv0 = codecs.VideoCodec('copy')
        ca0 = codecs.AudioCodec('copy')
        out0 = Output('/tmp/copy.flv', cv0, ca0)

        ff > out0

        cv1 = codecs.VideoCodec('libx264')
        ca1 = codecs.AudioCodec('aac')
        out1 = Output('/tmp/out.flv', cv1, ca1)

        v | filters.Scale(640, 360) > cv1
        a > ca1

        ff.add_output(out1)

        expected = [
            'ffmpeg',
            '-i', '/tmp/input.mp4',
            '-filter_complex',
            '[0:v]scale=width=640:height=360[vout0]',
            '-map', '0:v',
            '-c:v', 'copy',
            '-map', '0:a',
            '-c:a', 'copy',
            '-f', 'flv',
            '/tmp/copy.flv',
            '-map', '[vout0]',
            '-c:v', 'libx264',
            '-map', '0:a',
            '-c:a', 'aac',
            '-f', 'flv',
            '/tmp/out.flv'

        ]
        self.assertEqual(ensure_binary(expected), ff.get_args())

    def test_transcoding_without_graph(self):
        """ Transcoding works without filter graph."""
        ff = FFMPEG()
        ff < Input(input_file='input.mp4')
        ff.add_output(Output('/dev/null', format='null'))
        expected = [
            'ffmpeg',
            '-i', 'input.mp4',
            '-f', 'null',
            '/dev/null'
        ]
        self.assertEqual(ff.get_args(), ensure_binary(expected))

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
        ff = FFMPEG()
        ff < Input(input_file='preroll.mp4')
        ff < Input(input_file='input.mp4')

        cv0 = codecs.VideoCodec('libx264')
        ca0 = codecs.AudioCodec('aac')

        preroll_ready = ff.video | filters.Scale(640, 480) | SetSAR(1)
        concat = filters.Concat(VIDEO)
        preroll_ready | concat
        ff.video | concat

        concat > cv0

        aconcat = filters.Concat(AUDIO)
        ff.audio | aconcat
        ff.audio | aconcat

        aconcat > ca0
        ff.add_output(Output('output.mp4', cv0, ca0))

        expected = [
            'ffmpeg',
            '-i', 'preroll.mp4',
            '-i', 'input.mp4',
            '-filter_complex',
            "[0:v]scale=width=640:height=480[v:scale0];"
            "[v:scale0]setsar=1[v:setsar0];"
            "[v:setsar0][1:v]concat[vout0];"
            "[0:a][1:a]concat=v=0:a=1:n=2[aout0]",
            '-map', '[vout0]',
            '-c:v', 'libx264',
            '-map', '[aout0]',
            '-c:a', 'aac',
            '-f', 'mp4',
            'output.mp4'
        ]
        self.assertEqual(ff.get_args(), ensure_binary(expected))
