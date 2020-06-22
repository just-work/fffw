from fffw.encoding import *
from fffw.graph import VIDEO

ff = FFMPEG(input='input.mp4')

split = ff.video | Split(VIDEO, output_count=4)

# define video codecs
vc1 = VideoCodec('libx264', bitrate=4_000_000)
split | Scale(1920, 1080) > vc1
vc2 = VideoCodec('libx264', bitrate=2_000_000)
split | Scale(1280, 720) > vc2
vc3 = VideoCodec('libx264', bitrate=1_000_000)
split | Scale(960, 480) > vc3
vc4 = VideoCodec('libx264', bitrate=500_000)
split | Scale(640, 360) > vc4

# add an audio codec for each quality
ac1, ac2, ac3, ac4 = [AudioCodec('aac') for _ in range(4)]

# tell ffmpeg to take single audio stream and encode
# it 4 times for each output
audio_stream = ff.audio
audio_stream > ac1
audio_stream > ac2
audio_stream > ac3
audio_stream > ac4

# define outputs as a filename with codec set
ff > output_file('full_hd.mp4', vc1, ac1)
ff > output_file('hd.mp4', vc2, ac2)
ff > output_file('middle.mp4', vc3, ac3)
ff > output_file('low.mp4', vc4, ac4)
