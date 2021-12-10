from fffw.encoding import *
from fffw.graph import VIDEO, AUDIO

ff = FFMPEG(input=input_file('input.mp4', fast_seek=8.8, duration=15.766 - 8.8))

vc1 = VideoCodec('libx264', bitrate=4_000_000)
vst = ff.video
vst | Scale(1920, 1080) > vc1
vc2 = Copy(kind=VIDEO)
vst > vc2

ast = ff.audio

ac1 = AudioCodec('libfdk_aac', bitrate=128_000)
ast > ac1
ac2 = Copy(kind=AUDIO)
ast > ac2

ff > output_file('process.mp4', vc1, ac1)
ff > output_file('copy.mp4', vc2, ac2)

print(ff.get_cmd())