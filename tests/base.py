from unittest import TestCase

from fffw.encoding import FFMPEG
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
