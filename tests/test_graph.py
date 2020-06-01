from dataclasses import dataclass
from unittest import TestCase

from fffw.encoding.filters import *
from fffw.graph import *
from fffw.graph import VIDEO


@dataclass
class Deint(Filter):
    kind = VIDEO
    filter = 'yadif'
    mode: str = '0'

    @property
    def args(self) -> str:
        return "%s" % self.mode


class FilterGraphTestCase(TestCase):

    def test_filter_graph(self):
        """ Filter complex smoke test and features demo.

        [I-1/Logo]---<Scale>-------
                                  |
        [I-0/input]--<Deint>--<Overlay>--<Split>--<Scale>--[O/480p]
                                            |
                                            ------<Scale>--[O/720p]
        """
        logo = Input(Stream(VIDEO), input_file='logo.png')
        main = Input(input_file='main.mp4')
        il = InputList(main, logo)
        out0 = Output('out0.mp4')
        out1 = Output('out1.mp4')
        ol = OutputList(out0, out1)

        fc = FilterComplex(il, ol)

        deint = Deint()
        deint.enabled = False  # deinterlace is skipped

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
        asplit = fc.audio | Split(AUDIO)

        for out in ol.outputs:
            asplit > out

        # video split to two steams

        # connect split filter to overlayed video stream
        split = next_node | Split(VIDEO)

        # intermediate video stream scaling
        sizes = [(640, 480), (1280, 720)]

        for out, size in zip(ol.outputs, sizes):
            # add scale filters to video streams
            w, h = size
            scale = Scale(w, h)
            # connect scaled streams to video destinations
            split | scale > out

        result = fc.render()

        expected = ';'.join([
            # overlay logo
            '[0:v][v:scale0]overlay=x=20:y=20[v:overlay0]',
            # split video to two streams
            '[v:overlay0]split[v:split0][v:split1]',
            # each video is scaled to own size
            '[v:split0]scale=width=640:height=480[vout0]',
            '[v:split1]scale=width=1280:height=720[vout1]',

            # split audio to two streams
            '[0:a]asplit[aout0][aout1]',

            # logo scaling
            '[1:v]scale=width=200:height=50[v:scale0]',
        ])

        self.assertEqual(expected.replace(';', ';\n'),
                         result.replace(';', ';\n'))

    def test_disabled_filters(self):
        """ Filter skipping."""

        # noinspection PyShadowingNames
        def fc_factory():
            src = Input(Stream(VIDEO), input_file="input.mp4")
            dst = Output('output.mp4')
            fc = FilterComplex(InputList(src), OutputList(dst))
            return fc, dst

        def deint_factory():
            d = Deint()
            d.enabled = False
            return d

        fc, dst = fc_factory()

        fc.video | Scale(640, 360) | deint_factory() > dst.video
        self.assertEqual('[0:v]scale=width=640:height=360[vout0]', fc.render())

        fc, dst = fc_factory()

        fc.video | deint_factory() | Scale(640, 360) > dst.video
        self.assertEqual('[0:v]scale=width=640:height=360[vout0]', fc.render())

        fc, dst = fc_factory()

        tmp = fc.video | deint_factory()
        tmp = tmp | deint_factory()
        tmp | Scale(640, 360) > dst.video
        self.assertEqual('[0:v]scale=width=640:height=360[vout0]', fc.render())

        fc, dst = fc_factory()

        tmp = fc.video | Scale(640, 360)
        tmp = tmp | deint_factory()
        tmp | deint_factory() > dst.video
        self.assertEqual('[0:v]scale=width=640:height=360[vout0]', fc.render())

    def test_skip_not_connected_sources(self):
        """ Skip unused sources in filter complex.
        """
        source = Input(input_file='input.mp4')
        output = Output('output.mp4')
        il = InputList(source)
        ol = OutputList(output)
        # passing only video to FilterComplex
        fc = FilterComplex(il, ol)
        fc.video | Scale(640, 360) > output

        self.assertEqual('[0:v]scale=width=640:height=360[vout0]', fc.render())

    def test_pass_metadata(self):
        """
        stream metadata is passed from source to destination
        """
        metadata = video_meta_data()

        source = Input(Stream(VIDEO, meta=metadata),
                       input_file='input.mp4')
        output = Output('output.mp4')
        il = InputList(source)
        ol = OutputList(output)
        fc = FilterComplex(il, ol)
        dest = output.video
        fc.video | Scale(640, 360) > dest

        self.assertIs(dest.get_meta_data(dest), metadata)
