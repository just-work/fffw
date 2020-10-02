import io
import select
import subprocess
import time
from dataclasses import dataclass
from logging import getLogger
from typing import Tuple, List, Any, Optional, cast

from fffw.types import Literal
from fffw.wrapper.helpers import quote, ensure_binary, ensure_text
from fffw.wrapper.params import Params

# Optional subprocess PIPE, STDOUT and DEVNULL constants
Stream = Optional[Literal[-1, -2, -3]]

Streams = Tuple[Stream, Stream, Stream]


class CommandMixin:
    command: str


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
            if key:
                args.append(f'-{key}')
            if value:
                args.append(value)
        return args

    def get_cmd(self) -> str:
        command_line = [self.command] + ensure_text(self.get_args())
        return ' '.join(map(quote, command_line))

    def handle_stderr(self, line: str) -> str:
        self.logger.debug(line.strip())
        return ''

    def handle_stdout(self, line: str) -> str:
        self.logger.debug(line.strip())
        return ''

    # noinspection PyMethodMayBeStatic
    def init_streams(self) -> Streams:
        stdin = None
        stdout = cast(Literal[-1], subprocess.PIPE)
        stderr = cast(Literal[-1], subprocess.PIPE)
        return stdin, stdout, stderr

    def start_process(self) -> subprocess.Popen:
        self.logger.info(self.get_cmd())
        args = [self.command] + self.get_args()
        stdin, stdout, stderr = self.init_streams()
        return subprocess.Popen(args,
                                stdin=stdin,
                                stderr=stdout,
                                stdout=stderr)

    def handle_stdout_event(self):
        line = self._proc.stdout.readline()
        self._output.write(self.handle_stdout(ensure_text(line)))

    def handle_stderr_event(self):
        line = self._proc.stderr.readline()
        self._errors.write(self.handle_stderr(ensure_text(line)))

    # noinspection PyAttributeOutsideInit
    def run(self, timeout: Optional[float] = None) -> Tuple[int, str, str]:
        self.logger.info(self.get_cmd())
        args = self.get_args()

        self._proc = self.start_process()
        self._output = io.StringIO()
        self._errors = io.StringIO()
        ts = timeout and time.time() + timeout
        cmd = ensure_text(args[0])
        try:
            with self._proc:
                poll = select.poll()
                handlers = {}
                if self._proc.stdout is not None:
                    fd = self._proc.stdout.fileno()
                    handlers[fd] = self.handle_stdout_event
                    poll.register(fd, select.POLLIN)
                if self._proc.stderr is not None:
                    fd = self._proc.stderr.fileno()
                    handlers[fd] = self.handle_stderr_event
                    poll.register(fd, select.POLLIN)
                spin = 1024  # ms
                while self._proc.poll() is None:
                    for fd, event in poll.poll(spin):
                        handlers[fd]()
                        # speedup stdout/stderr reading if present
                        spin = max(1, spin // 2)
                    else:
                        # slow down if no output is read
                        spin = min(1024, spin * 2)
                        if ts and ts < time.time():
                            self.logger.error("Process %s timeouted", cmd)
                            self._proc.kill()

        except Exception:
            self._proc.kill()
            raise
        finally:
            return_code = self._proc.returncode
            output = self._output.getvalue()
            errors = self._errors.getvalue()
            self._proc = self._output = self._errors = None

        self.logger.info("%s return code is %s", cmd, return_code)
        return return_code, output, errors
