import io
import select
import subprocess
import time
from dataclasses import dataclass
from logging import getLogger
from typing import Tuple, List, Any, Optional

from fffw.wrapper.helpers import quote, ensure_binary, ensure_text
from fffw.wrapper.params import Params


class CommandMixin:
    command: str
    key_prefix: str = '-'
    key_suffix: str = ' '
    stdin = None
    stdout = subprocess.PIPE
    stderr = subprocess.PIPE


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

    def start_process(self) -> subprocess.Popen:
        self.logger.info(self.get_cmd())
        args = [ensure_binary(self.command)] + self.get_args()
        return subprocess.Popen(args,
                                stdin=self.stdin,
                                stderr=self.stdout,
                                stdout=self.stderr)

    def handle_stdout_event(self):
        line = self._proc.stdout.readline()
        self._output.write(self.handle_stdout(ensure_text(line)))
        return bool(line)

    def handle_stderr_event(self):
        line = self._proc.stderr.readline()
        self._errors.write(self.handle_stderr(ensure_text(line)))
        return bool(line)

    # noinspection PyAttributeOutsideInit
    def run(self, timeout: Optional[float] = None) -> Tuple[int, str, str]:
        self._proc = self.start_process()
        self._output = io.StringIO()
        self._errors = io.StringIO()
        self._timeout = timeout
        self._deadline = timeout and time.time() + timeout
        try:
            with self._proc:
                handlers, poll = self.init_stream_handers()
                spin = 1024  # ms
                while self._proc.poll() is None:
                    spin = self.poll_process(handlers, poll, spin)
                for handler in handlers.values():
                    # read data from buffered streams
                    while handler():
                        pass

        finally:
            if self._proc.returncode is None:
                self.logger.warning("killing %s", self.command)
                self._proc.kill()
            return_code = self._proc.returncode
            output = self._output.getvalue()
            errors = self._errors.getvalue()
            self._proc = self._output = self._errors = None
            self._timeout = self._deadline = None

        self.logger.info("%s return code is %s", self.command, return_code)
        return return_code, output, errors

    def poll_process(self, handlers, poll, spin):
        for fd, event in poll.poll(spin):
            handlers[fd]()
            # speedup stdout/stderr reading if present
            spin = max(1, spin // 2)
        else:
            # slow down if no output is read
            spin = min(1024, spin * 2)
            if self._deadline and self._deadline < time.time():
                self.logger.error("Process %s timeouted",
                                  self.command)
                raise subprocess.TimeoutExpired(self._proc.args,
                                                self._timeout)
        return spin

    def init_stream_handers(self):
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
        return handlers, poll
