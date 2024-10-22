import json
from copy import deepcopy
from dataclasses import dataclass, fields
from datetime import timedelta
from itertools import product
from pathlib import Path
from typing import Iterable, Tuple, Any, TYPE_CHECKING, cast
from unittest import TestCase

from pymediainfo import MediaInfo  # type: ignore

from fffw.analysis import mediainfo, ffprobe
from fffw.graph import meta


def read_fixture(fn: str) -> str:
    p = Path(__file__)
    fixtures = p.parent / 'fixtures'
    with open(fixtures / fn) as f:
        return f.read()


class MetaDataTestCase(TestCase):

    def test_subclassing_video_meta(self):
        """ VideoMeta must be extensible."""
        if TYPE_CHECKING:
            from _typeshed import DataclassInstance
        else:
            DataclassInstance = object

        @dataclass
        class ExtendedVideoMeta(meta.VideoMeta, DataclassInstance):
            my_custom_metadata: str

        self.assertIn("my_custom_metadata", [f.name for f in fields(ExtendedVideoMeta)])

    def test_subclassing_audio_meta(self):
        """ VideoMeta must be extensible."""
        if TYPE_CHECKING:
            from _typeshed import DataclassInstance
        else:
            DataclassInstance = object

        @dataclass
        class ExtendedAudioMeta(meta.AudioMeta, DataclassInstance):
            my_custom_metadata: str

        self.assertIn("my_custom_metadata", [f.name for f in fields(ExtendedAudioMeta)])


class MediaInfoAnyzerTestCase(TestCase):

    def setUp(self) -> None:
        self.media_info = MediaInfo(read_fixture("test_hd.mp4.xml"))

    def test_parse_streams(self):
        streams = mediainfo.Analyzer(self.media_info).analyze()
        self.assertEqual(len(streams), 2)
        video = streams[0]
        self.assertIsInstance(video, meta.VideoMeta)
        scene = meta.Scene(stream=None,
                           start=meta.TS(0),
                           duration=meta.TS(6.740),
                           position=meta.TS(0))
        expected = meta.VideoMeta(
            scenes=[scene],
            streams=[],
            duration=meta.TS(6.740),
            start=meta.TS(0),
            bitrate=4321426,
            width=1920,
            height=1080,
            par=1.0,
            dar=1.778,
            frame_rate=50.0,
            frames=337,
            device=None,
        )
        self.assertEqual(expected, video)
        audio = streams[1]
        self.assertIsInstance(audio, meta.AudioMeta)
        scene = meta.Scene(stream=None,
                           start=meta.TS(0),
                           duration=meta.TS(6.742),
                           position=meta.TS(0))
        expected = meta.AudioMeta(
            scenes=[scene],
            streams=[],
            duration=meta.TS(6.742),
            start=meta.TS(0),
            bitrate=192000,
            sampling_rate=48000,
            channels=6,
            samples=323616,
        )
        self.assertEqual(expected, audio)

    def test_mkv_stream_duration(self):
        """ MKV duration is stored as float and this is a problem for TS constuctor."""
        original = mediainfo.Analyzer(self.media_info).analyze()
        s = read_fixture('test_hd.mp4.xml')
        s = s.replace('<Duration>6742</Duration>', '<Duration>6742.000000</Duration>')
        s = s.replace('<Duration>6740</Duration>', '<Duration>6740.000000</Duration>')
        streams = mediainfo.Analyzer(MediaInfo(s)).analyze()
        self.assertEqual(len(original), len(streams))
        for s, o in zip(streams, original):
            self.assertEqual(s.duration, o.duration)

    def test_delay_parse(self):
        """ Delay tag contains stream start timestamp."""
        s = read_fixture('master3.ts.xml')
        streams = mediainfo.Analyzer(MediaInfo(s)).analyze()
        assert streams[0].kind == meta.VIDEO
        self.assertAlmostEqual(streams[0].start, meta.TS(31.476), places=3)  # track[type=Video].Delay
        self.assertAlmostEqual(streams[0].duration, meta.TS(31.476 + 10.01), places=3)  # + track[type=Video].Duration
        self.assertAlmostEqual(streams[0].scenes[0].duration, meta.TS(10.01), places=3)
        v = cast(meta.VideoMeta, streams[0])
        frames_duration = v.frames / v.frame_rate
        self.assertAlmostEqual(frames_duration, meta.TS(10.01), places=3)
        assert streams[1].kind == meta.AUDIO
        self.assertAlmostEqual(streams[1].start, meta.TS(31.447), places=3)  # track[type=Audio].Delay
        self.assertAlmostEqual(streams[1].duration, meta.TS(31.447 + 10.007), places=3)  # + track[type=Audio].Duration
        self.assertAlmostEqual(streams[1].scenes[0].duration, meta.TS(10.007), places=3)
        a = cast(meta.AudioMeta, streams[1])
        samples_duration = a.samples / a.sampling_rate
        self.assertAlmostEqual(samples_duration, meta.TS(10.007), places=3)


