from dataclasses import dataclass
from datetime import timedelta
from typing import List, Union

from pymediainfo import MediaInfo  # type: ignore

__all__ = [
    'Meta',
    'VideoMeta',
    'AudioMeta',
    'video_meta_data',
    'audio_meta_data',
    'TS'
]


class TS(timedelta):
    """
    Timestamp data type.

    Accepts common timestamp formats like '123:45:56.1234'.
    Integer values are parsed as milliseconds.
    """

    def __new__(cls, value: Union[int, float, str]) -> "TS":
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


@dataclass
class Meta:
    """
    Stream metadata.

    Describes common stream characteristics like bitrate and duration.
    """
    duration: TS
    """ Stream duration."""
    start: TS
    """ First frame/sample timestamp for stream."""
    bitrate: int
    """ Stream bitrate in bits per second."""


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

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.height != 0:
            assert abs(self.dar - self.width / self.height * self.par) <= 0.001
        else:
            assert str(self.dar) == 'nan'
        duration = self.duration.total_seconds()
        if duration != 0:
            assert abs(self.frame_rate - self.frames / duration) < 0.001
        else:
            assert self.frame_rate == 0


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

    def validate(self) -> None:
        duration = self.duration.total_seconds()
        if duration != 0:
            assert abs(self.sampling_rate - self.samples / duration) < 0.001
        else:
            assert self.sampling_rate == 0


def audio_meta_data(**kwargs: str) -> AudioMeta:
    return AudioMeta(
        duration=TS(kwargs.get('duration', 0)),
        start=TS(kwargs.get('start', 0)),
        bitrate=int(kwargs.get('bit_rate', 0)),
        channels=int(kwargs.get('channel_s', 0)),
        sampling_rate=int(kwargs.get('sampling_rate', 0)),
        samples=int(kwargs.get('samples_count', 0)),
    )


def video_meta_data(**kwargs: str) -> VideoMeta:
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
    return VideoMeta(
        duration=duration,
        start=TS(kwargs.get('start', 0)),
        bitrate=int(kwargs.get('bit_rate', 0)),
        width=width,
        height=height,
        par=par,
        dar=dar,
        frame_rate=frame_rate,
        frames=frames)


def from_media_info(mi: MediaInfo) -> List[Meta]:
    streams: List[Meta] = []
    for track in mi.tracks:
        if track.track_type == 'Video':
            streams.append(video_meta_data(**track.__dict__))
        elif track.track_type == 'Audio':
            streams.append(audio_meta_data(**track.__dict__))
    return streams
