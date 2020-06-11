from typing import List, Union, Type, Optional, Dict, Any, cast, Callable, \
    Iterable, overload, Set, Tuple

from fffw.encoding import ffmpeg, filters, inputs, outputs, FFMPEG
from fffw.graph import base

Group = Dict[int, Set[int]]

Incoming = Union[inputs.Stream, filters.Filter]
Outgoing = Union[filters.Filter, outputs.Codec]


def group(first: Iterable[Any], second: Iterable[Any]
          ) -> Group:
    """
    Group second iterable by first.
    """
    src_to_dst: Group = dict()
    for src, dst in zip(first, second):
        if src is None:
            continue
        dst_set = src_to_dst.setdefault(id(src), set())
        dst_set.add(id(dst))
    return src_to_dst


def prepare_src_splits(sources: Dict[int, Incoming],
                       groups: Group
                       ) -> Dict[Tuple[int, int], filters.Filter]:
    """ Initialize split filter for each unique group.

    :returns: split for each src/dst pair.
    """
    src_splits: Dict[Tuple[int, int], filters.Filter] = dict()
    for src_id, dst_set in groups.items():
        src = sources[src_id]
        # Split incoming stream for each destination that will be connected
        # to it.
        for dst_id, s in zip(dst_set, src.split(len(dst_set))):
            src_splits[src_id, dst_id] = s
    return src_splits


def prepare_dst_clones(destinations: Dict[int, Outgoing],
                       groups: Group) -> Dict[Tuple[int, int], Outgoing]:
    """ Prepares copies of filter for each unique group.

    :returns: destination filter copy for each src/dst pair.
    """
    dst_clones: Dict[Tuple[int, int], Outgoing] = dict()
    for dst_id, src_set in groups.items():
        dst = destinations[dst_id]
        # Clone destination filter for each source that will be connected
        # to it.
        clones = cast(List[Outgoing], dst.clone(len(src_set)))
        for src_id, c in zip(src_set, clones):
            dst_clones[dst_id, src_id] = c
    return dst_clones


def map_sources_to_destinations(
        sources: List[Incoming],
        src_splits: Dict[Tuple[int, int], filters.Filter],
        destinations: List[Optional[Outgoing]],
        dst_clones: Dict[Tuple[int, int], Outgoing]
) -> "Vector":
    links: Dict[Tuple[int, int], Outgoing] = dict()
    results: List[Outgoing] = list()
    # connecting sources to destinations and gathering results
    for src, dst in zip(sources, destinations):
        # use split instead of initial incoming node
        split = src_splits[id(src), id(dst)]
        if dst is None:
            # Skip via mask, pass split to output. We can't use src here
            # because it is already connected to split filter
            results.append(split)
            continue
        clone = dst_clones[id(dst), id(src)]

        key = id(split), id(clone)

        if key not in links:
            # connect same src to same dst only once
            links[key] = cast(Outgoing, split.connect_dest(clone))

        # add destination node to results
        results.append(links[key])
    return Vector(cast(Union[List[filters.Filter], List[outputs.Codec]],
                       results))


class Vector(tuple):

    def __new__(cls, source: Union[inputs.Stream, filters.Filter,
                                   Iterable[filters.Filter],
                                   Iterable[outputs.Codec]]) -> "Vector":
        iterable: Union[Iterable[inputs.Stream],
                        Iterable[filters.Filter],
                        Iterable[outputs.Codec]]
        if isinstance(source, filters.Filter):
            iterable = [source]
        elif isinstance(source, inputs.Stream):
            iterable = [source]
        else:
            iterable = source
        return tuple.__new__(cls, iterable)  # noqa

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
        dst, mask = self.__normalize_args(dst, mask, params)

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
        dst_by_id: Dict[int, Outgoing] = {
            id(dst): dst for dst in destinations if dst is not None}

        # Group destinations by source to prepare Split() filters at next step.
        src_to_dst = group(sources, destinations)

        # Group sources by destination to prepare destination clone() calls.
        dst_to_src = group(destinations, sources)

        # Split sources to have unique input for each unique destination
        # connected to same source
        src_splits = prepare_src_splits(src_by_id, src_to_dst)

        # Split destinations (with their inputs) to have unique output for each
        # unique source connected to same destination
        dst_clones = prepare_dst_clones(dst_by_id, dst_to_src)

        return map_sources_to_destinations(sources, src_splits,
                                           destinations, dst_clones)

    def __normalize_args(self,
                         dst: Union[filters.Filter,
                                    Type[filters.Filter],
                                    "Vector"],
                         mask: Optional[List[bool]] = None,
                         params: Union[
                             None,
                             List[Dict[str, Any]],
                             List[List[Any]],
                             List[Any],
                         ] = None) -> Tuple["Vector", List[bool]]:
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
                dst = cast(Vector, dst * len(mask))
            assert len(dst) == len(mask)
        else:
            mask = [True] * len(dst)
        if not isinstance(dst, Vector):
            dst = Vector(dst)
        return dst, mask

    @staticmethod
    def _init_filter_vector(filter_class: Type[filters.Filter],
                            params: Union[
                                List[Dict[str, Any]],
                                List[List[Any]],
                                List[Any],
                            ]) -> "Vector":
        vector = []
        factory = cast(Callable[..., filters.Filter], filter_class)
        seen_filters: Dict[str, filters.Filter] = dict()
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
        return Vector(vector)


class SIMD:
    """ Vector video file processing helper."""

    def __init__(self, source: inputs.Input, *results: outputs.Output) -> None:
        self.validate_input_file(source)
        for output in results:
            self.validate_output_file(output)
        self.__source = source
        self.__results = results
        self.__finalized = False
        self.__ffmpeg = FFMPEG(input=source)

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
    def ffmpeg(self) -> FFMPEG:
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
