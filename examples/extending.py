from dataclasses import dataclass
from fffw import encoding
from fffw.wrapper import param


@dataclass
class FFMPEG(encoding.FFMPEG):
    no_banner: bool = param(default=False, name='hide_banner')
