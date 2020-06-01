from dataclasses import field, dataclass
from typing import Any, Optional, Tuple, cast


def param(default: Any = None, name: Optional[str] = None,
          stream_suffix: bool = False, init: bool = True) -> Any:
    metadata = {
        'name': name,
        'stream_suffix': stream_suffix,
    }
    if callable(default):
        return field(default_factory=default, init=init, metadata=metadata)
    else:
        return field(default=default, init=init, metadata=metadata)


_FROZEN = '__frozen__'


@dataclass
class Params:
    ALLOWED = cast(Tuple[str], tuple())

    def __post_init__(self) -> None:
        getattr(super(), '__post_init__', lambda: None)()
        setattr(self, _FROZEN, True)

    def __setattr__(self, key: str, value: Any) -> None:
        frozen = getattr(self, _FROZEN, False)
        allowed = self.ALLOWED
        if frozen and key not in allowed:
            raise RuntimeError("Parameters are frozen")
        object.__setattr__(self, key, value)
