from dataclasses import dataclass
from typing import List, Optional, Literal, Any, TypeVar, Type, Union

from fffw.graph import base
from fffw.graph.complex import FilterComplex
from fffw.graph.inputs import InputList, Input
from fffw.graph.outputs import OutputList, Output, Codec
from fffw.wrapper import BaseWrapper, ensure_binary, param

__all__ = ['FFMPEG']

LogLevel = Literal['quiet', 'panic', 'fatal', 'error', 'warning',
                   'info', 'verbose', 'debug', 'trace']


T = TypeVar('T')


def ensure(value: Any, cls: Type[T], kwarg: str) -> T:
    if isinstance(value, cls):
        return value
    params = {kwarg: value}
    return cls(**params)  # type: ignore


@dataclass
class FFMPEG(BaseWrapper):
    command = 'ffmpeg'
    stderr_markers = ['[error]', '[fatal]']
    input: Union[str, Input] = param(skip=True)
    output: Union[str, Output] = param(skip=True)

    loglevel: LogLevel = param()
    overwrite: bool = param(name='y')

    def __post_init__(self) -> None:
        self.__inputs = InputList()
        self.__outputs = OutputList()
        if self.input:
            self.__inputs.append(ensure(self.input, Input, 'input_file'))
        if self.output:
            self.__outputs.append(ensure(self.output, Output, 'output_file'))
        self.__filter_complex = FilterComplex(self.__inputs, self.__outputs)
        super().__post_init__()

    def __lt__(self, other: Input) -> None:
        """ Adds new source file.
        """
        if not isinstance(other, Input):
            return NotImplemented
        self.add_input(other)

    def __gt__(self, other: Output) -> None:
        """ Adds new output file."""
        if not isinstance(other, Output):
            return NotImplemented
        self.add_output(other)

    @property
    def video(self) -> base.Source:
        return self._get_free_source(base.VIDEO)

    @property
    def audio(self) -> base.Source:
        return self._get_free_source(base.AUDIO)

    def _get_free_source(self, kind: base.StreamType) -> base.Source:
        """
        :param kind: stream type
        :return: first stream of this kind not connected to destination
        """
        for stream in self.__inputs.streams:
            if stream.kind != kind or stream.connected:
                continue
            return stream
        else:
            raise RuntimeError("no free streams")

    def _add_codec(self, c: Codec) -> Optional[Codec]:
        """ Connect codec to filter graph output or input stream.

        :param c: codec to connect to free source
        :returns: None of codec already connected to filter graph or codec
            itself if it was connected successfully to input stream.
        """
        if c.connected:
            return None
        node = self._get_free_source(c.kind)
        node.connect_dest(c)
        return c

    def get_args(self) -> List[bytes]:
        with base.Namer():
            fc = str(self.__filter_complex)
            fc_args = ['-filter_complex', fc] if fc else []

            # Namer context is used to generate unique output stream names
            return (ensure_binary([self.command]) +
                    super().get_args() +
                    self.__inputs.get_args() +
                    ensure_binary(fc_args) +
                    self.__outputs.get_args())

    def add_input(self, input_file: Input) -> None:
        """ Adds new source to ffmpeg.
        """
        assert isinstance(input_file, Input)
        self.__inputs.append(input_file)

    def add_output(self, output: Output) -> None:
        """
        Adds output file to ffmpeg and connect it's codecs to free sources.
        """
        self.__outputs.append(output)
        for codec in output.codecs:
            self._add_codec(codec)

    def handle_stderr(self, line: str) -> str:
        """
        Handle ffmpeg output.

        Capture only lines containing one of `stderr_markers`
        """
        if not self.stderr_markers:
            # if no markers are defined, handle each line
            return super().handle_stderr(line)
        # capture only lines containing markers
        for marker in self.stderr_markers:
            if marker in line:
                return super().handle_stderr(line)
        return ''
