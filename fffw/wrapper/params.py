from dataclasses import field, dataclass, Field, fields, asdict
from typing import Any, Optional, Tuple, cast, List, Dict


def param(default: Any = None, name: Optional[str] = None,
          stream_suffix: bool = False, init: bool = True, skip: bool = False
          ) -> Any:
    metadata = {
        'name': name,
        'stream_suffix': stream_suffix,
        'skip': skip,
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

    def as_pairs(self) -> List[Tuple[Optional[str], Optional[str]]]:
        args = cast(List[Tuple[Optional[str], Optional[str]]], [])
        local_fields: Dict[str, Field] = {
            f.name: f for f in fields(self)}
        for key, value in asdict(self).items():
            f = local_fields[key]
            if f.default == value and f.init:
                continue
            if not value:
                continue

            meta = f.metadata
            name = meta.get('name')
            stream_suffix = meta.get('stream_suffix')
            skip = meta.get('skip')
            if skip:
                continue
            if name is None:
                name = key
            if stream_suffix:
                name = f'{name}:{getattr(self, "kind").value}'
            arg = name and f'-{name}'

            if callable(value):
                value = value()

            if isinstance(value, (list, tuple)):
                args.extend((arg, str(v)) for v in value)
            elif value is True:
                assert arg
                args.append((arg, None))
            else:
                args.append((arg, str(value)))
        return args
