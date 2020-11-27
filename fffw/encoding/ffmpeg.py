from dataclasses import dataclass
from typing import List, Optional, Union, Tuple

from fffw.encoding.complex import FilterComplex
from fffw.encoding.inputs import InputList, Input, Stream
from fffw.encoding.outputs import OutputList, Output, Codec
from fffw.graph import base, meta
from fffw.graph.meta import AUDIO, VIDEO, StreamType
from fffw.wrapper import BaseWrapper, ensure_binary, param

__all__ = ['FFMPEG']


@dataclass
class FFMPEG(BaseWrapper):
    """
    ffmpeg command line basic wrapper.

    >>> from fffw.encoding.codecs import VideoCodec, AudioCodec
    >>> from fffw.encoding.filters import Scale
    >>> from fffw.encoding.outputs import output_file
    >>> ff = FFMPEG('/tmp/input.mp4', overwrite=True)
    >>> c = VideoCodec('libx264', bitrate=4_000_000)
    >>> ff.video | Scale(1280, 720) > c
    VideoCodec(codec='libx264', bitrate=4000000)
    >>> ff.overwrite = True
    >>> ff > output_file('/tmp/output.mp4', c,
    ...                  AudioCodec('libfdk_aac', bitrate=192_000))
    >>> ff.get_cmd()
    'ffmpeg -y -i /tmp/input.mp4\
 -filter_complex "[0:v]scale=w=1280:h=720[vout0]"\
 -map "[vout0]" -c:v libx264 -b:v 4000000 -map 0:a -c:a libfdk_aac -b:a 192000\
 /tmp/output.mp4'
    >>>
    """
    command = 'ffmpeg'
    stderr_markers = ['[error]', '[fatal]']
    input: Union[str, Input] = param(skip=True)
    output: Union[str, Output] = param(skip=True)

    loglevel: str = param()
    """ Loglevel: i.e. `level+info`."""
    overwrite: bool = param(name='y')
    """ Overwrite output files without manual confirmation."""
    init_hardware: str = param(name='init_hw_device')
    """ Initializes hardware acceleration device."""
    filter_hardware: str = param(name='filter_hw_device')
    """ Sets a device for filter graph by it's name set with `init_hardware`."""

    def __post_init__(self) -> None:
        """
        Fills internal shared structures for input and output files, and
        initializes filter graph.
        """

        self.__inputs = InputList()
        if self.input:
            if not isinstance(self.input, Input):
                self.__inputs.append(Input(input_file=self.input))
            else:
                self.__inputs.append(self.input)

        self.__outputs = OutputList()
        if self.output:
            if not isinstance(self.output, Output):
                self.__outputs.append(Output(output_file=self.output))
            else:
                self.__outputs.append(self.output)

        self.__filter_complex = FilterComplex(self.__inputs, self.__outputs)

        # calling super() to freeze params.
        super().__post_init__()

    def __lt__(self, other: Input) -> Input:
        """ Adds new source file.

        >>> ff = FFMPEG()
        >>> src = ff < Input(input_file='/tmp/input.mp4')
        >>>
        """
        if not isinstance(other, Input):
            return NotImplemented
        return self.add_input(other)

    def __gt__(self, other: Output) -> Output:
        """ Adds new output file.

        >>> from fffw.encoding.inputs import *
        >>> from fffw.encoding.outputs import *
        >>> ff = FFMPEG(input=input_file('input.mp4'))
        >>> dest = ff > output_file('/tmp/output.mp4')
        >>>
        """
        if not isinstance(other, Output):
            return NotImplemented
        return self.add_output(other)

    @property
    def inputs(self) -> Tuple[Input, ...]:
        """
        :return: a copy of ffmpeg input list.
        """
        return tuple(self.__inputs)

    @property
    def outputs(self) -> Tuple[Output, ...]:
        """
        :return: a copy of ffmpeg output list.
        """
        return tuple(self.__outputs)

    @property
    def filter_device(self) -> meta.Device:
        """ Returns filter hardware device metadata."""
        hardware, init = self.init_hardware.split("=")
        name = init.split(':', 1)[0]
        if self.filter_hardware != name:
            raise ValueError(self.filter_hardware)
        return meta.Device(hardware, name)

    @property
    def video(self) -> Stream:
        """
        :returns: first video stream not yet connected to filter graph or codec.

        >>> from fffw.encoding.filters import Scale
        >>> ff = FFMPEG('/tmp/input.mp4')
        >>> ff.video | Scale(1280, 720)
        Scale(width=1280, height=720)
        >>>
        """
        return self._get_free_source(VIDEO)

    @property
    def audio(self) -> Stream:
        """

        :returns: first audio stream not yet connected to filter graph or codec.

        >>> from fffw.encoding.codecs import AudioCodec
        >>> ff = FFMPEG('/tmp/input.mp4')
        >>> ac = AudioCodec('aac')
        >>> ff.audio > ac
        AudioCodec(codec='aac', bitrate=0)
        >>>
        """
        return self._get_free_source(AUDIO)

    def _get_free_source(self, kind: StreamType) -> Stream:
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
        """
        :returns: command line arguments for ffmpeg.

        This includes:
        - ffmpeg executable name
        - ffmpeg parameters
        - input list args
        - filter_graph definition
        - output list args
        """

        with base.Namer():
            fc = str(self.__filter_complex)
            fc_args = ['-filter_complex', fc] if fc else []

            # Namer context is used to generate unique output stream names
            return (super().get_args() +
                    self.__inputs.get_args() +
                    ensure_binary(fc_args) +
                    self.__outputs.get_args())

    def add_input(self, input_file: Input) -> Input:
        """ Adds new source to ffmpeg.

        >>> ff = FFMPEG()
        >>> ff.add_input(Input(input_file="/tmp/input.mp4"))
        >>>
        """
        assert isinstance(input_file, Input)
        self.__inputs.append(input_file)
        return input_file

    def add_output(self, output: Output) -> Output:
        """
        Adds output file to ffmpeg and connect it's codecs to free sources.

        >>> ff = FFMPEG()
        >>> ff.add_output(Output(output_file='/tmp/output.mp4'))
        >>>
        """
        self.__outputs.append(output)
        for codec in output.codecs:
            self._add_codec(codec)
        return output

    def handle_stderr(self, line: str) -> str:
        """
        Handle ffmpeg output.

        Capture only lines containing one of `stderr_markers`.

        :param line: ffmpeg output line
        :returns: line to be appended to whole ffmpeg output.
        """
        if not self.stderr_markers:
            # if no markers are defined, handle each line
            return super().handle_stderr(line)
        # capture only lines containing markers
        for marker in self.stderr_markers:
            if marker in line:
                return super().handle_stderr(line)
        return ''

    def check_buffering(self) -> None:
        """
        Checks that ffmpeg command will not cause frame buffering and
        out of memory errors.

        Each input file must be read simultaneously be all codecs in outputs,
        or some streams will be buffered until requested by output codecs.
        """
        chains = []
        for output in self.__outputs:
            for codec in output.codecs:
                streams = codec.check_buffering()
                if streams is None:
                    # Streams can't be computed because of missing metadata.
                    raise ValueError(streams)
                chains.append(streams)
        for chunk in zip(*chains):
            # Check that every codec reads same input stream
            if len(set(chunk)) > 1:
                # some codec read different file at this step, so one of input
                # stream will be buffered until this file is read by another
                # codec.
                raise BufferError(chunk)
