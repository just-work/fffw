import abc
from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import List, Union, Any, Optional

from pymediainfo import MediaInfo  # type: ignore

__all__ = [
    'AudioMeta',
    'VideoMeta',
    'StreamType',
    'AUDIO',
    'VIDEO',
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


class TS(timedelta):
    """
    Timestamp data type.

    Accepts common timestamp formats like '123:45:56.1234'.
    Integer values are parsed as milliseconds.
    """

    def __new__(cls, value: Union[int, float, str]) -> "TS":
        """
        :param value: integer duration in milliseconds, float duration in
            seconds or string ffmpeg interval definition (123:59:59.999).
        :returns new timestamp from value.
        """
        if isinstance(value, int):
            value = value / 1000.0
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
        return super().__new__(cls, seconds=value)  # type: ignore

    def __str__(self) -> str:
        """
        Removes non-valuable zeros from fractional part.

        :returns: ffmpeg seconds definition (123456.999).
        """
        v = str(self.total_seconds())
        if '.' in v:
            v = v.rstrip('0')
        return v

    def __add__(self, other: timedelta) -> "TS":
        if not isinstance(other, timedelta):
            return NotImplemented
        return TS(self.total_seconds() + other.total_seconds())

    def __sub__(self, other: timedelta) -> "TS":
        if not isinstance(other, timedelta):
            return NotImplemented
        return TS(self.total_seconds() - other.total_seconds())

    def __lt__(self, other: Union[int, float, str, timedelta, "TS"]) -> bool:
        if not isinstance(other, timedelta):
            other = TS(other)
        return self.total_seconds() < other.total_seconds()


@dataclass
class Scene:
    """
    Continuous part of stream used in transcoding graph.
    """
    stream: Optional[str]
    """ Stream identifier."""
    duration: TS
    """ Stream duration."""
    start: TS
    """ First frame/sample timestamp for stream."""

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
    """ Resulting stream duration."""
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
        duration = self.duration.total_seconds()
        if duration != 0:
            assert abs(self.sampling_rate - self.samples / duration) < 0.001
        else:
            assert self.sampling_rate == 0


def audio_meta_data(**kwargs: Any) -> AudioMeta:
    stream = kwargs.get('stream')
    duration = TS(kwargs.get('duration', 0))
    start = TS(kwargs.get('start', 0))
    scene = Scene(
        stream=stream,
        duration=duration,
        start=start,
    )

    return AudioMeta(
        scenes=[scene],
        streams=[stream] if stream else [],
        duration=duration,
        start=start,
        bitrate=int(kwargs.get('bit_rate', 0)),
        channels=int(kwargs.get('channel_s', 0)),
        sampling_rate=int(kwargs.get('sampling_rate', 0)),
        samples=int(kwargs.get('samples_count', 0)),
    )


def video_meta_data(**kwargs: Any) -> VideoMeta:
    duration = TS(kwargs.get('duration', 0))
    width = int(kwargs.get('width', 0))
    height = int(kwargs.get('height', 0))
    par = float(kwargs.get('pixel_aspect_ratio', 1.0))
    try:
        dar = float(kwargs['display_aspect_ratio'])
    except KeyError:
        if height == 0:
            dar = float('nan')
        else:
            dar = width / height * par
    frames = int(kwargs.get('frame_count', 0))
    try:
        frame_rate = float(kwargs['frame_rate'])
    except KeyError:
        if duration.total_seconds() == 0:
            frame_rate = 0
        else:
            frame_rate = frames / duration.total_seconds()

    stream = kwargs.get('stream')
    start = TS(kwargs.get('start', 0))
    scene = Scene(
        stream=stream,
        start=start,
        duration=duration,
    )
    return VideoMeta(
        scenes=[scene],
        streams=[stream] if stream else [],
        duration=duration,
        start=start,
        bitrate=int(kwargs.get('bit_rate', 0)),
        width=width,
        height=height,
        par=par,
        dar=dar,
        frame_rate=frame_rate)


def from_media_info(mi: MediaInfo) -> List[Meta]:
    streams: List[Meta] = []
    for track in mi.tracks:
        if track.track_type in ('Video', 'Image'):
            streams.append(video_meta_data(**track.__dict__))
        elif track.track_type == 'Audio':
            streams.append(audio_meta_data(**track.__dict__))
    return streams
