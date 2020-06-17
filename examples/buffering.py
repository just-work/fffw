from pymediainfo import MediaInfo

from fffw.encoding import *
from fffw.graph import *

# detect information about input file
mi = MediaInfo.parse('source.mp4')
streams = [Stream(m.kind, m) for m in from_media_info(mi)]

# initialize input file with stream and metadata
source = input_file('source.mp4', *streams)

mi = MediaInfo.parse('preroll.mp4')
# initialize input file with stream and metadata
streams = [Stream(m.kind, m) for m in from_media_info(mi)]
preroll = input_file('preroll.mp4', *streams)

ff = FFMPEG()

ff < preroll
ff < source

result = output_file('result.mp4', VideoCodec('libx264'), AudioCodec('aac'))
backup = output_file('backup.mp4', VideoCodec('libx264'), AudioCodec('aac'))

split = source | Split(VIDEO)
split > backup

concat = preroll | Concat(VIDEO)
split | concat
concat > result

ff > result
ff > backup

ff.check_buffering()
