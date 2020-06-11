from collections import defaultdict
from typing import List, Union, Type, Optional, Dict, Any, cast, Callable, \
    Iterable, overload, Set, Tuple

from fffw.encoding import ffmpeg, filters, inputs, outputs
from fffw.graph import base


Incoming = Union[inputs.Stream, filters.Filter]
Outgoing = Union[filters.Filter, outputs.Codec]


class Vector(tuple):

    def __new__(cls, source: Union[inputs.Stream, filters.Filter,
                                   Iterable[filters.Filter],
                                   Iterable[outputs.Codec]]):
        if not hasattr(source, '__iter__'):
            source = [source]
        return tuple.__new__(cls, source)  # noqa

    def __or__(self, other: filters.Filter) -> "Vector":
        return self.connect(other)

    @property
    def kind(self) -> base.StreamType:
        return self[0].kind

    @overload
    def connect(self, dst: filters.Filter, mask: Optional[List[bool]] = None
                ) -> "Vector":
        ...

    @overload
    def connect(self, dst: Type[filters.Filter],
                mask: Optional[List[bool]] = None,
                *,
                params: Union[List[Dict[str, Any]], List[List[Any]], List[Any]]
                ) -> "Vector":
        ...

    @overload
    def connect(self, dst: "Vector", mask: Optional[List[bool]] = None
                ) -> "Vector":
        ...

    def connect(self, dst: Union[filters.Filter,
                                 Type[filters.Filter],
                                 "Vector"],
                mask: Optional[List[bool]] = None,
                params: Union[
                    None,
                    List[Dict[str, Any]],
                    List[List[Any]],
                    List[Any],
                ] = None) -> "Vector":
        if isinstance(dst, type):
            assert issubclass(dst, filters.Filter), "filter class needed"
            assert params is not None, "params not specified for filter class"
            dst = self._init_filter_vector(dst, params)
        elif isinstance(dst, filters.Filter):
            dst = Vector(dst)
        elif not isinstance(dst, Vector):
            raise TypeError(dst)

        if mask is not None:
            if len(dst) == 1:
                dst = dst * len(mask)
            assert len(dst) == len(mask)
        else:
            mask = [True] * len(dst)

        if not isinstance(dst, Vector):
            dst = Vector(dst)

        # input list
        sources: List[Union[Incoming]] = list(self)
        # filter list
        destinations: List[Optional[Outgoing]] = list(dst)

        if len(sources) != len(destinations):
            if len(sources) == 1:
                # adjusting single source to multiple destinations
                sources = sources * len(destinations)
            elif len(destinations) == 1:
                # adjusting single destination to multiple sources
                destinations = destinations * len(sources)
            else:
                raise RuntimeError("Can't apply M sources to N destinations")

        # disabling destinations by mask
        for i, enabled in enumerate(mask):
            if not enabled:
                destinations[i] = None

        # sources cache
        src_by_id: Dict[int, Incoming] = {id(src): src for src in sources}
        # destinations cache
        dst_by_id: Dict[int, Outgoing] = {id(dst): dst for dst in destinations}

        # Group destinations by source to prepare Split() filters at next step.
        src_to_dst: Dict[int, Set[int]] = dict()
        for src, dst in zip(sources, destinations):
            dst_set = src_to_dst.setdefault(id(src), set())
            dst_set.add(id(dst))

        # Group sources by destination to prepare destination clone() calls.
        dst_to_src: Dict[int, Set[int]] = dict()
        for src, dst in zip(sources, destinations):
            if dst is None:
                continue
            src_set = dst_to_src.setdefault(id(dst), set())
            src_set.add(id(src))

        # initialize Split filter for each unique source
        src_splits: Dict[int, Dict[int, filters.Filter]] = dict()
        for src_id, dst_set in src_to_dst.items():
            src = src_by_id[src_id]
            # Split incoming stream for each destination that will be connected
            # to it.
            src_splits[src_id] = dict()
            for dst_id, s in zip(dst_set, src.split(len(dst_set))):
                src_splits[src_id][dst_id] = s

        dst_clones: Dict[int, Dict[int, filters.Filter]] = dict()
        for dst_id, src_set in dst_to_src.items():
            dst = dst_by_id[dst_id]
            # Clone destination filter for each source that will be connected
            # to it.
            dst_clones[dst_id] = dict()
            for src_id, c in zip(src_set, dst.clone(len(src_set))):
                dst_clones[dst_id][src_id] = c

        links: Dict[Tuple[int, int], Outgoing] = dict()
        used_dst: Set[int] = set()
        results = list()
        # connecting sources to destinations and gathering results
        for src, dst in zip(sources, destinations):
            # use split instead of initial incoming node
            split = src_splits[id(src)][id(dst)]
            if dst is None:
                # Skip via mask, pass split to output. We can't use src here
                # because it is already connected to split filter
                results.append(split)
                continue
            clone = dst_clones[id(dst)][id(src)]

            key = id(split), id(clone)

            if key not in links:
                # connect same src to same dst only once
                links[key] = cast(Outgoing, split.connect_dest(clone))

            # add destination node to results
            results.append(links[key])

        return Vector(results)

    @staticmethod
    def _init_filter_vector(filter_class: Type[filters.Filter],
                            params: Union[
                                List[Dict[str, Any]],
                                List[List[Any]],
                                List[Any],
                            ]) -> "Vector":
        vector = []
        factory = cast(Callable[..., filters.Filter], filter_class)
        seen_filters = dict()
        for param in params:
            try:
                f = seen_filters[repr(param)]
            except KeyError:
                if isinstance(param, dict):
                    f = factory(**param)
                elif hasattr(param, '__iter__'):
                    f = factory(*param)
                else:
                    f = factory(param)
                seen_filters[repr(param)] = f
            vector.append(f)
        filter_class = Vector(vector)
        return filter_class


class SIMD:
    """ Vector video file processing helper."""

    def __init__(self, source: inputs.Input, *results: outputs.Output) -> None:
        self.validate_input_file(source)
        for output in results:
            self.validate_output_file(output)
        self.__source = source
        self.__results = results
        self.__finalized = False
        self.__ffmpeg = ffmpeg.FFMPEG(input=source)

    def __lt__(self, other: Union[Vector, inputs.Input]) -> None:
        if isinstance(other, Vector):
            other.connect(self.get_codecs(other.kind))
        elif isinstance(other, inputs.Input):
            self.add_input(other)
        else:
            return NotImplemented

    def __or__(self, other: filters.Filter) -> Vector:
        if not isinstance(other, filters.Filter):
            return NotImplemented
        return Vector(self.get_stream(other.kind)).connect(other)

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
        if not self.__finalized:
            self.__finalized = True
            for output in self.__results:
                for codec in output.codecs:
                    if codec.connected:
                        continue
                    self.get_stream(codec.kind).connect_dest(codec)
                self.__ffmpeg.add_output(output)
        return self.__ffmpeg

    @property
    def video(self) -> Vector:
        return Vector(self.get_stream(base.VIDEO))

    @property
    def audio(self) -> Vector:
        return Vector(self.get_stream(base.AUDIO))

    def get_stream(self, kind: base.StreamType) -> inputs.Stream:
        for stream in self.__source.streams:
            if stream.kind == kind:
                return stream
        raise KeyError(kind)

    def get_codecs(self, kind: base.StreamType) -> Vector:
        result = []
        for output in self.__results:
            result.append(output.get_free_codec(kind, create=False))
        return Vector(result)

    def add_input(self, source: inputs.Input) -> None:
        self.validate_input_file(source)
        self.__ffmpeg.add_input(source)


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
