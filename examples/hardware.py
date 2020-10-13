from pymediainfo import MediaInfo

from fffw.encoding import *
from fffw.graph import from_media_info


class ScaleVAAPI(Scale):
    filter = "scale_vaapi"
    hardware = 'vaapi'


class H264Vaapi(VideoCodec):
    codec = 'h264_vaapi'
    hardware = 'vaapi'


# initialize ffmpeg wrapper with common flags and VAAPI device (works on
# GPU-enabled Intel CPU)
ff = FFMPEG(overwrite=True, loglevel='level+info',
            init_hardware='vaapi=foo:/dev/dri/renderD128',
            filter_hardware='foo')

vaapi = ff.filter_device

# detect information about input file
mi = MediaInfo.parse('input.mp4')
streams = [Stream(m.kind, m) for m in from_media_info(mi)]

# add an input file (video is decoded by VAAPI and placed on Intel GPU)
ff < input_file('input.mp4', *streams,
                hardware='vaapi',
                device='foo',
                output_format='vaapi',
                duration=5.0)

# scale video stream
scale = ff.video | ScaleVAAPI(width=1280, height=720)

# initialize an output file
output = output_file('output.mp4',
                     # Use HW-accelerated video codec
                     H264Vaapi(),
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
