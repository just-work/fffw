import io
import subprocess
from dataclasses import dataclass
from logging import getLogger
from typing import Tuple, List, Any, IO, cast, Optional

from fffw.wrapper.helpers import quote, ensure_binary, ensure_text
from fffw.wrapper.params import Params


@dataclass
class BaseWrapper(Params):
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
        return ' '.join(map(quote, ensure_text(self.get_args())))

    def handle_stderr(self, line: str) -> str:
        self.logger.debug(line.strip())
        return line

    def run(self) -> Tuple[int, str]:
        output = io.StringIO()
        self.logger.info(self.get_cmd())
        args = self.get_args()

        with subprocess.Popen(args, stderr=subprocess.PIPE) as proc:
            while True:
                stderr = cast(IO[bytes], proc.stderr)
                line = stderr.readline()
                if not line:
                    break
                output.write(self.handle_stderr(ensure_text(line)))
        self.logger.info("%s return code is %s", args[0], proc.returncode)
        return proc.returncode, output.getvalue()
