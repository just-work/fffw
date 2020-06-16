from pymediainfo import MediaInfo

from fffw.encoding import *
from fffw.graph import VIDEO, AUDIO
from fffw.graph.meta import *

# detect information about input file
mi = MediaInfo.parse('input.mp4')

# initializing streams with metadata
streams = []
for track in from_media_info(mi):
    if isinstance(track, VideoMeta):
        streams.append(Stream(VIDEO, meta=track))
    else:
        streams.append(Stream(AUDIO, meta=track))

# initialize input file
source = Input(input_file='input.mp4', streams=tuple(streams))

# if no metadata is required, just use text variant
ff = FFMPEG(input='logo.png')

# add another input to ffmpeg
ff < source