class FFProbeAnyzerTestCase(TestCase):
    def setUp(self) -> None:
        self.ffprobe_info = ffprobe.ProbeInfo(**json.loads(read_fixture('test_hd.mp4.json')))

    def test_parse_streams(self):
        streams = ffprobe.Analyzer(self.ffprobe_info).analyze()
        self.assertEqual(len(streams), 2)
        video = streams[0]
        self.assertIsInstance(video, meta.VideoMeta)
        scene = meta.Scene(stream=None,
                           start=meta.TS(0),
                           duration=meta.TS(6.740),
                           position=meta.TS(0))
        expected = meta.VideoMeta(
            scenes=[scene],
            streams=[],
            duration=meta.TS(6.740),
            start=meta.TS(0),
            bitrate=4321425,
            width=1920,
            height=1080,
            par=1.0,
            dar=1.778,
            frame_rate=50.0,
            frames=337,
            device=None,
        )
        self.assertEqual(expected, video)
        audio = streams[1]
        self.assertIsInstance(audio, meta.AudioMeta)
        scene = meta.Scene(stream=None,
                           start=meta.TS(0),
                           duration=meta.TS(6.741333),
                           position=meta.TS(0))
        expected = meta.AudioMeta(
            scenes=[scene],
            streams=[],
            duration=meta.TS(6.741333),
            start=meta.TS(0),
            bitrate=192545,
            sampling_rate=48000,
            channels=6,
            samples=323584,
        )
        self.assertEqual(expected, audio)

    def test_delay_parse(self):
        """ Delay tag contains stream start timestamp."""
        s = read_fixture('master3.ts.json')
        info = ffprobe.ProbeInfo(**json.loads(s))
        streams = ffprobe.Analyzer(info).analyze()
        assert streams[0].kind == meta.VIDEO
        self.assertAlmostEqual(streams[0].start, meta.TS(31.476), places=3)  # streams[index=0].start_time
        self.assertAlmostEqual(streams[0].duration, meta.TS(31.476 + 10.01), places=3)  # + streams[index=0].duration
        self.assertAlmostEqual(streams[0].scenes[0].duration, meta.TS(10.01), places=3)
        v = cast(meta.VideoMeta, streams[0])
        frames_duration = v.frames / v.frame_rate
        self.assertAlmostEqual(frames_duration, meta.TS(10.01), places=3)
        assert streams[1].kind == meta.AUDIO
        self.assertAlmostEqual(streams[1].start, meta.TS(31.4467), places=3)  # streams[index=1].start_time
        self.assertAlmostEqual(streams[1].duration, meta.TS(31.4467 + 9.6827), places=3)  # + streams[index=1].duration
        self.assertAlmostEqual(streams[1].scenes[0].duration, meta.TS(9.6827), places=3)
        a = cast(meta.AudioMeta, streams[1])
        samples_duration = a.samples / a.sampling_rate
        self.assertAlmostEqual(samples_duration, meta.TS(9.6827), places=3)


