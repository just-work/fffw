import collections

import fffw.graph.sources
from fffw.graph import base


__all__ = [
    'FilterComplex'
]


class FilterComplex:
    """ ffmpeg filter graph wrapper."""

    def __init__(self, video=None, audio=None):
        """
        """
        self.video = video or fffw.graph.sources.Input(kind=base.VIDEO)
        self.audio = audio or fffw.graph.sources.Input(kind=base.AUDIO)
        self.__video_outputs = {}
        self.__audio_outputs = {}
        self._video_tmp = collections.Counter()
        self._audio_tmp = collections.Counter()

    def get_video_dest(self, index=0, create=True):
        """ Returns video output by index.
        :param index: video output index.
        :type index: int
        :param create: create new video output flag
        :return: output video stream
        :rtype: base.Dest
        """
        try:
            return self.__video_outputs[index]
        except KeyError:
            if not create:
                raise IndexError(index)
            self.__video_outputs[index] = base.Dest(
                'vout%s' % index, base.VIDEO)
        return self.__video_outputs[index]

    def get_audio_dest(self, index=0, create=True):
        """ Returns audio output by index.
        :param index: audio output index.
        :type index: int
        :param create: create new audio output flag
        :return: output audio stream
        :rtype: base.Dest
        """
        try:
            return self.__audio_outputs[index]
        except KeyError:
            if not create:
                raise IndexError(index)
            self.__audio_outputs[index] = base.Dest(
                'aout%s' % index, base.AUDIO)
        return self.__audio_outputs[index]

    def render(self, partial=False):
        """
        Returns filter_graph description in corresponding ffmpeg param syntax.

        :rtype: str
        """
        result = []
        for src in self.video.streams:
            # noinspection PyProtectedMember
            if not src._edge:
                continue
            result.extend(src.render(self.video_naming, partial=partial))
        for src in self.audio.streams:
            # noinspection PyProtectedMember
            if not src._edge:
                continue
            result.extend(src.render(self.audio_naming, partial=partial))

        # There are no visit checks in recurse graph traversing, so remove
        # duplicates respecting order of appearance.
        return ';'.join(collections.OrderedDict.fromkeys(result))

    def __str__(self):
        return self.render()

    def video_naming(self, name='tmp'):
        """ Unique video edge identifier generator.

        :param name: prefix used in name generation.
        :type name: str
        :rtype: str
        """
        res = 'v:%s%s' % (name, self._video_tmp[name])
        self._video_tmp[name] += 1
        return res

    def audio_naming(self, name='tmp'):
        """ Unique audio edge identifier generator.

        :param name: prefix used in name generation.
        :type name: str
        :rtype: str
        """
        res = 'a:%s%s' % (name, self._audio_tmp[name])
        self._audio_tmp[name] += 1
        return res
