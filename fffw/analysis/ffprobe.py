from typing import List, Dict, Any, Union, Optional

from fffw.graph import meta


class Analyzer:
    """
    Perform ffprobe analysis and normalization to obtain media stream metadata list.

    >>> from fffw.encoding.ffprobe import analyze
    >>> data = analyze('test.mp4')
    >>> streams = Analyzer().from_ffprobe_data(**data)
    """

    audio_meta_class = meta.AudioMeta
    video_meta_class = meta.VideoMeta

    @staticmethod
    def maybe_parse_rational(value: Union[str, float, None], precision: Optional[int] = None) -> float:
        if value is None:
            return 0.0
        if isinstance(value, float):
            return value
        if ":" in value:
            num, den = value.split(':')
        elif "/" in value:
            num, den = value.split('/')
        else:
            return float(value)
        value = float(num) / float(den)
        if precision is not None:
            value = round(value, precision)
        return value

    @staticmethod
    def maybe_parse_duration(value: Union[str, None]) -> meta.TS:
        """
        Parses duration from ffprobe output, if necessary.

        FFprobe outputs duration as float seconds value.
        """
        if value is None:
            return meta.TS(0)
        return meta.TS(value)

    def from_ffprobe_data(self, **data: Any) -> List[meta.Meta]:
        streams: List[meta.Meta] = []
        for stream in data.get("streams", []):
            if stream["codec_type"] == "video":
                streams.append(self.video_meta_data(**stream))
            elif stream["codec_type"] == "audio":
                streams.append(self.audio_meta_data(**stream))
        return streams

    def audio_meta_data(self, **track: Any) -> meta.AudioMeta:
        kwargs = self.get_audio_meta_kwargs(track)
        return self.audio_meta_class(**kwargs)

    def video_meta_data(self, **track: Any) -> meta.VideoMeta:
        kwargs = self.get_video_meta_kwargs(track)
        return self.video_meta_class(**kwargs)

    def get_audio_meta_kwargs(self, track: Dict[str, Any]) -> Dict[str, Any]:
        duration = self.maybe_parse_duration(track.get('duration'))
        start = meta.TS(track.get('start_time', 0))
        scene = meta.Scene(
            stream=None,
            duration=duration,
            start=start,
            position=start,
        )
        sample_rate = int(track.get('sample_rate', 0))
        if sample_rate != 0:
            samples = round(duration * sample_rate)
        else:
            samples = 0
        return dict(
            scenes=[scene],
            streams=[],
            duration=duration,
            start=start,
            bitrate=int(track.get('bit_rate', 0)),
            channels=int(track.get('channels', 0)),
            sampling_rate=sample_rate,
            samples=samples,
        )

    def get_video_meta_kwargs(self, track: Dict[str, Any]) -> Dict[str, Any]:
        duration = self.maybe_parse_duration(track.get('duration'))
        width = int(track.get('width', 0))
        height = int(track.get('height', 0))
        par = self.maybe_parse_rational(track.get('sample_aspect_ratio', 1.0), precision=3)
        try:
            dar = self.maybe_parse_rational(track['display_aspect_ratio'], precision=3)
        except KeyError:
            if height == 0:
                dar = float('nan')
            else:
                dar = width / height * par
        frames = int(track.get('nb_frames', 0))
        try:
            frame_rate = self.maybe_parse_rational(track.get('r_frame_rate') or track['avg_frame_rate'])
        except KeyError:
            if duration.total_seconds() == 0:
                frame_rate = 0
            else:
                frame_rate = frames / duration.total_seconds()
        start = meta.TS(track.get('start_time', 0))
        scene = meta.Scene(
            stream=None,
            duration=duration,
            start=start,
            position=start,
        )
        return dict(
            scenes=[scene],
            streams=[],
            duration=duration,
            start=start,
            bitrate=int(track.get('bit_rate', 0)),
            width=width,
            height=height,
            par=par,
            dar=dar,
            frame_rate=frame_rate,
            frames=frames,
            device=None,
        )
