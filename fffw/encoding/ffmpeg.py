from typing import List, Any, Union, Optional

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


class FFMPEG(BaseWrapper):
    command = 'ffmpeg'
    stderr_markers = ['[error]', '[fatal]']

    arguments = [
        ('loglevel', '-loglevel '),
        ('strict', '-strict '),
        ('realtime', '-re '),
        ('threads', '-threads '),
        ('time_offset', '-ss '),
        ('no_autorotate', '-noautorotate'),
        ('inputformat', '-f '),
        ('pix_fmt', '-pix_fmt '),
        ('presize_offset', '-ss '),
        ('filter_complex', '-filter_complex '),
        ('time_limit', '-t '),
        ('vframes', '-vframes '),
        ('overwrite', '-y '),
        ('verbose', '-v '),
        ('novideo', '-vn '),
        ('noaudio', '-an '),
        ('vfilter', '-vf '),
        ('afilter', '-af '),
        ('metadata', '-metadata '),
        ('map_chapters', '-map_chapters '),
        ('map_metadata', '-map_metadata '),
        ('vbsf', '-bsf:v '),
        ('absf', '-bsf:a '),
        ('format', '-f '),
        ('segment_list_flags', '-segment_list_flags '),
    ]

    def __init__(self, *sources: Union[inputs.Input, str],
                 output: Union[None, outputs.Output, str] = None, **kw: Any):
        """
        :param sources: list of input files (or another ffmpeg sources)
        :param kw: ffmpeg command line arguments
        """
        super(FFMPEG, self).__init__(**kw)
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

    def __setattr__(self, key: str, value: Any) -> None:
        # TODO: #9 refactor working with args
        if key == 'filter_complex':
            raise NotImplementedError("use init_filter_complex instead")
        if key == 'inputfile':
            raise NotImplementedError("use add_input instead")
        return super(FFMPEG, self).__setattr__(key, value)

    @property
    def filter_complex(self) -> FilterComplex:
        # TODO #9 refactor filter complex initialization
        return self._args['filter_complex']

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
        node: Union[base.Source, base.Dest]
        if c.map:
            return None
        node = self._get_free_source(c.kind)
        node.connect_dest(c)
        return c

    def init_filter_complex(self) -> FilterComplex:
        # TODO #9 refactor filter complex initialization
        fc = FilterComplex(self.__input_list, self.__output_list)
        self._args['filter_complex'] = fc
        return fc

    def get_args(self) -> List[bytes]:
        with base.Namer():
            # Namer context is used to generate unique output stream names
            return (ensure_binary([self.command]) +
                    self.__input_list.get_args() +
                    super(FFMPEG, self).get_args() +
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
