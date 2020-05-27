from dataclasses import dataclass
from datetime import timedelta
from typing import List, Union, Any

from pymediainfo import MediaInfo  # type: ignore


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


def audio_meta_data(**kwargs: Any) -> AudioMeta:
    return AudioMeta(
        duration=TS(kwargs.get('duration', 0)),
        start=TS(kwargs.get('start', 0)),
        bitrate=int(kwargs.get('bit_rate', 0)),
        channels=int(kwargs.get('channel_s', 0)),
        sampling_rate=int(kwargs.get('sampling_rate', 0))
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
    try:
        frame_rate = float(kwargs['frame_rate'])
    except KeyError:
        frames = int(kwargs.get('frame_count', 0))
        if frames == 0:
            frame_rate = float('nan')
        else:
            frame_rate = duration.total_seconds() / frames
    return VideoMeta(
        duration=duration,
        start=TS(kwargs.get('start', 0)),
        bitrate=int(kwargs.get('bit_rate', 0)),
        width=width,
        height=height,
        par=par,
        dar=dar,
        frame_rate=frame_rate)


def from_media_info(mi: MediaInfo) -> List[Meta]:
    streams: List[Meta] = []
    for track in mi.tracks:
        if track.track_type == 'Video':
            streams.append(video_meta_data(**track.__dict__))
        elif track.track_type == 'Audio':
            streams.append(audio_meta_data(**track.__dict__))
    return streams
