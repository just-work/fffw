from dataclasses import dataclass
from typing import List, Union, Optional

from fffw.graph import base, inputs, outputs
from fffw.graph.complex import FilterComplex
from fffw.wrapper import BaseWrapper, ensure_binary

__all__ = ['FFMPEG']


class InputList(list):
    def __call__(self) -> List[str]:
        """ Delegates arguments formatting to Source objects."""
        result: List[str] = []
        for src in self:
            if hasattr(src, 'get_args') and callable(src.get_args):
                result.extend(src.get_args())
            else:
                result.append(str(src))
        return result


@dataclass
class FFMPEGParams:
    pass


class FFMPEG(FFMPEGParams, BaseWrapper):
    command = 'ffmpeg'
    stderr_markers = ['[error]', '[fatal]']

    def __init__(self, *sources: Union[inputs.Input, str],
                 output: Union[None, outputs.Output, str] = None) -> None:
        """
        :param sources: list of input files (or another ffmpeg sources)
        """
        super(FFMPEG, self).__init__()
        self.__input_list = inputs.InputList(
            *(
                inputs.Input(input_file=src)
                if isinstance(src, str) else src
                for src in sources
            ))
        self.__output_list = outputs.OutputList()
        if output:
            self.__output_list.append(
                outputs.Output(output_file=output)
                if isinstance(output, str) else output
            )
        self.__filter_complex = FilterComplex(self.__input_list,
                                              self.__output_list)

    def __lt__(self, other: inputs.Input) -> None:
        """ Adds new source file.
        """
        if not isinstance(other, inputs.Input):
            return NotImplemented
        self.add_input(other)

    def __gt__(self, other: outputs.Output) -> None:
        """ Adds new output file."""
        if not isinstance(other, outputs.Output):
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
        for stream in self.__input_list.streams:
            if stream.kind != kind or stream.connected:
                continue
            return stream
        else:
            raise RuntimeError("no free streams")

    def _add_codec(self, c: outputs.Codec) -> Optional[outputs.Codec]:
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
                    self.__input_list.get_args() +
                    super(FFMPEG, self).get_args() +
                    ensure_binary(fc_args) +
                    self.__output_list.get_args())

    def add_input(self, input_file: inputs.Input) -> None:
        """ Adds new source to ffmpeg.
        """
        assert isinstance(input_file, inputs.Input)
        self.__input_list.append(input_file)

    def add_output(self, output: outputs.Output) -> None:
        """
        Adds output file to ffmpeg and connect it's codecs to free sources.
        """
        self.__output_list.append(output)
        for codec in output.codecs:
            self._add_codec(codec)

    def handle_stderr(self, line: str) -> None:
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
                super().handle_stderr(line)
