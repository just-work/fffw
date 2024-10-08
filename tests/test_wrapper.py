import asyncio
import io
import random
import sys
import time
from dataclasses import dataclass
from typing import List
from unittest import TestCase, mock

from fffw.graph import TS
from fffw.wrapper import param
from fffw.wrapper.base import UniversalLineReader, BaseWrapper
from fffw.wrapper.params import Params


@dataclass
class Python(BaseWrapper):
    command = 'python'
    module: str = param(name='m')


def script():
    line = input()
    sys.stdout.write(f'stdout: {line}\n')
    sys.stderr.write(f'stderr: {line}\n')
    time.sleep(int(line) // 100)
    return int(line)


if __name__ == '__main__':
    sys.exit(script())


class WrapperTestCase(TestCase):

    def test_run_child_process(self):
        p = Python(module='tests.test_wrapper')
        ret, out, err = p.run('1')
        self.assertEqual(ret, 1)
        self.assertEqual(out, 'stdout: 1\n')
        self.assertEqual(err, 'stderr: 1\n')

    def test_child_timeout(self):
        p = Python(module='tests.test_wrapper')
        ret, out, err = p.run('100', timeout=0.01)
        self.assertEqual(ret, -9)

    def test_child_timeout_process_missing(self):
        """
        Handle ProcessLookupError if process exited just before timeout.
        """
        p = Python(module='tests.test_wrapper')
        with mock.patch('asyncio.subprocess.Process.kill',
                        side_effect=ProcessLookupError) as kill_mock:
            ret, out, err = p.run('100', timeout=0.01)
        kill_mock.assert_called_once_with()
        self.assertEqual(ret, 100)


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

    def test_unicode_error_handling(self):
        real_log_line = (b'[info]         handler_name    : '
                         b'\x8e\xe1\xf0\xe0\xe1\xee\xf2\xf7\xe8\xea '
                         b'\xe2\xe8\xe4\xe5\xee Apple\n')
        self.data.write(real_log_line)
        self.data.seek(0)

        string = asyncio.get_event_loop().run_until_complete(self.iterate())

        self.assertIn("handler_name", '\n'.join(string))
        self.assertIn("Apple", '\n'.join(string))


@dataclass
class Wrapper(Params):
    field: TS  # no default and TS instance


class ParamsTestCase(TestCase):
    """ Check command line parameters rendering."""

    def test_as_pairs_if_default_is_missing(self):
        """
        Checks that missing default does not checks value for equality with
        dataclasses.MISSING.
        """
        w = Wrapper(TS(42.0))
        self.assertEqual(w.as_pairs(), [('field', '42.0')])
