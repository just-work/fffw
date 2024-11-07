import warnings
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from functools import wraps
from typing import (
    List, Union, Any, Optional, Callable, Tuple, Literal, overload, cast
)

from pymediainfo import MediaInfo  # type: ignore

__all__ = [
    'AudioMeta',
    'VideoMeta',
    'StreamType',
    'AUDIO',
    'VIDEO',
    'Device',
    'Meta',
    'Scene',
    'TS',
    'video_meta_data',
    'audio_meta_data',
    'from_media_info',
]


class StreamType(Enum):
    VIDEO = 'v'
    AUDIO = 'a'


VIDEO = StreamType.VIDEO
AUDIO = StreamType.AUDIO

NullaryOp = Callable[[], Any]
NullaryTS = Callable[[], "TS"]
BinaryOp = Callable[[Any, Any], Any]
BinaryTS = Callable[[Any, Any], "TS"]
UnaryOp = Callable[[Any], Any]
UnaryTS = Callable[[Any], "TS"]


@overload
def ts(func: BinaryOp,
       *,
       arg: bool = True,
       res: Literal[True] = True,
       noarg: Literal[False] = False
       ) -> BinaryTS:
    ...


@overload
def ts(func: BinaryOp,
       *,
       arg: bool = True,
       res: Literal[False],
       noarg: Literal[False] = False
       ) -> BinaryOp:
    ...


@overload
def ts(func: UnaryOp,
       *,
       arg: bool = True,
       res: Literal[True] = True,
       noarg: Literal[True]
       ) -> UnaryTS:
    ...


@overload
def ts(func: UnaryOp,
       *,
       arg: bool = True,
       res: Literal[False],
       noarg: Literal[True]
       ) -> UnaryOp:
    ...


@overload
def ts(func: NullaryOp,
       *,
       arg: bool = True,
       res: Literal[True] = True,
       noarg: Literal[True]
       ) -> NullaryTS:
    ...


@overload
def ts(func: NullaryOp,
       *,
       arg: bool = True,
       res: Literal[False],
       noarg: Literal[True]
       ) -> NullaryTS:
    ...


def ts(func: Union[BinaryOp, UnaryOp, NullaryOp], *,
       arg: bool = True, res: bool = True, noarg: bool = False
       ) -> Union[BinaryTS, UnaryTS, NullaryTS]:
    """
    Decorates functions to automatically cast first argument and result to TS.
    """
    if arg and res:
        if noarg:
            @wraps(func)
            def wrapper(self: "TS") -> "TS":
                return TS(cast(UnaryOp, func)(self))  # noqa
        else:
            @wraps(func)
            def wrapper(self: "TS", value: Any) -> "TS":
                if value is None:
                    res = cast(BinaryOp, func)(self, value)  # noqa
                else:
                    res = cast(BinaryOp, func)(self, TS(value))  # noqa
                return TS(res)
    elif arg:
        @wraps(func)
        def wrapper(self: "TS", value: Any) -> Any:
            if value is None:
                return cast(BinaryOp, func)(self, value)  # noqa
            return cast(BinaryOp, func)(self, TS(value))  # noqa
    elif res:
        @wraps(func)
        def wrapper(self: "TS", value: Any) -> "TS":
            return TS(cast(BinaryOp, func)(self, value))  # noqa
    else:
        return func

    return wrapper