class TimeStampTestCase(TestCase):
    td: timedelta
    ts: meta.TS
    binary_cases: Iterable[Tuple[Any, Any]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.td = timedelta(
            days=10,
            hours=12,
            minutes=34,
            seconds=56,
            microseconds=789000)
        cls.ts = meta.TS(cls.td.total_seconds())

        ms = int(cls.td.total_seconds() * 1000)
        seconds = cls.td.total_seconds()
        string = '252:34:56.789000'
        cls.binary_cases = (
            (cls.ts, cls.ts),
            (cls.ts, cls.td),
            (cls.ts, ms),
            (cls.ts, seconds),
            (cls.ts, string),
            (cls.td, cls.ts),
            (ms, cls.ts),
            (seconds, cls.ts),
            (string, cls.ts),
        )

    def assert_ts_equal(self, ts: Any, expected: float):
        self.assertIsInstance(ts, meta.TS)
        self.assertAlmostEqual(ts.total_seconds(), expected, places=4)

    def test_ts_hashable(self):
        marker = object()
        data = {float(self.ts): marker}
        self.assertIs(data.get(self.ts), marker)

    def test_ts_float(self):
        self.assertEqual(float(self.ts), self.td.total_seconds())

    def test_ts_int(self):
        self.assertEqual(int(self.ts), int(self.td.total_seconds() * 1000))

    def test_ts_deconstruction(self):
        self.assertEqual(self.ts, deepcopy(self.ts))

    def test_ts_init(self):
        cases = (
            # from float seconds
            self.td.total_seconds(),
            # from in milliseconds
            int(self.td.total_seconds() * 1000),
            # from string
            '252:34:56.789000',
        )
        for v in cases:
            with self.subTest(v):
                self.assertEqual(self.ts, meta.TS(v))

    def test_addition(self):
        for case in self.binary_cases:
            with self.subTest(case):
                first, second = case
                ts = first + second
                self.assert_ts_equal(ts, 2 * self.td.total_seconds())

    def test_substraction(self):
        for case in self.binary_cases:
            with self.subTest(case):
                first, second = case
                ts = first - second
                self.assert_ts_equal(ts, 0.0)

    def test_multiplication(self):
        cases = (
            2.0,
            2,
        )
        for case in product(cases, (True, False)):
            with self.subTest(case):
                v, rev = case
                if rev:
                    ts = v * self.ts
                else:
                    ts = self.ts * v
                self.assert_ts_equal(ts, 2 * self.td.total_seconds())

    def test_divmod(self):
        """ Test timedelta.__divmod__ behavior."""
        # noinspection PyTypeChecker
        div, mod = divmod(self.ts, self.ts)
        self.assert_ts_equal(mod, 0.0)
        self.assertIsInstance(div, int)
        self.assertEqual(div, 1)

    def test_floordiv(self):
        """ Test timedelta.__floordiv__ behavior."""
        ts = (self.ts + 0.000001) // 2
        expected = int(self.td.total_seconds() * 1000000) / 2000000.0
        self.assert_ts_equal(ts, expected)

        ts = (self.ts + 0.000001) // meta.TS(2.0)
        expected = int(self.td.total_seconds() * 1000000) // 2000000
        self.assertIsInstance(ts, int)
        self.assertEqual(ts, expected)

    def test_truediv(self):
        ts = (self.ts + 0.000001) / 2
        expected = int(self.td.total_seconds() * 1000000) / 2000000.0
        self.assert_ts_equal(ts, expected)

        ts = (self.ts + 0.000001) / 2.0
        expected = int(self.td.total_seconds() * 1000000) / 2000000.0
        self.assert_ts_equal(ts, expected)

        ts = (self.ts + 0.000001) / meta.TS(2.0)
        expected = int(self.td.total_seconds() * 1000000) / 2000000.0
        self.assertIsInstance(ts, float)
        self.assertAlmostEqual(ts, expected, places=5)

    def test_negate_abs(self):
        ts = -self.ts
        self.assert_ts_equal(ts, -self.td.total_seconds())
        self.assert_ts_equal(abs(ts), self.td.total_seconds())

    def test_compare(self):
        v = cast(meta.TS, self.ts + 0.001)
        cases = (
            v,
            v.total_seconds(),
            int(v.total_seconds() * 1000),
        )
        for v in cases:
            with self.subTest(v):
                self.assertTrue(v > self.ts)
                self.assertTrue(v >= self.ts)
                self.assertFalse(v < self.ts)
                self.assertTrue(self.ts < v)
                self.assertTrue(self.ts <= v)
                self.assertFalse(self.ts > v)
                self.assertFalse(self.ts == v)
                self.assertFalse(v == self.ts)
                self.assertTrue(v != self.ts)
                self.assertTrue(self.ts != v)

        self.assertFalse(self.ts == None)  # noqa
        self.assertTrue(self.ts != None)  # noqa
        self.assertFalse(self.ts is None)
        self.assertTrue(self.ts is not None)

    def test_total_seconds(self):
        self.assertEqual(self.ts.total_seconds(), self.td.total_seconds())

    def test_fields(self):
        self.assertEqual(self.ts.days, self.td.days)
        self.assertEqual(self.ts.seconds, self.td.seconds)
        self.assertEqual(self.ts.microseconds, self.td.microseconds)

    def test_json_serializable(self):
        self.assertEqual(json.dumps(self.ts),
                         json.dumps(self.td.total_seconds()))

    def test_str(self):
        self.assertEqual(str(self.ts), str(self.td.total_seconds()))

    def test_repr(self):
        self.assertEqual(repr(self.ts), f'TS({repr(self.td.total_seconds())})')
