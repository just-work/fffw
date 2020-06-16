from dataclasses import dataclass

from fffw import encoding
from fffw.encoding import *
from fffw.wrapper import param


@dataclass
class X11Grab(encoding.Input):
    """
    X-server grabbing input.
    """
    # `skip=True` removes parameter from argument list
    # (it is added manually in `encoding.Input.as_pairs`).
    # This field overwrites `default` from `encoding.Input`.
    input_file: str = param(name='i', default=':0.0', skip=True)

    # `init=False` excludes parameter from `__init__`.
    # Field is initialized with value passed in `default`
    # parameter. Exactly as in dataclasses.
    format: str = param(name='f', default='x11grab', init=False)

    size: str = param(name='video_size')
    fps: float = param(name='framerate')


ff = FFMPEG()

ff < X11Grab(fps=25, size='cif', input_file=':0.0+10,20')

# As Output is not initialized with any video codec,
# force excluding `-vn` flag.
ff > output_file('out.mpg', no_video=False)

print(ff.get_cmd())
