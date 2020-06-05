from typing import List, Union, Type, Optional, Dict, Any, Tuple, cast, Callable

from fffw.encoding import ffmpeg, codecs, filters
from fffw.graph import inputs, outputs, meta, base, InputList, OutputList


class Vector:
    """ Vector video file processing helper."""

    def __init__(self, source: inputs.Input, *results: outputs.Output) -> None:
        self.validate_input_file(source)
        for output in results:
            self.validate_output_file(output)
        self.__source = source
        self.__inputs = InputList([source])
        self.__outputs = OutputList(results)

    def __lt__(self, other: inputs.Input) -> inputs.Input:
        """
        Add additional files to ffmpeg.

        :returns: input added to ffmpeg.

        >>> source = inputs.input_file(
        ...     "input.mp4",
        ...     inputs.Stream(base.VIDEO, meta=meta.video_meta_data()))
        ...     inputs.Stream(base.AUDIO, meta=meta.audio_meta_data())))
        >>> output = outputs.output_file(
        ...     "output.mp4",
        ...     codecs.VideoCodec('libx264'),
        ...     codecs.AudioCodec('aac'))
        >>>

        """
        assert isinstance(other, inputs.Input)
        self.validate_input_file(other)
        self.__inputs.append(other)
        return other

    @staticmethod
    def init_wrapper(sources: InputList,
                     results: OutputList) -> ffmpeg.FFMPEG:
        """ Initializes ffmpeg instance."""
        return ffmpeg.FFMPEG(input=sources, output=results)

    @staticmethod
    def validate_input_file(input_file: inputs.Input) -> None:
        if not input_file.streams:
            raise ValueError("streams must be set for input file")
        for stream in input_file.streams:
            if not stream.meta:
                raise ValueError("stream metadata must be set for input file")

    @staticmethod
    def validate_output_file(output: outputs.Output) -> None:
        if not output.codecs:
            raise ValueError("codecs must be set for output file")

    @property
    def ffmpeg(self) -> ffmpeg.FFMPEG:
        video_stream = next(filter(lambda s: s.kind == base.VIDEO,
                                   self.__source.streams))
        audio_stream = next(filter(lambda s: s.kind == base.AUDIO,
                                   self.__source.streams))

        for codec in self.get_codecs(base.VIDEO):
            if codec.edge is None:
                video_stream > codec
        for codec in self.get_codecs(base.AUDIO):
            if codec.edge is None:
                audio_stream > codec

        return self.init_wrapper(self.__inputs, self.__outputs)

    def get_codecs(self, kind: base.StreamType) -> List[outputs.Codec]:
        result = []
        for output in self.__outputs:
            result.append(output.get_free_codec(kind))
        return result


class Cursor:
    def __init__(self, vector: Vector, 
                 *streams: Union[inputs.Stream, filters.Filter]) -> None:
        self.vector = vector
        self.streams = streams
        self.kind = streams[0].kind

    def __or__(self, other: filters.Filter) -> "Cursor":
        if not isinstance(other, filters.Filter):
            return NotImplemented
        return self.connect(other)

    def connect(self,
                other: Union[filters.Filter, Type[filters.Filter]],
                mask: Optional[List[bool]] = None,
                params: Optional[List[Union[List[Any],
                                            Tuple[Any],
                                            Dict[str, Any]]]] = None,
                ) -> "Cursor":
        # noinspection PyUnresolvedReferences
        """
        Applies a filter to a stream vector.

        :param other: filter instance or class
        :param mask: stream mask (whether to apply filter or not)
        :param params: filter params if they differs between streams
        :return: new streams vector.

        >>> cursor.connect(Volume, params=[10, 20, 30])
        >>> cursor.connect(Scale(640, 360))
        >>> cursor.connect(overlay, mask=[True, False, True])

        """
        if isinstance(other, filters.Filter):
            if params is not None:
                raise ValueError("params already passed to filter instance")
            vector = [other] * len(self.streams)
        else:
            if params is None:
                raise ValueError("params must be passed with filter class")
            if len(params) != len(self.streams):
                raise ValueError("params vector doesn't match streams vector")
            vector = []
            factory = cast(Callable[..., filters.Filter], other)
            for param in params:
                if isinstance(param, dict):
                    vector.append(factory(**param))
                else:
                    vector.append(factory(*param))

        if mask is None:
            mask = [True] * len(self.streams)
        if len(mask) != len(self.streams):
            raise ValueError("mask vector doesn't match streams vector")

        return self.__apply_filters(vector, mask)

    def __apply_filters(self, vector: List[filters.Filter],
                        mask: List[bool]) -> "Cursor":
        """ Applies each filter in list to it's corresponding stream.

        :param vector: list of filters
        :param mask: flag for skipping a filter in list
        :returns: new streams vector.
        """
        if not all(mask):
            raise NotImplementedError()
        streams = []
        for src, dst in zip(self.streams, vector):
            streams.append(cast(filters.Filter, src.connect_dest(dst)))
        return Cursor(self.vector, *streams)

    def finalize(self) -> None:
        """ Connect streams to codecs."""
        dst = self.vector.get_codecs(self.kind)
        for stream, codec in zip(self.streams, dst):
            stream > codec
