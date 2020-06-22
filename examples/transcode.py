from fffw.encoding import *

# initialize ffmpeg wrapper with common flags
ff = FFMPEG(overwrite=True, loglevel='level+info')

# add an input file
ff < input_file('input.mp4', duration=5.0)

# scale video stream
scale = ff.video | Scale(width=1280, height=720)

# initialize an output file
output = output_file('output.mp4',
                     VideoCodec('libx264'),
                     AudioCodec('aac'))

# point scaled video stream to output file
scale > output

# tell ffmpeg about output file
ff > output

# check what we've configured
print(ff.get_cmd())

# run it
return_code, output = ff.run()
if return_code != 0:
    print(output)
