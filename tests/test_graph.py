from unittest import TestCase

from fffw.graph import *
from fffw.graph import base, sources


class FilterGraphTestCase(TestCase):

    def test_filter_graph(self):
        """ Filter complex smoke test and features demo.

        [I-1/Logo]---<Scale>-------
                                  |
        [I-0/input]--<Deint>--<Overlay>--<Split>--<Scale>--[O/480p]
                                            |
                                            ------<Scale>--[O/720p]
        """

        inputs = 2  # number of input files - logo + video

        video_streams = [base.Source("%i:v" % i, VIDEO) for i in range(inputs)]
        audio_streams = [base.Source("0:a", AUDIO)]

        fc = FilterComplex(video=sources.Input(video_streams, VIDEO),
                           audio=sources.Input(audio_streams, AUDIO))

        deint = Deint(enabled=False)  # deinterlace is disabled

        # first video stream is deinterlaced
        next_node = fc.video | deint

        left, top = 20, 20  # logo position

        # first overlay input is deinterlaced source (or source itself as
        # deint filter is disabled)
        over = next_node | Overlay(left, top)

        logo_width, logo_height = 200, 50  # logo scaled

        # second input stream is connected to logo scaler, followed by overlay
        # filter
        next_node = fc.video | Scale(logo_width, logo_height) | over

        # audio is split to two streams
        asplit = fc.audio | AudioSplit(2)

        for i in range(2):
            asplit.connect_dest(fc.get_audio_dest(i))

        # video split to two steams

        # connect split filter to overlayed video stream
        split = next_node | Split(2)

        # intermediate video stream scaling
        sizes = [(640, 480), (1280, 720)]

        for i, size in enumerate(sizes):
            # add scale filters to video streams
            w, h = size
            scale = Scale(w, h, enabled=True)
            # connect scaled streams to video destinations
            split | scale | fc.get_video_dest(i)

        result = fc.render()

        expected = ';'.join([
            # overlay logo
            '[0:v][v:scale0]overlay=x=20:y=20[v:overlay0]',
            # split video to two streams
            '[v:overlay0]split[v:split0][v:split1]',
            # each video is scaled to own size
            '[v:split0]scale=640x480[vout0]',
            '[v:split1]scale=1280x720[vout1]',

            # logo scaling
            '[1:v]scale=200x50[v:scale0]',

            # split audio to two streams
            '[0:a]asplit[aout0][aout1]'
        ])

        self.assertEqual(expected.replace(';', ';\n'),
                         result.replace(';', ';\n'))

    def test_disabled_filters(self):
        """ Filter skipping."""
        fc = FilterComplex(video=sources.Input(
            [base.Source("0:v", VIDEO)], VIDEO))

        dest = fc.get_video_dest(0)
        fc.video | Scale(640, 360) | Deint(enabled=False) | dest
        self.assertEqual(fc.render(), '[0:v]scale=640x360[vout0]')

        fc = FilterComplex(video=sources.Input(
            [base.Source("0:v", VIDEO)], VIDEO))

        dest = fc.get_video_dest(0)
        fc.video | Deint(enabled=False) | Scale(640, 360) | dest
        self.assertEqual(fc.render(), '[0:v]scale=640x360[vout0]')

        fc = FilterComplex(video=sources.Input(
            [base.Source("0:v", VIDEO)], VIDEO))
        dest = fc.get_video_dest(0)
        tmp = fc.video | Deint(enabled=False)
        tmp = tmp | Deint(enabled=False)
        tmp | Scale(640, 360) | dest
        self.assertEqual(fc.render(), '[0:v]scale=640x360[vout0]')

        fc = FilterComplex(video=sources.Input(
            [base.Source("0:v", VIDEO)], VIDEO))
        dest = fc.get_video_dest(0)
        tmp = fc.video | Scale(640, 360)
        tmp = tmp | Deint(enabled=False)
        tmp | Deint(enabled=False) | dest
        self.assertEqual(fc.render(), '[0:v]scale=640x360[vout0]')

    def test_skip_not_connected_sources(self):
        """ Skip unused sources in filter complex.
        """
        fc = FilterComplex(
            video=sources.Input(
                [base.Source("0:v", VIDEO)], VIDEO),
            audio=sources.Input(
                [base.Source("0:a", AUDIO)], AUDIO))
        dest = fc.get_video_dest(0)
        fc.video | Scale(640, 360) | dest

        self.assertEqual(fc.render(), '[0:v]scale=640x360[vout0]')
