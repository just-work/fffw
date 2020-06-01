from dataclasses import field
from typing import Any

from fffw.graph import base, outputs


__all__ = [
    'AudioCodec',
    'VideoCodec',
    'codec_name',
]


class VideoCodec(outputs.Codec):
    kind = base.VIDEO


class AudioCodec(outputs.Codec):
    kind = base.AUDIO


def codec_name(name: str) -> Any:
    metadata = {
        'name': 'c',
        'stream_suffix': True,
    }
    return field(default=name, init=False, metadata=metadata)
