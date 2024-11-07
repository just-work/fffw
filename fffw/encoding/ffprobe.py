from dataclasses import dataclass

from fffw.wrapper import BaseWrapper, param

__all__ = ['FFProbe']


@dataclass
class FFProbe(BaseWrapper):
    """
    ffprobe command line basic wrapper.

    >>> ff = FFProbe(
    ...     '/tmp/input.mp4',
    ...     show_streams=True,
    ...     show_format=True,
    ...     output_format='json')
    >>> ff.get_cmd()
    'ffprobe -show_streams -show_format -of json -i /tmp/input.mp4'
    >>>
    """
    command = 'ffprobe'
    input: str = param(name='i')
    """ Input media uri/path."""
    loglevel: str = param()
    """ Loglevel: i.e. `level+info`."""
    show_streams: bool = param(default=False)
    show_format: bool = param(default=False)
    output_format: str = param(name='of')
    allowed_extensions: str = param()
