import asyncio
import io
import random
from typing import List
from unittest import TestCase, mock
from fffw.wrapper.base import UniversalLineReader


class UniversalLineReaderTestCase(TestCase):
    def setUp(self) -> None:
        self.data = io.BytesIO()
        self.stream = mock.MagicMock(read=self.read)
        self.reader = UniversalLineReader(self.stream, bufsize=100, blocksize=5)

    async def read(self, n=-1):
        return self.data.read(n)

    async def iterate(self) -> List[str]:
        result = []
        async for line in self.reader:
            result.append(line)
        return result

    def assert_lines(self, lines: List[str]):
        for line in lines:
            self.data.write(line.encode('utf-8'))
        self.data.seek(0)
        result = asyncio.get_event_loop().run_until_complete(self.iterate())
        self.assertListEqual(lines, result)

    def test_read_lf(self):
        lines = []
        for c in 'abcdefghijklmnopqrstuvwxyz':
            length = random.randint(0, 15)
            lines.append(c * length + '\n')
        for line in lines:
            self.data.write(line.encode('utf-8'))
        self.data.seek(0)

        self.assert_lines(lines)

    def test_read_cr(self):
        lines = []
        for c in 'abcdefghijklmnopqrstuvwxyz':
            length = random.randint(0, 15)
            lines.append(c * length + '\r')

        self.assert_lines(lines)

    def test_read_crlf(self):
        lines = []
        for c in 'abcdefghijklmnopqrstuvwxyz':
            length = random.randint(0, 15)
            lines.append(c * length + '\r\n')

        self.assert_lines(lines)

    def test_empty_lines(self):
        lines = [
            'a\n',
            '\n',
            'b\n'
        ]

        self.assert_lines(lines)

    def test_last_incomplete_line(self):
        lines = [
            'aaaaa\n',
            'b'
        ]

        self.assert_lines(lines)

    def test_empty_stream(self):
        self.assert_lines([])

    def test_buffer_overrun(self):
        max_line = 'a' * self.reader.bufsize
        lines = [max_line + '\n']

        with self.assertRaises(asyncio.LimitOverrunError):
            self.assert_lines(lines)
