import re
import subprocess
from functools import wraps
from logging import getLogger
from typing import Tuple, List, Any, Dict, Union, overload, IO, cast, Callable


def quote(token: Any) -> str:
    """ Escapes a token for command line."""
    token = ensure_text(token)
    if re.search(r'[ ()[\];]', token):
        return '"%s"' % token.replace('\"', '\\"')
    return token


@overload
def ensure_binary(x: Tuple[Any, ...]) -> Tuple[bytes, ...]:
    ...


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


class BaseWrapper:
    """
    Base class for generating command line arguments from params.

    Values meanings:
    * True: flag presense
    * False/None: flag absense
    * List/Tuple: param name is repeated multiple times with values
    * Callable: function call result is added to result
    * All other: param name and value are added to result
    """
    arguments: List[Tuple[str, str]] = []

    def __init_args(self) -> None:
        self._key_mapping = {}
        self._args: Dict[str, Any] = {}
        self._args_order = []
        for (name, key) in self.arguments:
            self._key_mapping[name] = key
            self._args[name] = None
            self._args_order.append(name)

    def __init__(self, **kw: Any):
        self.__init_args()
        for k, v in kw.items():
            setattr(self, k, v)
        self._output = ''
        cls = self.__class__
        self.logger = getLogger("%s.%s" % (cls.__module__, cls.__name__))

    def __setattr__(self, key: str, value: Any) -> None:
        if key in getattr(self, '_key_mapping', {}):
            self._args[key] = value
        else:
            object.__setattr__(self, key, value)

    @ensure_binary
    def get_args(self) -> List[Any]:
        result = []
        for k in self._args_order:
            v = self._args[k]
            if v is not None and v is not False:
                param = self._key_mapping[k]
                if callable(v):
                    value = v()
                    if isinstance(value, list):
                        result.extend(value)
                    else:
                        result.append(value)
                elif isinstance(v, list):
                    for item in v:
                        result.extend([param.strip(), item])
                elif v is True:
                    result.append(param.strip())
                else:
                    if param.endswith(' '):
                        result.extend([param.strip(), str(v)])
                    else:
                        result.append("%s%s" % (param, v))

        return result

    def set_args(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get_cmd(self) -> str:
        return ' '.join(map(quote, ensure_text(self.get_args())))

    def handle_stderr(self, line: str) -> None:
        self.logger.debug(line.strip())
        self._output += line

    def run(self) -> Tuple[int, str]:
        self._output = ''
        self.logger.info(self.get_cmd())
        args = self.get_args()

        with subprocess.Popen(args, stderr=subprocess.PIPE) as proc:
            while True:
                stderr = cast(IO[bytes], proc.stderr)
                line = stderr.readline()
                if not line:
                    break
                self.handle_stderr(ensure_text(line))
        self.logger.info("%s return code is %s", args[0], proc.returncode)
        return proc.returncode, self._output
