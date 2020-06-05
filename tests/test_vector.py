from unittest import TestCase

from fffw.encoding import *
from fffw.encoding.vector import Vector
from fffw.graph import *
from fffw.wrapper import ensure_binary


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
