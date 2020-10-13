from dataclasses import dataclass

from fffw.encoding import *
from fffw.wrapper import param


class ScaleVAAPI(Scale):
    filter = "scale_vaapi"
    hardware = "vaapi"


# initialize ffmpeg wrapper with common flags and VAAPI device (works on
# GPU-enabled Intel CPU)
ff = FFMPEG(overwrite=True, loglevel='level+info',
            init_hardware='vaapi=foo:/dev/dri/renderD128',
            filter_hardware='foo')

vaapi = ff.filter_device

# add an input file
ff < input_file('input.mp4',
                hardware='vaapi',
                device='foo',
                duration=5.0)

# change video pixel format and upload it to Intel GPU
hw_stream = ff.video | Format('nv12') | Upload(device=vaapi)
# scale video stream
scale = hw_stream | ScaleVAAPI(width=1280, height=720)

# initialize an output file
output = output_file('output.mp4',
                     # Use HW-accelerated video codec
                     VideoCodec('h264_vaapi'),
                     AudioCodec('aac'))

# point scaled video stream to output file
scale > output

# tell ffmpeg about output file
ff > output

# check what we've configured
print(ff.get_cmd())

# run it
return_code, output, errors = ff.run()
if return_code != 0:
    print(output, errors)