class TS(float):
    """
    Timestamp data type.

    Accepts common timestamp formats like '123:45:56.1234'.
    Integer values are parsed as milliseconds.
    """

    def __new__(cls, value: Union[int, float, str, timedelta]) -> "TS":
        """
        :param value: integer duration in milliseconds, float duration in
            seconds or string ffmpeg interval definition (123:59:59.999).
        :returns new timestamp from value.
        """
        if isinstance(value, timedelta):
            value = value.total_seconds()
        elif isinstance(value, int):
            value /= 1000.0
        elif isinstance(value, str):
            if '.' in value:
                value, rest = value.split('.')
                fractional = float(f'0.{rest}')
            else:
                fractional = 0
            seconds = 0
            for part in map(int, value.rsplit(':', 2)):
                seconds *= 60
                seconds += part
            value = seconds + fractional
        return super().__new__(cls, value)  # type: ignore

    __hash__ = float.__hash__
    __add__ = ts(float.__add__)
    __radd__ = ts(float.__radd__)
    __sub__ = ts(float.__sub__)
    __rsub__ = ts(float.__rsub__)
    __mul__ = ts(float.__mul__, arg=False)
    __rmul__ = ts(float.__rmul__, arg=False)
    __neg__ = ts(float.__neg__, noarg=True)
    __abs__ = ts(float.__abs__, noarg=True)
    __eq__ = ts(float.__eq__, res=False)
    __ne__ = ts(float.__ne__, res=False)
    __gt__ = ts(float.__gt__, res=False)
    __ge__ = ts(float.__ge__, res=False)
    __lt__ = ts(float.__lt__, res=False)
    __le__ = ts(float.__le__, res=False)

    @overload  # type: ignore
    def __floordiv__(self, other: "TS") -> int:
        ...

    @overload  # type: ignore
    def __floordiv__(self, other: int) -> "TS":
        ...

    def __floordiv__(self, other: Union["TS", float, int]) -> Union[int, "TS"]:
        """
        Division behavior from timedelta (rounds to microseconds)

        >>> TS(10.0) // TS(3.0)
        3
        >>> TS(10.0) // 3
        TS(3.333333)
        >>> TS(10.0) // 3.0
        TS(3.333333)
        """
        value = (float(self * 1000000.0) // other) / 1000000.0
        if isinstance(other, TS):
            return int(value)
        return TS(value)

    @overload
    def __truediv__(self, other: "TS") -> float:  # type: ignore
        ...

    @overload
    def __truediv__(self, other: Union[float, int]) -> "TS":  # type: ignore
        ...

    def __truediv__(self, other: Union["TS", float, int]) -> Union[float, "TS"]:
        """
        Division behavior from timedelta

        >>> TS(10.0) / TS(2.125)
        4.705882352941177
        >>> TS(10.0) / 2.125
        TS(4.705882352941177)
        >>> TS(10.0) / 2
        TS(5.0)
        """
        value = super().__truediv__(other)
        if isinstance(other, TS):
            return value
        return TS(value)

    def __divmod__(self, other: float) -> Tuple[int, "TS"]:
        """
        Div/mod behavior from timedelta

        >>> divmod(TS(10.0), TS(2.125))
        (4, TS(1.5))
        """
        div, mod = super().__divmod__(other)
        return int(div), TS(mod)

    def __int__(self) -> int:
        """
        :return: duration in milliseconds.
        """
        return int(float(self * 1000))

    def __str__(self) -> str:
        """
        Removes non-valuable zeros from fractional part.

        :returns: ffmpeg seconds definition (123456.999).
        """
        v = super().__repr__()
        if '.' in v:
            v = v.rstrip('0')
            if v.endswith('.'):
                v += '0'
        return v

    def __repr__(self) -> str:
        return f'TS({super().__repr__()})'

    def total_seconds(self) -> float:
        return float(self)

    @property
    def days(self) -> int:
        return int(float(self / (24 * 3600)))

    @property
    def seconds(self) -> int:
        return int(float(self) % (24 * 3600))

    @property
    def microseconds(self) -> int:
        return int(float(self * 1000000) % 1000000)


@dataclass
class Scene:
    """
    Continuous part of stream used in transcoding graph.
    """
    stream: Optional[str]
    """ Stream identifier."""
    duration: TS
    """ Stream duration from first to last timestamp."""
    start: TS
    """ First frame/sample timestamp in source stream."""
    position: TS
    """ Position of scene in current stream."""

    @property
    def end(self) -> TS:
        return self.start + self.duration


@dataclass
class Meta:
    """
    Stream metadata.

    Describes common stream characteristics like bitrate and duration.
    """
    duration: TS
    """ Resulting stream duration counted from zero timestamp."""
    start: TS
    """ First frame/sample timestamp for resulting stream."""
    bitrate: int
    """ Input stream bitrate in bits per second."""
    scenes: List[Scene]
    """ 
    List of continuous stream fragments (maybe from different files), that need
    to be read to get a result with current metadata.
    """
    streams: List[str]
    """
    List of streams (maybe from different files), that need to be read to get
    a result with current metadata."""

    @property
    def end(self) -> TS:
        """
        :return: Timestamp of last frame resulting stream.
        """
        return self.start + self.duration

    @property
    def kind(self) -> StreamType:
        raise NotImplementedError()


@dataclass
class Device:
    """
    Describes hardware device used for video acceleration
    """
    hardware: str
    name: str


@dataclass
class VideoMeta(Meta):
    """
    Video stream metadata.

    Describes video stream characteristics.
    """
    width: int
    height: int
    par: float
    """ Pixel aspect ratio."""
    dar: float
    """ Display aspect ratio."""
    frame_rate: float
    """ Frames per second."""
    frames: int
    """ Number of frames."""
    device: Optional[Device]
    """ Hardware device asociated with current stream."""

    def __post_init__(self) -> None:
        self.validate()

    @property
    def kind(self) -> StreamType:
        return VIDEO

    def validate(self) -> None:
        if self.height != 0:
            assert abs(self.dar - self.width / self.height * self.par) <= 0.001
        else:
            assert str(self.dar) == 'nan'

        interval = float(self.duration - self.start)
        assert abs(self.frames - interval * self.frame_rate) <= 1, f'{self.frames} <> {interval} * {self.frame_rate}'


@dataclass
class AudioMeta(Meta):
    """
    Audio stream metadata.

    Describes audio stream characteristics.
    """
    sampling_rate: int
    """ Samples per second."""
    channels: int
    """ Number of audio channels."""
    samples: int
    """ Samples count."""

    def __post_init__(self) -> None:
        self.validate()

    @property
    def kind(self) -> StreamType:
        return AUDIO

    def validate(self) -> None:
        interval = float(self.duration - self.start)
        assert abs(self.samples - interval * self.sampling_rate) <= 1, f'{self.samples} <> {interval} * {self.sampling_rate}'


def maybe_parse_duration(value: Union[str, float, int, None]) -> TS:
    """
    Parses duration from mediainfo output, if necessary.

    Some containers store float value and some int, but in both cases (which is different from ffmpeg) value is
    counted in milliseconds.
    """
    if value is None:
        return TS(0)
    if isinstance(value, str):
        try:
            value = int(value)
        except ValueError:
            # prepare seconds for TS constructor
            value = float(value) / 1000
    return TS(value)


def audio_meta_data(**kwargs: Any) -> AudioMeta:
    warnings.warn("use fffw.analysis.mediainfo.Analyzer.audio_meta_data", DeprecationWarning, stacklevel=2)
    from fffw.analysis.mediainfo import Analyzer
    return Analyzer().audio_meta_data(**kwargs)


def video_meta_data(**kwargs: Any) -> VideoMeta:
    warnings.warn("use fffw.analysis.mediainfo.Analyzer.video_meta_data", DeprecationWarning, stacklevel=2)
    from fffw.analysis.mediainfo import Analyzer
    return Analyzer().video_meta_data(**kwargs)


def from_media_info(mi: MediaInfo) -> List[Meta]:
    warnings.warn("use fffw.analysis.mediainfo.Analyzer.from_media_info", DeprecationWarning, stacklevel=2)
    from fffw.analysis.mediainfo import Analyzer
    return Analyzer().from_media_info(mi)
