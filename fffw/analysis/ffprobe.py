import json
from dataclasses import dataclass
from typing import List, Dict, Any, Union, Optional, Iterable

from fffw.analysis import base
from fffw.graph import meta
from fffw.encoding import ffprobe


@dataclass
class ProbeInfo:
    streams: Iterable[Dict[str, Any]]
    format: Dict[str, Any]


def analyze(source: str) -> ProbeInfo:
    """
    Performs source analysis with ffprobe.
    :param source: source uri
    :return: metadata loaded from json output.
    """
    ff = ffprobe.FFProbe(source, show_format=True, show_streams=True, output_format='json')
    ret, output, errors = ff.run()
    if ret != 0:
        raise RuntimeError(f"ffprobe returned {ret}")
    return ProbeInfo(**json.loads(output))


class Analyzer(base.Analyzer):
    """
    Perform ffprobe analysis and normalization to obtain media stream metadata list.

    >>> info = analyze('test.mp4')
    >>> streams = Analyzer(info).analyze()
    """

    def __init__(self, info: ProbeInfo):
        self.info = info

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

    def analyze(self) -> List[meta.Meta]:
        streams: List[meta.Meta] = []
        for stream in self.info.streams:
            if stream["codec_type"] == "video":
                streams.append(self.video_meta_data(**stream))
            elif stream["codec_type"] == "audio":
                streams.append(self.audio_meta_data(**stream))
        return streams

    def get_duration(self, track: Dict[str, Any]) -> meta.TS:
        return self.maybe_parse_duration(track.get('duration'))

    def get_start(self, track: Dict[str, Any]) -> meta.TS:
        return meta.TS(track.get('start_time', 0))

    def get_bitrate(self, track: Dict[str, Any]) -> int:
        return int(track.get('bit_rate', 0))

    def get_channels(self, track: Dict[str, Any]) -> int:
        return int(track.get('channels', 0))

    def get_sampling_rate(self, track: Dict[str, Any]) -> int:
        return int(track.get('sample_rate', 0))

    def get_samples(self, track: Dict[str, Any]) -> int:
        duration = self.get_duration(track)
        sampling_rate = self.get_sampling_rate(track)
        if sampling_rate != 0:
            samples = round(duration * sampling_rate)
        else:
            samples = 0
        return samples

    def get_par(self, track: Dict[str, Any]) -> float:
        return self.maybe_parse_rational(track.get('sample_aspect_ratio', 1.0), precision=3)

    def get_dar(self, track: Dict[str, Any]) -> float:
        par = self.get_par(track)
        width = self.get_width(track)
        height = self.get_height(track)
        try:
            dar = self.maybe_parse_rational(track['display_aspect_ratio'], precision=3)
        except KeyError:
            if height == 0:
                dar = float('nan')
            else:
                dar = width / height * par
        return dar

    def get_frame_rate(self, track: Dict[str, Any]) -> float:
        duration = self.get_duration(track)
        raw_frames = int(track.get('nb_frames', 0))
        try:
            frame_rate = self.maybe_parse_rational(track.get('r_frame_rate') or track['avg_frame_rate'])
        except KeyError:
            if duration == 0:
                frame_rate = 0
            else:
                frame_rate = raw_frames / duration.total_seconds()
        return frame_rate

    def get_frames(self, track: Dict[str, Any]) -> int:
        frames = int(track.get('nb_frames', 0))
        if frames != 0:
            return frames
        duration = self.get_duration(track)
        frame_rate = self.get_frame_rate(track)
        return round(duration * frame_rate)
