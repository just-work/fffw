from itertools import chain
from typing import List, Tuple, Any, Union

from fffw.encoding import Muxer, codec
from fffw.graph import FilterComplex, base, inputs
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

    def __init__(self, *sources: inputs.Input, **kw: Any):
        """
        :param sources: list of input files (or another ffmpeg sources)
        :param kw: ffmpeg command line arguments
        """
        super(FFMPEG, self).__init__(**kw)
        self.__outputs: List[Tuple[Tuple[codec.BaseCodec, ...], Muxer]] = []
        self.__vdest = self.__adest = 0
        self.__input_list = inputs.InputList(*sources)

    def init_filter_complex(self) -> FilterComplex:
        # TODO #9 refactor filter complex initialization
        assert not self.__outputs, "outputs already defined"
        fc = FilterComplex(self.__input_list)
        self._args['filter_complex'] = fc
        return fc

    @property
    def filter_complex(self) -> FilterComplex:
        return self._args['filter_complex']

    def get_args(self) -> List[bytes]:
        return (ensure_binary([self.command]) +
                ensure_binary(self.__input_list.get_args()) +
                super(FFMPEG, self).get_args() +
                ensure_binary(self.get_output_args()))

    def get_output_args(self) -> List[bytes]:
        result: List[bytes] = []
        for codecs, muxer in self.__outputs:
            args = list(chain.from_iterable(c.get_args() for c in codecs))
            output = [ensure_binary(muxer.output)]
            result.extend(args + muxer.get_args() + output)
        return result

    def add_input(self, input_file: inputs.Input) -> None:
        """ Adds new source to ffmpeg.
        """
        assert isinstance(input_file, inputs.Input)
        self.__input_list.append(input_file)

    def get_free_source(self, kind: base.StreamType) -> base.Source:
        """
        :param kind: stream type
        :return: first stream of this kind not connected to destination
        """
        for stream in self.__input_list.streams:
            if stream.kind != kind or stream.edge is not None:
                continue
            return stream
        else:
            raise RuntimeError("no free streams")

    def add_codec(self, c: codec.BaseCodec) -> None:
        """ Connect codec to filter graph output or input stream."""
        # TODO: #14 refactor connecting codec while merging Dest and BaseCodec
        node: Union[base.Source, base.Dest]
        if c.map:
            try:
                node = next(filter(lambda s: s.name == c.map,
                                   self.__input_list.streams))
            except StopIteration:
                raise RuntimeError("No stream for map")
        else:
            try:
                node = self.get_free_source(c.codec_type)
            except RuntimeError:
                # no free sources, search for free dest in fc
                fc = self.filter_complex
                if fc is None:
                    raise
                if c.codec_type == base.VIDEO:
                    node = fc.get_video_dest(self.__vdest, create=False)
                    self.__vdest += 1
                else:
                    node = fc.get_audio_dest(self.__adest, create=False)
                    self.__adest += 1
        if c.codec_type != node.kind:
            raise RuntimeError("stream and codec type mismatch")
        node | c

    def add_output(self, muxer: Muxer, *codecs: codec.BaseCodec) -> None:
        # TODO: #14 muxer should contain codecs and codecs should connect
        #  directly to input stream or graph filter.
        assert isinstance(muxer, Muxer)
        for c in codecs:
            self.add_codec(c)
        self.__outputs.append((codecs, muxer))

    @property
    def outputs(self) -> List[Tuple[Tuple[codec.BaseCodec, ...], Muxer]]:
        return list(self.__outputs)

    def __lt__(self, other: inputs.Input) -> None:
        """ Adds new source file.
        """
        if not isinstance(other, inputs.Input):
           return NotImplemented
        self.add_input(other)

    def __setattr__(self, key: str, value: Any) -> None:
        # TODO: #9 refactor working with args
        if key == 'filter_complex':
            raise NotImplementedError("use init_filter_complex instead")
        if key == 'inputfile':
            raise NotImplementedError("use add_input instead")
        return super(FFMPEG, self).__setattr__(key, value)

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
