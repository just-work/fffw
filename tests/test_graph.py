from unittest import TestCase

from fffw.graph import *


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
        out0 = Output('out0.mp4', Codec(VIDEO, 'v'), Codec(AUDIO, 'a'))
        out1 = Output('out1.mp4', Codec(VIDEO, 'v'), Codec(AUDIO, 'a'))
        ol = OutputList(out0, out1)

        fc = FilterComplex(il, ol)

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

        for out in ol.outputs:
            asplit.connect_dest(out.codecs[1])

        # video split to two steams

        # connect split filter to overlayed video stream
        split = next_node | Split(2)

        # intermediate video stream scaling
        sizes = [(640, 480), (1280, 720)]

        for out, size in zip(ol.outputs, sizes):
            # add scale filters to video streams
            w, h = size
            scale = Scale(w, h, enabled=True)
            # connect scaled streams to video destinations
            split | scale > out.codecs[0]

        result = fc.render()

        expected = ';'.join([
            # overlay logo
            '[0:v][v:scale0]overlay=x=20:y=20[v:overlay0]',
            # split video to two streams
            '[v:overlay0]split[v:split0][v:split1]',
            # each video is scaled to own size
            '[v:split0]scale=640x480[vout0]',
            '[v:split1]scale=1280x720[vout1]',

            # split audio to two streams
            '[0:a]asplit[aout0][aout1]',

            # logo scaling
            '[1:v]scale=200x50[v:scale0]',
        ])

        self.assertEqual(expected.replace(';', ';\n'),
                         result.replace(';', ';\n'))

    def test_disabled_filters(self):
        """ Filter skipping."""

        # noinspection PyShadowingNames
        def fc_factory():
            src = Input(Stream(VIDEO), input_file="input.mp4")
            dst = Output(
                'output.mp4', Codec(VIDEO, 'v'), Codec(AUDIO, 'a'))
            fc = FilterComplex(InputList(src), OutputList(dst))
            return fc, dst

        fc, dst = fc_factory()

        fc.video | Scale(640, 360) | Deint(enabled=False) > dst.codecs[0]
        self.assertEqual(fc.render(), '[0:v]scale=640x360[vout0]')

        fc, dst = fc_factory()

        fc.video | Deint(enabled=False) | Scale(640, 360) > dst.codecs[0]
        self.assertEqual(fc.render(), '[0:v]scale=640x360[vout0]')

        fc, dst = fc_factory()

        tmp = fc.video | Deint(enabled=False)
        tmp = tmp | Deint(enabled=False)
        tmp | Scale(640, 360) > dst.codecs[0]
        self.assertEqual(fc.render(), '[0:v]scale=640x360[vout0]')

        fc, dst = fc_factory()

        tmp = fc.video | Scale(640, 360)
        tmp = tmp | Deint(enabled=False)
        tmp | Deint(enabled=False) > dst.codecs[0]
        self.assertEqual(fc.render(), '[0:v]scale=640x360[vout0]')

    def test_skip_not_connected_sources(self):
        """ Skip unused sources in filter complex.
        """
        source = Input(input_file='input.mp4')
        output = Output('output.mp4', Codec(VIDEO, 'v'))
        il = InputList(source)
        ol = OutputList(output)
        # passing only video to FilterComplex
        fc = FilterComplex(il, ol)
        fc.video | Scale(640, 360) > output.codecs[0]

        self.assertEqual(fc.render(), '[0:v]scale=640x360[vout0]')

    def test_pass_metadata(self):
        """
        stream metadata is passed from source to destination
        """
        metadata = video_meta_data()

        source = Input(Stream(VIDEO, meta=metadata),
                       input_file='input.mp4')
        output = Output('output.mp4', Codec(VIDEO, 'v'))
        il = InputList(source)
        ol = OutputList(output)
        fc = FilterComplex(il, ol)
        dest = output.codecs[0]
        fc.video | Scale(640, 360) > dest

        self.assertIs(dest.get_meta_data(dest), metadata)
