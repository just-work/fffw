import json
from dataclasses import dataclass
from typing import Any, Dict, List

from fffw.wrapper import BaseWrapper, param

__all__ = ['FFProbe', 'analyze']


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


def analyze(source: str) -> List[Dict[str, Any]]:
    """
    Performs source analysis with ffprobe.
    :param source: source uri
    :return: list of stream metadata from ffprobe output
    """
    ff = FFProbe(source, show_streams=True, output_format='json')
    ret, output, errors = ff.run()
    if ret != 0:
        raise RuntimeError(f"ffprobe returned {ret}")
    return json.loads(output).get("streams", [])
