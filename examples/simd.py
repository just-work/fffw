from pymediainfo import MediaInfo

from fffw.encoding import *
from fffw.encoding.vector import SIMD, Vector
from fffw.graph import *

# detect information about input file
mi = MediaInfo.parse('source.mp4')
video_meta, audio_meta = from_media_info(mi)

# initialize input file with stream and metadata
source = input_file('source.mp4',
                    Stream(VIDEO, video_meta),
                    Stream(AUDIO, audio_meta))

outputs = []
for size in 360, 540, 720, 1080:
    out = output_file(f'{size}.mp4',
                      VideoCodec('libx264'),
                      AudioCodec('aac'))
    outputs.append(out)

simd = SIMD(source, *outputs)

mi = MediaInfo.parse('logo.png')
logo_meta, = from_media_info(mi)

# add a logo
logo = input_file('logo.png', Stream(VIDEO, logo_meta))

simd < logo

trim = [
    {'kind': VIDEO, 'start': 25, 'end': 50},
    {'kind': VIDEO, 'start': 160, 'end': 240},
    {'kind': VIDEO, 'start': 330, 'end': 820},
]

# cut three parts from input video stream and
# reset timestamps for it
edited = simd.video.connect(Trim, params=trim) | SetPTS(VIDEO)

# concatenate all vector elements to a single stream
concat = Concat(VIDEO, input_count=len(edited))
for stream in edited:
    stream | concat

# cut same parts from input audio stream
for p in trim:
    p['kind'] = AUDIO

audio = simd.audio.connect(Trim, params=trim) | SetPTS(AUDIO)

audio_concat = Concat(AUDIO, input_count=len(audio))
for stream in audio:
    stream | audio_concat

# add a logo to an edited video stream
with_logo = concat | Overlay(x=100, y=100)
logo.streams[0] | with_logo

# now we need to vectorize video stream again to perform
# scaling to multiple sizes
cursor = Vector(with_logo)

sizes = [(640, 360), (960, 540), (1280, 720), (1920, 1080)]
cursor = cursor.connect(Scale, params=sizes)

# finalize video processing
cursor > simd

# finalize audio processing
Vector(audio_concat) > simd

simd.ffmpeg.overwrite = True

print(simd.ffmpeg.get_cmd())
