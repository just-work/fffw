from dataclasses import field, dataclass, Field, fields, MISSING
from typing import Any, Optional, Tuple, cast, List, Callable


def param(default: Any = None, name: Optional[str] = None,
          stream_suffix: bool = False, init: bool = True, skip: bool = False,
          render: Callable[[Any], Any] = None
          ) -> Any:
    """
    Command line and filter parameters constructor.

    :param default: default value for parameter, or a callable (see dataclass
        field default_factory)
    :param name: command line argument name
    :param stream_suffix: flag to add stream specifier suffix to parameter name
        (like '-b:v' or '-c:a')
    :param init: add parameter to dataclass constructor.
    :param skip: skip parameter while generating command line args list.
    :param render: a callable used to format output value.
    :return: dataclass field definition with extra metadata.

    >>> from fffw.encoding.filters import VideoFilter
    >>> @dataclass
    ... class Deinterlace(VideoFilter):
    ...     filter = 'yadif'
    ...     mode: int = param(default=0)
    ...
    >>>
    """
    metadata = {
        'name': name,
        'stream_suffix': stream_suffix,
        'skip': skip,
        'render': render
    }
    if callable(default):
        return field(default_factory=default, init=init, metadata=metadata)
    else:
        return field(default=default, init=init, metadata=metadata)


_FROZEN = '__frozen__'


@dataclass
class Params:
    """ Base class for parametrized objects."""
    ALLOWED = cast(Tuple[str], tuple())
    """ 
    List of attributes that are allowed to be set after instance initialization.
    """

    def __post_init__(self) -> None:
        """ Marks class instance as frozen."""
        setattr(self, _FROZEN, True)

    def __setattr__(self, key: str, value: Any) -> None:
        """ If class is frozen, forbids instance attributes modification."""
        frozen = getattr(self, _FROZEN, False)
        allowed = self.ALLOWED
        if frozen and key not in allowed:
            raise RuntimeError("Parameters are frozen")
        object.__setattr__(self, key, value)

    @property
    def _fields(self) -> Tuple[Field, ...]:
        """
        :return: ordered list of dataclass field
        """
        return fields(self)

    def as_pairs(self) -> List[Tuple[Optional[str], Optional[str]]]:
        """
        :return: a list or pairs (key, value), where key is optional ffmpeg
            parameter name and value is parameter value

        * parameters are all dataclass fields without `skip` flag.
        * by default field name is used as ffmpeg parameter name, but this
          can be overridden by `name` metadata field.
        * if `name` is empty, key is omitted.
        * if `stream_suffix` metadata flag is set, `:v` or `:a` modifier is
          appended to key depending of current object stream kind.
        * if value is callable, real value is computed via function call
        * if value is iterable, corresponding parameter is added to a result
          multiple times
        * if value is `True`, parameter is added as a flag without a value
        """
        args = cast(List[Tuple[Optional[str], Optional[str]]], [])
        for f in self._fields:  # type: Field
            key = f.name
            value = getattr(self, key)
            if f.default is not MISSING and f.default == value and f.init:
                # if field value has default value and is configurable via
                # __init__, we omit this field
                continue
            if not value:
                # if value is not set, we omit this field
                continue

            meta = f.metadata
            name = meta.get('name')
            stream_suffix = meta.get('stream_suffix')
            skip = meta.get('skip')
            render = meta.get('render')
            if skip:
                # if field metadata is marked as `skip`
                continue
            if name is None:
                # by default field name is used as parameter name
                name = key
            if stream_suffix:
                # append stream suffix (':v' or ':a') to parameter name
                name = f'{name}:{getattr(self, "kind").value}'
            if callable(render):
                value = render(value)

            if callable(value):
                # get lazy parameter value
                value = value()

            if isinstance(value, (list, tuple)):
                # output multiple parameter values (-i file1 -i file2 ...)
                args.extend((name, str(v)) for v in value)
            elif value is True:
                # support flag without a value
                assert name
                args.append((name, None))
            else:
                # output parameter name and value converted to string
                args.append((name, str(value)))
        return args
