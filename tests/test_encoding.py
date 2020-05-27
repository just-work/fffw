from unittest import TestCase

from fffw.encoding import inputs
from fffw.graph import StreamType


class InputsTestCase(TestCase):
    """ Checks ffmpeg inputs configuration."""

    def setUp(self) -> None:
        self.v1 = inputs.Stream(StreamType.VIDEO)
        self.v2 = inputs.Stream(StreamType.VIDEO)
        self.a1 = inputs.Stream(StreamType.AUDIO)
        self.a2 = inputs.Stream(StreamType.AUDIO)
        self.a3 = inputs.Stream(StreamType.AUDIO)
        self.i1 = inputs.BaseInput(input_file='i1', streams=(self.v1, self.a1))
        self.i2 = inputs.BaseInput(input_file='i2',
                                   streams=(self.a2, self.v2, self.a3))

    def test_input_list(self):
        """ Inputs and streams are properly enumerated."""
        il = inputs.InputList(self.i1, self.i2)
        self.assertEqual(il.inputs[0].index, 0)
        self.assertEqual(il.inputs[1].index, 1)
        self.assertEqual(self.v1.name, '0:v:0')
        self.assertEqual(self.a1.name, '0:a:0')
        self.assertEqual(self.v2.name, '1:v:0')
        self.assertEqual(self.a2.name, '1:a:0')
        self.assertEqual(self.a3.name, '1:a:1')

    def test_default_input(self):
        """
        By default each input has a video and an audio stream without meta.
        """
        source = inputs.BaseInput(input_file='input.mp4')
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

        il.append(inputs.BaseInput(input_file='input.mp4', streams=(self.v1,)))

        self.assertEqual(self.v1.name, '0:v:0')

    def test_validate_stream_kind(self):
        """
        Stream without proper StreamType can't be added to input.
        """
        # noinspection PyTypeChecker
        self.assertRaises(ValueError, inputs.BaseInput, input_file='input.mp4',
                          streams=(inputs.Stream(kind=None),))
