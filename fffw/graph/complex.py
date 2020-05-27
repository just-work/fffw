import collections
from typing import Dict

from fffw.graph import base, inputs

__all__ = [
    'FilterComplex'
]


class FilterComplex:
    """ ffmpeg filter graph wrapper."""

    def __init__(self, input_list: inputs.InputList):
        """
        :param input_list: list of input files, containing video and audio
        streams.
        """
        self.__input_list = input_list
        self.__video_outputs: Dict[int, base.Dest] = {}
        self.__audio_outputs: Dict[int, base.Dest] = {}

    @property
    def video(self) -> base.Source:
        """ Returns first free video stream."""
        return self.get_free_source(base.VIDEO)

    @property
    def audio(self) -> base.Source:
        """ Returns first free audio stream."""
        return self.get_free_source(base.AUDIO)

    def get_free_source(self, kind: base.StreamType) -> base.Source:
        """
        :param kind: stream type
        :return: first stream of this kind not connected to filter graph
        """
        for stream in self.__input_list.streams:
            if stream.kind != kind or stream.edge is not None:
                continue
            return stream
        else:
            raise RuntimeError("No free streams")

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
            for src in self.__input_list.streams:
                result.extend(src.render(partial=partial))

        # There are no visit checks in recurse graph traversing, so remove
        # duplicates respecting order of appearance.
        return ';'.join(collections.OrderedDict.fromkeys(result))

    def __str__(self) -> str:
        return self.render()
