from dataclasses import dataclass

from fffw.encoding import *
from fffw.graph import VIDEO
from fffw.wrapper import param


@dataclass
class Scale2Ref(VideoFilter):
    """
    Filter that scales one stream to fit another one.
    """
    # define filter name
    filter = 'scale2ref'
    # configure input and output edges count
    input_count = 2
    output_count = 2

    # add some parameters that compute dimensions
    # based on input stream characteristics
    width: str = param(name='w')
    height: str = param(name='h')


ff = FFMPEG()

ff < input_file('preroll.mp4')
ff < input_file('input.mp4')

# don't know what that formulas mean, it's from ffmpeg docs
scale2ref = ff.video | Scale2Ref('oh*mdar', 'ih/10')
# pass second file to same filter as second input
ff.video | scale2ref

output = output_file('output.mp4')
# concatenate scaled preroll and main video
concat = scale2ref | Concat(VIDEO)
scale2ref | concat > output

ff > output

print(ff.get_cmd())
