from typing import List, Any, Union, Dict

import pymediainfo  # type: ignore

from fffw.analysis import base
from fffw.graph import meta


class Analyzer(base.Analyzer):
    """
    Perform mediainfo analysis and normalization to obtain media stream metadata list.

    >>> import pymediainfo
    >>> mi = pymediainfo.MediaInfo.parse('test.mp4')
    >>> streams = Analyzer(mi).analyze()
    """

    def __init__(self, info: pymediainfo.MediaInfo):
        self.info = info

    def analyze(self) -> List[meta.Meta]:
        """
        Normalizes stream info from LibMediaInfo into internal stream metadata representation
        :return: list of media stream metadata
        """
        streams: List[meta.Meta] = []
        for track in self.info.tracks:
            if track.track_type in ('Video', 'Image'):
                streams.append(self.video_meta_data(**track.__dict__))
            elif track.track_type == 'Audio':
                streams.append(self.audio_meta_data(**track.__dict__))
        return streams

    @staticmethod
    def maybe_parse_duration(value: Union[str, float, int, None]) -> meta.TS:
        """
        Parses duration from mediainfo output, if necessary.

        Some containers store float value and some int, but in both cases (which is different from ffmpeg) value is
        counted in milliseconds.
        """
        if value is None:
            return meta.TS(0)
        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError:
                # prepare seconds for TS constructor
                value = float(value) / 1000
        return meta.TS(value)

    def get_duration(self, track: Dict[str, Any]) -> meta.TS:
        return self.maybe_parse_duration(track.get('duration'))

    def get_start(self, track: Dict[str, Any]) -> meta.TS:
        return self.maybe_parse_duration(track.get('delay'))

    def get_bitrate(self, track: Dict[str, Any]) -> int:
        return int(track.get('bit_rate', 0))

    def get_channels(self, track: Dict[str, Any]) -> int:
        return int(track.get('channel_s', 0))

    def get_sampling_rate(self, track: Dict[str, Any]) -> int:
        return int(track.get('sampling_rate', 0))

    def get_samples(self, track: Dict[str, Any]) -> int:
        return int(track.get('samples_count', 0))

    def get_par(self, track: Dict[str, Any]) -> float:
        return float(track.get('pixel_aspect_ratio', 1.0))

    def get_dar(self, track: Dict[str, Any]) -> float:
        par = self.get_par(track)
        width = self.get_width(track)
        height = self.get_height(track)
        try:
            dar = float(track['display_aspect_ratio'])
        except KeyError:
            if height == 0:
                dar = float('nan')
            else:
                dar = width / height * par
        return dar

    def get_frame_rate(self, track: Dict[str, Any]) -> float:
        duration = self.get_video_duration(track).total_seconds()
        frames = self.get_frames(track)
        try:
            frame_rate = float(track['frame_rate'])
        except KeyError:
            if duration == 0:
                frame_rate = 0
            else:
                frame_rate = frames / duration
        return frame_rate

    def get_frames(self, track: Dict[str, Any]) -> int:
        return int(track.get('frame_count', 0))
