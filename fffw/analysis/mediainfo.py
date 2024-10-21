from typing import List, Any, Union, Dict

import pymediainfo

from fffw.graph import meta


class Analyzer:
    """
    Perform mediainfo analysis and normalization to obtain media stream metadata list.

    >>> import pymediainfo
    >>> mi = pymediainfo.MediaInfo.parse('test.mp4')
    >>> streams = Analyzer().from_media_info(mi)
    """

    audio_meta_class = meta.AudioMeta
    video_meta_class = meta.VideoMeta

    def from_media_info(self, mi: pymediainfo.MediaInfo) -> List[meta.Meta]:
        """
        Normalizes stream info from LibMediaInfo into internal stream metadata representation
        :param mi: media info
        :return: list of media stream metadata
        """
        streams: List[meta.Meta] = []
        for track in mi.tracks:
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

    def audio_meta_data(self, **track: Any) -> meta.AudioMeta:
        kwargs = self.get_audio_meta_kwargs(track)
        return self.audio_meta_class(**kwargs)

    def get_audio_meta_kwargs(self, track: Dict[str, Any]) -> Dict[str, Any]:
        duration = self.maybe_parse_duration(track.get('duration'))
        start = meta.TS(track.get('start', 0))
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
            channels=int(track.get('channel_s', 0)),
            sampling_rate=int(track.get('sampling_rate', 0)),
            samples=int(track.get('samples_count', 0)),
        )

    def video_meta_data(self, **track: Any) -> meta.VideoMeta:
        kwargs = self.get_video_meta_kwargs(track)
        return self.video_meta_class(**kwargs)

    def get_video_meta_kwargs(self, track: Dict[str, Any]) -> Dict[str, Any]:
        duration = self.maybe_parse_duration(track.get('duration'))
        width = int(track.get('width', 0))
        height = int(track.get('height', 0))
        par = float(track.get('pixel_aspect_ratio', 1.0))
        try:
            dar = float(track['display_aspect_ratio'])
        except KeyError:
            if height == 0:
                dar = float('nan')
            else:
                dar = width / height * par
        frames = int(track.get('frame_count', 0))
        try:
            frame_rate = float(track['frame_rate'])
        except KeyError:
            if duration.total_seconds() == 0:
                frame_rate = 0
            else:
                frame_rate = frames / duration.total_seconds()
        start = meta.TS(track.get('start', 0))
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
