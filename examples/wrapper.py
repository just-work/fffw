from dataclasses import dataclass

from fffw.wrapper import BaseWrapper, param


@dataclass
class MediaInfo(BaseWrapper):
    command = 'mediainfo'
    input_file: str = param(name='')

    def handle_stderr(self, line: str) -> str:
        if 'error' in line:
            raise RuntimeError(f"Mediainfo error: {line}")
        return super().handle_stderr(line)


mi = MediaInfo(input_file='input.mp4')

return_code, output, errors = mi.run()
if return_code != 0:
    raise RuntimeError(output, errors)
