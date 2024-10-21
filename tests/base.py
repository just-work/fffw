from unittest import TestCase

from fffw.encoding import FFMPEG
from fffw.graph import meta
from fffw.wrapper.helpers import ensure_text


class BaseTestCase(TestCase):
    ffmpeg: FFMPEG

    def assert_ffmpeg_args(self, *arguments: str):

        expected = list(arguments)
        args = ensure_text(self.ffmpeg.get_args())
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

    @staticmethod
    def video_meta_data(duration=10.0, width=640, height=360) -> meta.VideoMeta:
        """
        :return: correct metadata with given parameters.
        """
        return meta.VideoMeta(
            duration=meta.TS(duration),
            start=meta.TS(0),
            bitrate=500000,
            scenes=[],
            streams=[],
            width=width,
            height=height,
            par=1.0,
            dar=width / height,
            frame_rate=30,
            frames=round(duration * 30),
            device=None
        )

    @staticmethod
    def audio_meta_data(duration=10.0) -> meta.AudioMeta:
        """
        :return: correct metadata with giren parameters.
        """
        return meta.AudioMeta(
            duration=meta.TS(duration),
            start=meta.TS(0),
            bitrate=192000,
            scenes=[],
            streams=[],
            sampling_rate=48000,
            channels=2,
            samples=round(duration * 48000),
        )