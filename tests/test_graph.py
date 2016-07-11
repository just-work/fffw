# coding: utf-8

# $Id: $
from unittest import TestCase
from fffw.graph import FilterComplex, filters
from fffw.graph.base import Input, VIDEO, AUDIO
from fffw.graph.base import Source


class FilterGraphTestCase(TestCase):

    def testFilterGraph(self):
        """ Большой тест на работоспособность и как пример использования.

        [I-1/Logo]---<Scale>-------
                                  |
        [I-0/input]--<Deint>--<Overlay>--<Split>--<Scale>--[O/480p]
                                            |
                                            ------<Scale>--[O/720p]
        """

        inputs = 2  # число входных файлов - лого + видео

        video_streams = [Source("%i:v" % i, VIDEO) for i in range(inputs)]
        audio_streams = [Source("0:a", AUDIO)]

        fc = FilterComplex(video=Input(video_streams, VIDEO),
                           audio=Input(audio_streams, AUDIO))

        deint = filters.Deint(enabled=True)  # можно отключить, если не нужен

        # первый видеопоток идет в деинтерлейсинг
        next_node = fc.video | deint

        left, top = 20, 20  # лого будет в левом верхнем углу

        # прокидываем в overlay либо первый источник, либо его
        # deinterlaced - вариант
        over = next_node | filters.Overlay(left, top)

        logo_width, logo_height = 200, 50  # размер лого подогнан под размер
        # исходника видео

        # второй поток идет в масштабировине логотипа, а затем вторым
        # входом в overlay
        next_node = fc.video | filters.Scale(logo_width, logo_height) | over

        # разбираемся с аудио
        asplit = fc.audio | filters.AudioSplit(2)

        for i in range(2):
            asplit.connect_dest(fc.get_audio_dest(i))

        # делим видео на потоки; если выходной поток всего один, то вставляем
        # заглушку

        # подключаем split к предыдущей вершине
        split = next_node | filters.Split(2)

        # готовим почву для добавления масштабирования в промежуточные
        # видеопотоки
        sizes = [(640, 480), (1280, 720)]

        for i, size in enumerate(sizes):
            # готовим фильтр масштабирования; если масштабирование не задано,
            # генерируем заглушку
            w, h = size or (0, 0)
            scale = filters.Scale(w, h, enabled=size)
            # связываем потоки из фильтра split с выходными потоками через
            # фильтр масштабирования
            split | scale | fc.get_video_dest(i)

        result = fc.render()

        expected = ';'.join([
            # деинтерлейс
            '[0:v]yadif=0[v:yadif0]',
            # наложение лого
            '[v:yadif0][v:overlay0]overlay=x=20:y=20[v:overlay1]',
            # копирование видео в 2 потока
            '[v:overlay1]split[v:split0][v:split1]',
            # каждый поток масштабируется к своему размеру
            '[v:split0]scale=640x480[vout0]',
            '[v:split1]scale=1280x720[vout1]',

            # масштабирование логотипа
            '[1:v]scale=200x50[v:overlay0]',

            # копирование аудио в 2 потока
            '[0:a]asplit[aout0][aout1]'
        ])

        self.assertEqual(result, expected)

    def testDisableFilter(self):
        """Проверяет возможность выключения любого фильтра."""
        fc = FilterComplex(video=Input([Source("0:v", VIDEO)], VIDEO))

        dest = fc.get_video_dest(0)
        fc.video | filters.Scale(640, 360) | filters.Deint(enabled=False) | dest
        self.assertEqual(fc.render(), '[0:v]scale=640x360[vout0]')

        fc = FilterComplex(video=Input([Source("0:v", VIDEO)], VIDEO))

        dest = fc.get_video_dest(0)
        fc.video | filters.Deint(enabled=False) | filters.Scale(640, 360) | dest
        self.assertEqual(fc.render(), '[0:v]scale=640x360[vout0]')

        fc = FilterComplex(video=Input([Source("0:v", VIDEO)], VIDEO))
        dest = fc.get_video_dest(0)
        tmp = fc.video | filters.Deint(enabled=False)
        tmp = tmp | filters.Deint(enabled=False)
        tmp | filters.Scale(640, 360) | dest
        self.assertEqual(fc.render(), '[0:v]scale=640x360[vout0]')

        fc = FilterComplex(video=Input([Source("0:v", VIDEO)], VIDEO))
        dest = fc.get_video_dest(0)
        tmp = fc.video | filters.Scale(640, 360)
        tmp = tmp | filters.Deint(enabled=False)
        tmp | filters.Deint(enabled=False) | dest
        self.assertEqual(fc.render(), '[0:v]scale=640x360[vout0]')

    def testDontUseNotConnectedSrc(self):
        """ Проверяет возможность инициализировать, но не использовать
        исходный поток.
        """
        fc = FilterComplex(video=Input([Source("0:v", VIDEO)], VIDEO),
                           audio=Input([Source("0:a", AUDIO)], AUDIO))
        dest = fc.get_video_dest(0)
        fc.video | filters.Scale(640, 360) | dest

        self.assertEqual(fc.render(), '[0:v]scale=640x360[vout0]')
