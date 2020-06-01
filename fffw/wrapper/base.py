import io
import re
import subprocess
from dataclasses import dataclass
from functools import wraps
from logging import getLogger
from typing import Tuple, List, Any, Union, overload, IO, cast, Callable, \
    Optional

from fffw.wrapper.params import Params


def quote(token: Any) -> str:
    """ Escapes a token for command line."""
    token = ensure_text(token)
    if re.search(r'[ ()[\];]', token):
        return '"%s"' % token.replace('\"', '\\"')
    return token


@overload
def ensure_binary(x: List[Any]) -> List[bytes]:
    ...


@overload
def ensure_binary(x: Union[int, float, str, bytes, None]) -> bytes:
    ...


@overload
def ensure_binary(x: Callable[..., Tuple[Any]]
                  ) -> Callable[..., Tuple[bytes]]:
    ...


@overload
def ensure_binary(x: Callable[..., List[Any]]
                  ) -> Callable[..., List[bytes]]:
    ...


@overload
def ensure_binary(x: Callable[..., Union[int, float, str, bytes, None]]
                  ) -> Callable[..., bytes]:
    ...


def ensure_binary(x: Any) -> Any:
    """ Recursively ensures that all values except collections are bytes.

    * tuples and lists are encoded recursively
    * strings are encoded with utf-8
    * bytes are left intact
    * functions are decorated with ensuring binary results
    * all other types are converted to string and encoded
    """
    if isinstance(x, tuple):
        return tuple(ensure_binary(y) for y in x)
    if isinstance(x, list):
        return list(ensure_binary(y) for y in x)
    if isinstance(x, str):
        return x.encode("utf-8")
    if callable(x):
        @wraps(x)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return ensure_binary(x(*args, **kwargs))

        return wrapper
    if not isinstance(x, bytes):
        return str(x).encode("utf-8")
    return x


@overload
def ensure_text(x: Tuple[Any, ...]) -> Tuple[str, ...]:
    ...


@overload
def ensure_text(x: List[Any]) -> List[str]:
    ...


@overload
def ensure_text(x: Union[int, float, str, bytes, None]) -> str:
    ...


def ensure_text(x: Any) -> Any:
    """ Recursively ensures that all values except collections are strings."""
    if isinstance(x, tuple):
        return tuple(ensure_text(y) for y in x)
    if isinstance(x, list):
        return list(ensure_text(y) for y in x)
    if isinstance(x, bytes):
        return x.decode("utf-8")
    return str(x)


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
        args: List[Optional[str]] = []
        for pair in self.as_pairs():
            args.extend(pair)
        return list(filter(None, args))

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
