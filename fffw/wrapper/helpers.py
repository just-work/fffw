import re
from functools import wraps
from typing import Any, overload, List, Union, Callable, Tuple


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
