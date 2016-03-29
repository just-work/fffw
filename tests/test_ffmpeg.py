# coding: utf-8

# $Id: $
from unittest import TestCase

from fffw.encoding import FFMPEG, Muxer, VideoCodec, AudioCodec
from fffw.graph import FilterComplex, filters
from fffw.wrapper import ensure_binary


class FFMPEGTestCase(TestCase):

    def testFFMPEG(self):
        """ Проверка работоспособности и демонстрация возможностей."""
        ff = FFMPEG(inputfile='/tmp/input.mp4')

        fc = FilterComplex(outputs=1, audio_outputs=2)

        asplit = fc.audio | filters.AudioSplit()

        fc.video | filters.Scale(640, 360) | fc.get_video_dest(0)

        asplit.connect_dest(fc.get_audio_dest(0))
        asplit.connect_dest(fc.get_audio_dest(1))

        ff.filter_complex = fc

        out0 = Muxer('flv', '/tmp/out.flv')
        out1 = Muxer('mp3', '/tmp/out.mp3')

        cv0 = VideoCodec(vcodec='libx264', vbitrate='700000', size='640x360')
        ca0 = AudioCodec(acodec='aac', abitrate='128000')
        ca1 = AudioCodec(acodec='libmp3lame', abitrate='394000')

        ff.add_output(out0, cv0, ca0)
        ff.add_output(out1, ca1)

        expected = [
            'ffmpeg',
            '-i', '/tmp/input.mp4',
            '-filter_complex',
                '[0:v]scale=640x360[vout0];[0:a]asplit[aout0][aout1]',
            '-f', 'flv',
                '-map', '[vout0]', '-c:v', 'libx264', '-b:v', '700000',
                '-map', '[aout0]', '-c:a', 'aac', '-b:a', '128000',
            '/tmp/out.flv',
            '-f', 'mp3',
                '-map', '[aout1]', '-c:a', 'libmp3lame', '-b:a', '394000',
            '/tmp/out.mp3'
        ]
        self.assertEqual(ff.get_args(), ensure_binary(expected))

    def testBypass(self):
        """ Проверка работы в режиме bypass, когда аудиопоток не проходит ни
        через один фильтр."""
        ff = FFMPEG(inputfile='/tmp/input.mp4')

        fc = FilterComplex(audio_inputs=0, audio_outputs=0)
        fc.video | filters.Scale(640, 360) | fc.get_video_dest(0)

        ff.filter_complex = fc

        cv0 = VideoCodec(vcodec='libx264', vbitrate='700000', size='640x360')
        ca0 = AudioCodec(acodec='aac', abitrate='128000')
        out0 = Muxer('flv', '/tmp/out.flv')
        ff.add_output(out0, cv0, ca0)

        expected = [
            'ffmpeg',
            '-i', '/tmp/input.mp4',
            '-filter_complex',
            '[0:v]scale=640x360[vout0]',
            '-f', 'flv',
            '-map', '[vout0]', '-c:v', 'libx264', '-b:v', '700000',
            '-map', '0:a', '-c:a', 'aac', '-b:a', '128000',
            '/tmp/out.flv'
        ]
        self.assertEqual(ff.get_args(), ensure_binary(expected))
        print(ff.get_cmd())
