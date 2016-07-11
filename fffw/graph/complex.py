# coding: utf-8

# $Id: $
import collections

from fffw.graph import base


__all__ = [
    'FilterComplex'
]


class FilterComplex(object):
    """ Описание графов конвертации для ffmpeg."""

    def __init__(self, video=None, audio=None):
        """
        """
        self.video = video or base.Input(kind=base.VIDEO)
        self.audio = audio or base.Input(kind=base.AUDIO)
        self.__video_outputs = {}
        self.__audio_outputs = {}
        self._video_tmp = collections.Counter()
        self._audio_tmp = collections.Counter()

    def get_video_dest(self, index=0, create=True):
        """ Возвращает выходной видеопоток по индексу.
        :param index: номер видеопотока.
        :type index: int
        :return: выходной видеопоток
        :rtype: base.Dest
        """
        try:
            return self.__video_outputs[index]
        except KeyError:
            if not create:
                raise IndexError(index)
            self.__video_outputs[index] = base.Dest('vout%s' % index, base.VIDEO)
        return self.__video_outputs[index]

    def get_audio_dest(self, index=0, create=True):
        """ Возвращает выходной аудиопоток по индексу.
        :param index: номер аудиопотока.
        :type index: int
        :return: выходной аудиопоток
        :rtype: base.Dest
        """
        try:
            return self.__audio_outputs[index]
        except KeyError:
            if not create:
                raise IndexError(index)
            self.__audio_outputs[index] = base.Dest('aout%s' % index, base.AUDIO)
        return self.__audio_outputs[index]

    def render(self, partial=False):
        """ Возвращает описание filter_graph в форме, понятной ffmpeg.

        :rtype: str
        """
        result = []
        for src in self.video.streams:
            if not src._edge:
                continue
            result.extend(src.render(self.video_naming, partial=partial))
        for src in self.audio.streams:
            if not src._edge:
                continue
            result.extend(src.render(self.audio_naming, partial=partial))

        # При рекурсивном обходе графа не производится проверка посещений на
        # лету, поэтому перед конкатенацией удаляем дубликаты (с учетом порядка)
        return ';'.join(collections.OrderedDict.fromkeys(result))

    def __str__(self):
        return self.render()

    def video_naming(self, name='tmp'):
        """ Функция, генерирующая уникальные идентификаторы ребер графа.

        :param name: префикс, используемый в идентификаторе
        :type name: str
        :rtype: str
        """
        res = 'v:%s%s' % (name, self._video_tmp[name])
        self._video_tmp[name] += 1
        return res

    def audio_naming(self, name='tmp'):
        """ Функция, генерирующая уникальные идентификаторы ребер графа.

        :param name: префикс, используемый в идентификаторе
        :type name: str
        :rtype: str
        """
        res = 'a:%s%s' % (name, self._audio_tmp[name])
        self._audio_tmp[name] += 1
        return res
