from collections import defaultdict
from typing import List, Union, Type, Optional, Dict, Any, cast, Callable

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

    @property
    def video(self) -> "Cursor":
        return Cursor(self, *self.get_streams(base.VIDEO))

    @property
    def audio(self) -> "Cursor":
        return Cursor(self, *self.get_streams(base.AUDIO))

    def get_streams(self, kind: base.StreamType) -> List[inputs.Stream]:
        for stream in self.__source.streams:
            if stream.kind == kind:
                return [stream] * len(self.__outputs)
        raise KeyError(kind)

    def get_codecs(self, kind: base.StreamType) -> List[outputs.Codec]:
        result = []
        for output in self.__outputs:
            result.append(next(filter(lambda c: c.kind == kind,
                                      output.codecs)))
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

    def __apply(self, vector: Union[List[Optional[filters.Filter]],
                                    List[outputs.Codec]]) -> "Cursor":
        """ Applies each filter in list to it's corresponding stream.

        :param vector: list of filters or list of codecs
        :returns: new streams vector.
        """
        sources = dict()
        destinations = dict()
        indices = defaultdict(list)
        src_to_dst = defaultdict(set)
        for src, dst, i in zip(self.streams, vector, range(len(vector))):
            sources[id(src)] = src
            destinations[id(dst)] = dst
            # Splitting single source to connect to multiple outputs
            src_to_dst[id(src)].add(id(dst))
            indices[id(src), id(dst)].append(i)

        for src_id, dst_ids in src_to_dst.items():
            src = sources[src_id]
            split = filters.Split(self.kind, output_count=len(dst_ids))
            src.connect_dest(split)
            for dst_id in dst_ids:
                dst = destinations[dst_id]
                if dst is not None:
                    split.connect_dest(dst)
                else:
                    for idx in indices[id(src), id(dst)]:
                        vector[idx] = split
        return Cursor(self.vector, *vector)

    def connect(self,
                other: Union[filters.Filter, Type[filters.Filter]],
                mask: Optional[List[bool]] = None,
                params: Union[
                    None,
                    List[Dict[str, Any]],
                    List[List[Any]],
                    List[Any],
                ] = None,
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
        vector: List[Optional[filters.Filter]]
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
            seen_filters = dict()
            for param in params:
                try:
                    f = seen_filters[repr(param)]
                except KeyError:
                    if isinstance(param, dict):
                        f = factory(**param)
                    elif isinstance(param, list):
                        f = factory(*param)
                    else:
                        f = factory(param)
                    seen_filters[repr(param)] = f
                vector.append(f)

        if mask is None:
            mask = [True] * len(self.streams)

        if len(mask) != len(self.streams):
            raise ValueError("mask vector doesn't match streams vector")
        else:
            for i, enabled in enumerate(mask):
                if not enabled:
                    vector[i] = None
        return self.__apply(vector)

    def finalize(self) -> None:
        """ Connect streams to codecs."""
        self.__apply(self.vector.get_codecs(self.kind))
