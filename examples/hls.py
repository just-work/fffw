from dataclasses import dataclass

from fffw.encoding import *
from fffw.wrapper import param


@dataclass
class HLS(Output):
    """
    m3u8 muxer
    """
    format: str = param(name='f', init=False, default='hls')
    # Add empty `param()` call to prevent
    # "Non-default argument(s) follows default argument(s)"
    # dataclass error.
    hls_init_time: int = param()
    hls_base_url: str = param()
    hls_segment_filename: str = 'file%03d.ts'


ff = FFMPEG(input='input.mp4')

base_url = 'https://my.video.streaming.server.ru/my-playlist/'
ff > HLS(hls_base_url=base_url,
         output_file='out.m3u8',
         codecs=[VideoCodec('libx264'), AudioCodec('aac')])

print(ff.get_cmd())
