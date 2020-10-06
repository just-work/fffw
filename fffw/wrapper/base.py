import asyncio
import io
import subprocess
from asyncio.subprocess import Process
from dataclasses import dataclass
from logging import getLogger
from types import TracebackType
from typing import Tuple, List, Any, Optional, cast, Callable, Union, TextIO, \
    Type

from fffw.wrapper.helpers import quote, ensure_binary, ensure_text
from fffw.wrapper.params import Params


class Runner:
    """ Wrapper for Popen process for non-blocking streams handling."""

    def __init__(self, command: Union[str, bytes], *args: Any,
                 stdin: Union[None, str, TextIO] = None,
                 stdout: Optional[Callable[[str], str]] = None,
                 stderr: Optional[Callable[[str], str]] = None,
                 timeout: Union[int, float, None] = None) -> None:
        """
        :param command: executable file name
        :param args: executable arguments
        :param stdin: input stream or content
        :param stdout: output stream line handler
        :param stderr: error stream line handler
        :param timeout: process execution timeout
        """
        self.command = ensure_binary(command)
        self.args = ensure_binary(list(args))
        if isinstance(stdin, str):
            stdin = io.StringIO(stdin)
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.timeout = timeout
        self.output = io.StringIO()
        self.errors = io.StringIO()

    async def start_process(self) -> Process:
        """ Starts child process."""
        return await asyncio.create_subprocess_exec(
            self.command, *self.args,
            stdin=self.stdin and subprocess.PIPE,
            stdout=self.stdout and subprocess.PIPE,
            stderr=self.stderr and subprocess.PIPE,
        )

    async def __aenter__(self) -> Process:
        """ Starts child process and initialize I/O handling."""
        self.proc = await self.start_process()
        return self.proc

    async def __aexit__(self,
                        exc_type: Optional[Type[BaseException]],
                        exc_val: Optional[BaseException],
                        exc_tb: TracebackType) -> None:
        await self.proc.wait()

    def __call__(self) -> Tuple[int, str, str]:
        return asyncio.get_event_loop().run_until_complete(self.run())

    @staticmethod
    async def read(reader: Optional[asyncio.StreamReader],
                   callback: Optional[Callable[[str], str]],
                   output: io.StringIO) -> None:
        """
        Handles read from stdout/stderr.

        Reads lines from reader and feeds it to callback. Values, filtered by
        callback, are written to output buffer.

        :param reader: Process.stdout or Process.stderr instance
        :param callback: callback for handling read lines
        :param output: output biffer
        """
        if callback is None or reader is None:
            return
        while True:
            line = await reader.readline()
            if line:
                data = callback(line.decode())
                if data:
                    output.write(data)
            else:
                break

    @staticmethod
    async def write(writer: Optional[asyncio.StreamWriter],
                    stream: Optional[TextIO]) -> None:
        """
        Handle write to stdin.

        :param writer: Process.stdin instance
        :param stream: stream to read lines from
        """
        if stream is None or writer is None:
            return
        while True:
            line = stream.readline()
            if not line:
                break
            writer.write(line.encode())
            try:
                await writer.drain()
            except (ConnectionResetError, BrokenPipeError):
                # inspired by Process.communicate
                return
        writer.close()

    async def run(self) -> Tuple[int, str, str]:
        async with self as p:
            try:
                await asyncio.wait_for(
                    asyncio.shield(asyncio.gather(
                        # write input data to stdin
                        self.write(p.stdin, self.stdin),
                        # read output from stdout
                        self.read(p.stdout, self.stdout, self.output),
                        # read output from stderr
                        self.read(p.stderr, self.stderr, self.errors),
                        # wait for process termination
                        p.wait(),
                    )),
                    timeout=self.timeout)
            except asyncio.TimeoutError:
                self.proc.kill()
        return (cast(int, self.proc.returncode),
                self.output.getvalue(),
                self.errors.getvalue())


# noinspection PyTypeChecker
class CommandMixin:
    command: str
    key_prefix: str = '-'
    key_suffix: str = ' '
    stdout: bool = True
    stderr: bool = True
    timeout: Optional[float] = None
    runner_class = Runner


@dataclass
class BaseWrapper(CommandMixin, Params):
    """
    Base class for generating command line arguments from params.

    Values meanings:
    * True: flag presence
    * False/None: flag absence
    * List/Tuple: param name is repeated multiple times with values
    * Callable: function call result is added to result
    * All other: param name and value are added to result
    """

    def __post_init__(self) -> None:
        cls = self.__class__
        self.logger = getLogger("%s.%s" % (cls.__module__, cls.__name__))

    @ensure_binary
    def get_args(self) -> List[Any]:
        args: List[str] = []
        for key, value in self.as_pairs():
            tokens = []
            if key:
                tokens.append(f'{self.key_prefix}{key}')
            if value:
                tokens.append(value)
            if tokens:
                if self.key_suffix == ' ':
                    args.extend(tokens)
                else:
                    args.append(self.key_suffix.join(tokens))
        return args

    def get_cmd(self) -> str:
        command_line = [self.command] + ensure_text(self.get_args())
        return ' '.join(map(quote, command_line))

    def handle_stderr(self, line: str) -> str:
        if line != '':
            self.logger.debug(line.strip())
        return line

    def handle_stdout(self, line: str) -> str:
        if line != '':
            self.logger.debug(line.strip())
        return line

    def run(self,
            stdin: Union[None, str, TextIO] = None,
            timeout: Optional[float] = None) -> Tuple[int, str, str]:
        args = self.get_args()
        self.logger.debug(self.get_cmd())
        runner = self.runner(
            self.command, *args,
            stdin=stdin,
            stdout=self.handle_stdout if self.stdout else None,
            stderr=self.handle_stderr if self.stderr else None,
            timeout=timeout
        )
        return runner()

    def runner(self,
               command: Union[str, bytes],
               *args: Any,
               stdin: Union[None, str, TextIO] = None,
               stdout: Optional[Callable[[str], str]] = None,
               stderr: Optional[Callable[[str], str]] = None,
               timeout: Union[int, float, None] = None) -> Runner:
        """ Initializer runner instance."""
        return self.runner_class(
            command,
            *args,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
            timeout=timeout)
