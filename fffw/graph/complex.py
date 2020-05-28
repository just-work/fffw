import collections
from typing import Optional, Dict

from fffw.graph import base, sources

__all__ = [
    'FilterComplex'
]


class FilterComplex:
    """ ffmpeg filter graph wrapper."""

    def __init__(self, video: Optional[sources.Input] = None,
                 audio: Optional[sources.Input] = None):
        """
        :param video: input video streams set
        :param audio: input audio streams set
        """
        self.video = video or sources.Input(kind=base.VIDEO)
        self.audio = audio or sources.Input(kind=base.AUDIO)
        self.__video_outputs: Dict[int, base.Dest] = {}
        self.__audio_outputs: Dict[int, base.Dest] = {}

    def get_video_dest(self, index: int = 0, create: bool = True) -> base.Dest:
        """ Returns video output by index.
        :param index: video output index.
        :param create: create new video output flag
        :return: output video stream
        """
        try:
            return self.__video_outputs[index]
        except KeyError:
            if not create:
                raise IndexError(index)
            self.__video_outputs[index] = base.Dest(
                'vout%s' % index, base.VIDEO)
        return self.__video_outputs[index]

    def get_audio_dest(self, index: int = 0, create: bool = True) -> base.Dest:
        """ Returns audio output by index.
        :param index: audio output index.
        :param create: create new audio output flag
        :return: output audio stream
        """
        try:
            return self.__audio_outputs[index]
        except KeyError:
            if not create:
                raise IndexError(index)
            self.__audio_outputs[index] = base.Dest(
                'aout%s' % index, base.AUDIO)
        return self.__audio_outputs[index]

    def render(self, partial: bool = False) -> str:
        """
        Returns filter_graph description in corresponding ffmpeg param syntax.
        """
        result = []
        with base.Namer():
            # Initialize namer context to track unique edge identifiers.
            # In name generation there is no access to namer, so it is accessed
            # via Namer singleton's method. Within context it is guaranteed that
            # same edges will receive same names and different edges will
            # receive unique names. This includes idempotent results for
            # subsequent render() calls for outer Namer context.
            for src in self.video.streams:
                # noinspection PyProtectedMember
                if not src._edge:
                    continue
                result.extend(src.render(partial=partial))
            for src in self.audio.streams:
                # noinspection PyProtectedMember
                if not src._edge:
                    continue
                result.extend(src.render(partial=partial))

        # There are no visit checks in recurse graph traversing, so remove
        # duplicates respecting order of appearance.
        return ';'.join(collections.OrderedDict.fromkeys(result))

    def __str__(self) -> str:
        return self.render()
