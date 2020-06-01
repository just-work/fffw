from dataclasses import Field, MISSING
from typing import Any, Optional, Tuple


def param(default: Any = None, name: Optional[str] = None,
          stream_suffix: bool = False, init: bool = True) -> Field:
    metadata = {
        'name': name,
        'stream_suffix': stream_suffix,
    }
    return Field(default, MISSING, init, True, None, True, metadata)


_FROZEN = '__frozen__'


class Params:
    ALLOWED: Tuple[str] = ()

    def __post_init__(self):
        setattr(self, _FROZEN, True)

    def __setattr__(self, key: str, value: Any) -> None:
        frozen = getattr(self, _FROZEN, False)
        allowed = self.ALLOWED
        if frozen and key not in allowed:
            raise RuntimeError("Parameters are frozen")
        object.__setattr__(self, key, value)
