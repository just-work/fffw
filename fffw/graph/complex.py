# coding: utf-8

# $Id: $
import collections

from fffw.graph import base


__all__ = [
    'FilterComplex'
]


class FilterComplex(object):
    """ Описание графов конвертации для ffmpeg."""

    def __init__(self, outputs=1, audio_outputs=None,
                 inputs=1, audio_inputs=None):
        """
        :param outputs: Число выходных видео потоков (по-умолчанию 1)
        :type outputs: int
        :param audio_outputs: Число выходных аудио потоков (по-уполчанию равно
        числу выходных видео-потоков)
        :type audio_outputs: int
        :param inputs: Число входных видео потоков (по-умолчанию 1)
        :type inputs: int
        :param audio_inputs: Число входных аудио потоков (по-уполчанию равно
        числу входных видео-потоков)
        :type audio_inputs: int
        """
        if audio_inputs is None:
            audio_inputs = inputs
        if audio_outputs is None:
            audio_outputs = outputs

        self.video = base.Input([base.Source('%s:v' % i, base.VIDEO)
                                for i in range(inputs)], base.VIDEO)
        self.audio = base.Input([base.Source('%s:a' % i, base.AUDIO)
                                for i in range(audio_inputs)], base.AUDIO)
        self.video_outputs = [base.Dest('vout%s' % i, base.VIDEO)
                              for i in range(outputs)]
        self.audio_outputs = [base.Dest('aout%s' % i, base.AUDIO)
                              for i in range(audio_outputs)]
        self._video_tmp = None
        self._audio_tmp = None

    def get_video_dest(self, index=0):
        """ Возвращает выходной видеопоток по индексу.
        :param index: номер видеопотока.
        :type index: int
        :return: выходной видеопоток
        :rtype: base.Dest
        """
        return self.video_outputs[index]

    def get_audio_dest(self, index=0):
        """ Возвращает выходной аудиопоток по индексу.
        :param index: номер аудиопотока.
        :type index: int
        :return: выходной аудиопоток
        :rtype: base.Dest
        """
        return self.audio_outputs[index]

    def render(self):
        """ Возвращает описание filter_graph в форме, понятной ffmpeg.

        :rtype: str
        """
        result = []
        self._video_tmp = collections.Counter()
        self._audio_tmp = collections.Counter()
        for src in self.video.streams:
            result.extend(src.render(self.video_naming))
        for src in self.audio.streams:
            result.extend(src.render(self.audio_naming))

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
