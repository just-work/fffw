import abc
from typing import Any, Dict, TypedDict, List

from fffw.graph import meta


class CommonKwargs(TypedDict):
    bitrate: int
    duration: meta.TS
    start: meta.TS
    streams: List[str]
    scenes: List[meta.Scene]


class AudioKwargs(CommonKwargs):
    channels: int
    sampling_rate: int
    samples: int


class VideoKwargs(CommonKwargs):
    width: int
    height: int
    par: float
    dar: float
    frame_rate: float
    frames: int
    device: None


class Analyzer(abc.ABC):
    """ Base implementation for media analysis."""
    audio_meta_class = meta.AudioMeta
    video_meta_class = meta.VideoMeta

    def audio_meta_data(self, **track: Any) -> meta.AudioMeta:
        kwargs = self.get_audio_kwargs(track)
        return self.audio_meta_class(**kwargs)

    def video_meta_data(self, **track: Any) -> meta.VideoMeta:
        kwargs = self.get_video_kwargs(track)
        return self.video_meta_class(**kwargs)

    def get_video_common_kwargs(self, track: Dict[str, Any]) -> CommonKwargs:
        return self.get_common_kwargs(track)

    def get_audio_common_kwargs(self, track: Dict[str, Any]) -> CommonKwargs:
        return self.get_common_kwargs(track)

    def get_audio_kwargs(self, track: Dict[str, Any]) -> AudioKwargs:
        kwargs = self.get_audio_common_kwargs(track)
        channels = self.get_channels(track)
        sampling_rate = self.get_sampling_rate(track)
        samples = self.get_samples(track)
        return dict(
            channels=channels,
            sampling_rate=sampling_rate,
            samples=samples,
            **kwargs,
        )

    def get_video_kwargs(self, track: Dict[str, Any]) -> VideoKwargs:
        kwargs = self.get_video_common_kwargs(track)

        width = self.get_width(track)
        height = self.get_height(track)
        par = self.get_par(track)
        dar = self.get_dar(track)
        frame_rate = self.get_frame_rate(track)
        frames = self.get_frames(track)

        return dict(
            device=None,
            width=width,
            height=height,
            par=par,
            dar=dar,
            frame_rate=frame_rate,
            frames=frames,
            **kwargs,
        )

    def get_common_kwargs(self, track: Dict[str, Any]) -> CommonKwargs:
        duration = self.get_duration(track)
        start = self.get_start(track)
        bitrate = self.get_bitrate(track)
        scene = meta.Scene(
            stream=None,
            duration=duration,
            start=start,
            position=start,
        )
        return {
            "duration": duration,
            "start": start,
            "bitrate": bitrate,
            "scenes": [scene],
            "streams": [],
        }

    @staticmethod
    def get_width(track: Dict[str, Any]) -> int:
        return int(track.get('width', 0))

    @staticmethod
    def get_height(track: Dict[str, Any]) -> int:
        return int(track.get('height', 0))

    @abc.abstractmethod
    def analyze(self) -> List[meta.Meta]:  # pragma: no cover
        raise NotImplementedError

    @abc.abstractmethod
    def get_duration(self, track: Dict[str, Any]) -> meta.TS:  # pragma: no cover
        raise NotImplementedError

    @abc.abstractmethod
    def get_start(self, track: Dict[str, Any]) -> meta.TS:  # pragma: no cover
        raise NotImplementedError

    @abc.abstractmethod
    def get_bitrate(self, track: Dict[str, Any]) -> int:  # pragma: no cover
        raise NotImplementedError

    @abc.abstractmethod
    def get_channels(self, track: Dict[str, Any]) -> int:  # pragma: no cover
        raise NotImplementedError

    @abc.abstractmethod
    def get_sampling_rate(self, track: Dict[str, Any]) -> int:  # pragma: no cover
        raise NotImplementedError

    @abc.abstractmethod
    def get_samples(self, track: Dict[str, Any]) -> int:  # pragma: no cover
        raise NotImplementedError

    @abc.abstractmethod
    def get_par(self, track: Dict[str, Any]) -> float:  # pragma: no cover
        raise NotImplementedError

    @abc.abstractmethod
    def get_dar(self, track: Dict[str, Any]) -> float:  # pragma: no cover
        raise NotImplementedError

    @abc.abstractmethod
    def get_frame_rate(self, track: Dict[str, Any]) -> float:  # pragma: no cover
        raise NotImplementedError

    @abc.abstractmethod
    def get_frames(self, track: Dict[str, Any]) -> int:  # pragma: no cover
        raise NotImplementedError
