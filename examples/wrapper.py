from dataclasses import dataclass
from typing import List

from fffw.wrapper import BaseWrapper, param, ensure_binary


@dataclass
class MediaInfo(BaseWrapper):
    command = 'mediainfo'
    input_file: str = param(name='')

    def handle_stderr(self, line: str) -> str:
        if 'error' in line:
            raise RuntimeError(f"Mediainfo error: {line}")
        return super().handle_stderr(line)

    def get_args(self) -> List[bytes]:
        return ensure_binary([self.command] + super().get_args())


mi = MediaInfo(input_file='input.mp4')

return_code, output = mi.run()
if return_code != 0:
    raise RuntimeError(output)
