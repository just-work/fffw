from typing import *

from fffw.graph.meta import AUDIO, VIDEO, StreamType, Meta
from fffw.encoding import filters, inputs, outputs, FFMPEG

Group = Dict[int, Set[int]]
""" Grouping result."""
PairKey = Tuple[int, int]
""" Dict key containing ids of two related objects."""

Incoming = Union[inputs.Stream, filters.Filter]
Outgoing = Union[filters.Filter, outputs.Codec]


def group(first: Iterable[Any], second: Iterable[Any]) -> Group:
    """
    Group second iterable by first.

    :param first: First iterable. Id of each object in iterable will be used as
        a key.
    :param second: Second iterable. Id of each object in iterable will be added
        to a set, which is a value for corresponding key in first iterable.
    :returns: A dict that maps single object from first iterable to a set of
        objects from second iterable by object ids.
    """
    src_to_dst: Group = dict()
    for src, dst in zip(first, second):
        if src is None:
            continue
        dst_set = src_to_dst.setdefault(id(src), set())
        dst_set.add(id(dst))
    return src_to_dst


def prepare_src_splits(sources: Dict[int, Incoming],
                       groups: Group) -> Dict[PairKey, filters.Filter]:
    """
    Initialize split filter for each unique group.

    Source (which is a group key) is split to N nodes, where N is a number of
    corresponding outputs related to this source.

    :param sources: contains sources by object id.
    :param groups: destinations grouped by source id.
    :returns: split for each src/dst pair.
    """
    src_splits: Dict[PairKey, filters.Filter] = dict()
    for src_id, dst_set in groups.items():
        src = sources[src_id]
        # Split incoming stream for each destination that will be connected
        # to it.
        for dst_id, s in zip(dst_set, src.split(len(dst_set))):
            src_splits[src_id, dst_id] = s
    return src_splits


def prepare_dst_clones(destinations: Dict[int, Outgoing],
                       groups: Group) -> Dict[PairKey, Outgoing]:
    """
    Prepares copies of filter for each unique group.

    Destination (which is a group key) is copied N times with same parameters,
    where N is a number of unique inputs related to this destination.

    If destination is a filter with multiple inputs, each input is split
    multiple times, disconnected from initial filter and split results are
    connected to filter copies.

    :param destinations: contains outputs by object id.
    :param groups: sources grouped by destination id.
    :returns: destination filter copy for each src/dst pair.
    """
    dst_clones: Dict[Tuple[int, int], Outgoing] = dict()
    for dst_id, src_set in groups.items():
        dst = destinations[dst_id]
        # Clone destination filter for each source that will be connected
        # to it.
        # noinspection PyTypeChecker
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
    """
    Links sources to destinations.

    For each source/destination pair we find corresponding source split result
    and destination clone. Split is connected to clone, clone is added to
    resulting vector and cached to prevent connecting same split to same clone
    twice.

    If destination is None, which means that it is disabled by mask,
    split is added to resulting vector instead of clone.

    :param sources: list of initial incoming nodes.
    :param src_splits: contains actual split node for each source/destination
        pair.
    :param destinations: list of outgoing nodes (or None if disabled by mask).
    :param dst_clones: contains actual dst clone for each source/destination
        pair.
    :returns: final vector with results of src/dst connection.
    """
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
            # noinspection PyTypeChecker
            links[key] = cast(Outgoing, split.connect_dest(clone))

        # add destination node to results
        results.append(links[key])
    # noinspection PyTypeChecker
    return Vector(cast(Union[List[filters.Filter], List[outputs.Codec]],
                       results))


def init_filter_vector(filter_class: Type[filters.Filter],
                       params: Union[
                           List[Dict[str, Any]],
                           List[List[Any]],
                           List[Any],
                       ]) -> "Vector":
    """
    Initializes filter vector from filter class and list of parameters.

    :param filter_class: type to initialize
    :param params: list of filter class positional or keyword arguments
    :returns: filter vector with elements count equal to length of params list,
        each vector is instance of filter_class.
    """
    vector = []
    # noinspection PyTypeChecker
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


def normalize_args(dst: Union[filters.Filter,
                              Type[filters.Filter],
                              "Vector"],
                   mask: Optional[List[bool]] = None,
                   params: Union[
                       None,
                       List[Dict[str, Any]],
                       List[List[Any]],
                       List[Any],
                   ] = None) -> Tuple["Vector", List[bool]]:
    """
    Transform different args to same form: vector of filters/codecs and
    boolean mask with corresponding length.

    :param dst: destination vector, single filter or filter class used to
        initialize same filter with different parameters.
    :param mask: list of flags that allows to skip applying destination
        filters to some of sources.
    :param params: filter class constructor arguments used to initialize
        a destination filter vector from filter class.
    :returns: new vector which is a result of applying destination filters
        to a input streams vector.
    """
    if isinstance(dst, type):
        # handle filter class + params
        assert issubclass(dst, filters.Filter), "filter class needed"
        assert params is not None, "params not specified for filter class"
        dst = init_filter_vector(dst, params)
    elif isinstance(dst, filters.Filter):
        # handle filter instance
        dst = Vector(dst)
    elif not isinstance(dst, Vector):
        # handle vector instance - rest types are not supported.
        raise TypeError(dst)

    # align mask and destination lengths
    if mask is not None:
        if len(dst) == 1:
            # handle filter instance and mask vector
            dst = Vector(dst * len(mask))
        assert len(dst) == len(mask)
    else:
        # handle omitted mask
        mask = [True] * len(dst)
    return dst, mask


class Vector(tuple):
    """
    Represents immutable stream vector that helps to apply same or similar
    filters to a set of stream simultaneously.
    """

    def __new__(cls, source: Union[inputs.Stream, filters.Filter,
                                   Iterable[filters.Filter],
                                   Iterable[outputs.Codec]]) -> "Vector":
        """
        Constructs new Vector from single input or a list of inputs.

        Normalizes input parameter to an iterable of input stream, filter or
        codec.

        :param source: single input stream (video or audio), single filter,
            list of filters or list of codecs.
        :returns: an immutable list of streams, filters or codecs.
        """
        iterable: Union[Iterable[inputs.Stream],
                        Iterable[filters.Filter],
                        Iterable[outputs.Codec]]
        if isinstance(source, filters.Filter):
            iterable = [source]
        elif isinstance(source, inputs.Stream):
            # This branch is separated from previous for mypy.
            iterable = [source]
        else:
            iterable = source
        return tuple.__new__(cls, iterable)  # noqa

    def __or__(self, other: Union["Vector", filters.Filter]) -> "Vector":
        """ A shortcut to connect vector to another filter."""
        return self.connect(other)

    def __ror__(self, other: filters.Filter) -> "Vector":
        # noinspection PyUnresolvedReferences
        """ A shortcut to connect a filter to the vector.

        >>> overlay: Vector = simd | Overlay(1100, 100)
        >>> scaled_logo: Filter = logo.video | Scale(120, 120)
        >>> scaled_logo | overlay
        """
        if not isinstance(other, filters.Filter):
            return NotImplemented
        return Vector(other) | self

    @property
    def kind(self) -> StreamType:
        """
        :returns: a kind of streams in vector.
        """
        kinds = {s.kind for s in self}
        if len(kinds) != 1:
            raise RuntimeError("multiple kind of streams in vector")
        return self[0].kind

    @property
    def meta(self) -> Meta:
        """
        :returns: metadata for a stream in vector.
        """
        if len(self) != 1:
            raise RuntimeError("not a scalar")
        return self[0].meta

    @overload
    def connect(self, dst: filters.Filter, mask: Optional[List[bool]] = None
                ) -> "Vector":
        """

        >>> vector = Vector(inputs.Stream(VIDEO))
        >>> vector.connect(filters.Scale(), mask=[True, False])
        """
        ...  # pragma: no cover

    @overload
    def connect(self, dst: Type[filters.Filter],
                mask: Optional[List[bool]] = None,
                *,
                params: Union[List[Dict[str, Any]], List[List[Any]], List[Any]]
                ) -> "Vector":
        """

        >>> vector = Vector(inputs.Stream(VIDEO))
        >>> vector.connect(filters.Scale, params=[
        ... {'width': 1280, 'height': 720},
        ... {'width': 640, 'height': 360}])
        >>>
        """
        ...  # pragma: no cover

    @overload
    def connect(self, dst: "Vector", mask: Optional[List[bool]] = None
                ) -> "Vector":
        """

        >>> vector = Vector(inputs.Stream(VIDEO))
        >>> out = Vector([
        ... outputs.Codec(codec='libx264'),
        ... outputs.Codec(codec='libx264')])
        >>> vector.connect(out)
        """
        ...  # pragma: no cover

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
        """
        Connects current vector to destination filter vector.

        :param dst: destination vector, single filter or filter class used to
            initialize same filter with different parameters.
        :param mask: list of flags that allows to skip applying destination
            filters to some of sources.
        :param params: filter class constructor arguments used to initialize
            a destination filter vector from filter class.
        :returns: new vector which is a result of applying destination filters
            to a input streams vector.
        """
        # Transform different args to same form: vector of filters/codecs and
        # boolean mask with corresponding length.
        dst, mask = normalize_args(dst, mask, params)

        # input list
        sources: List[Union[Incoming]] = list(self)
        # filter list
        destinations: List[Optional[Outgoing]] = list(dst)

        if len(sources) != len(destinations):
            # Transform source or destination vector to fit vector length.
            # We support connecting single source to multiple destinations or
            # multiple sources to a single destination.
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

        # Link split sources to cloned destinations.
        return map_sources_to_destinations(sources, src_splits,
                                           destinations, dst_clones)


class FFMPEGFactory:
    """ MyPy-respected FFMPEG factory definition."""

    def __call__(self, **kwargs: Any) -> FFMPEG:
        return FFMPEG(**kwargs)


class SIMD:
    """
    Single Instruction Multiple Data helper for video file processing.

    Handles Vector initialization from source streams and output codecs
    connections.
    """
    ffmpeg_wrapper = FFMPEGFactory()

    def __init__(self, source: inputs.Input, *results: outputs.Output,
                 **kwargs: Any) -> None:
        """
        :param source: input file for ffmpeg.
        :param results: list of ffmpeg output files.
        :param kwargs: ffmpeg command line arguments.
        """
        self.validate_input_file(source)
        for output in results:
            self.validate_output_file(output)
        self.__source = source
        self.__extra: List[inputs.Input] = []
        self.__results = results
        self.__ffmpeg: Optional[FFMPEG] = None
        self.__kwargs = kwargs

    @overload
    def __lt__(self, other: Union[inputs.Stream, filters.Filter, Vector]
               ) -> Vector:
        ...

    @overload
    def __lt__(self, other: inputs.Input) -> inputs.Input:
        ...

    def __lt__(self, other: Union[Vector, inputs.Input, inputs.Stream,
                                  filters.Filter]
               ) -> Union[Vector, inputs.Input]:
        # noinspection PyUnresolvedReferences
        """
        A shortcut to connect additional input file or codec vector.

        >>> simd = SIMD(inputs.input_file('input.mp4'))
        >>> # Adding extra input file
        >>> logo = simd < inputs.input_file('logo.png')
        >>> # Finalizing filter to simd with single stream
        >>> simd | filters.Scale(1280, 720) > simd
        >>> # Finalizing input stream excluded from filter graph
        >>> preroll.audio > simd
        >>> # Finalizing stream vector
        >>> scaled_vector = simd.video.connect(Scale, params=[size1, size2])
        >>> scaled_vector > simd
        """
        if isinstance(other, (inputs.Stream, filters.Filter)):
            # finalizing stream excluded from filter graph or single filtered
            # stream
            other = Vector(other)
        if isinstance(other, Vector):
            return other.connect(self.get_codecs(other.kind))
        elif isinstance(other, inputs.Input):
            return self.add_input(other)
        else:
            # noinspection PyTypeChecker
            return NotImplemented

    def __or__(self, other: filters.Filter) -> Vector:
        """
        A shortcut to connect input file stream to a filter.

        >>> simd = SIMD(inputs.input_file('input.mp4'))
        >>> vector = simd | filters.Scale(1280, 720)
        """
        if not isinstance(other, filters.Filter):
            return NotImplemented
        return Vector(self.get_stream(other.kind)).connect(other)

    @staticmethod
    def validate_input_file(input_file: inputs.Input) -> None:
        """
        Checks that input file contains streams information with stream
        metadata.
        """
        if not input_file.streams:
            raise ValueError("streams must be set for input file")
        for stream in input_file.streams:
            if not stream.meta:
                raise ValueError("stream metadata must be set for input file")

    @staticmethod
    def validate_output_file(output: outputs.Output) -> None:
        """
        Checks that output file contains codec information.
        """
        if not output.codecs:
            raise ValueError("codecs must be set for output file")

    @property
    def ffmpeg(self) -> FFMPEG:
        """
        Initializes ffmpeg wrapper with input/output files and command line
        arguments.

        Note that ffmpeg instance can't be instantiated twice, because existing
        output files could be connected to input streams only once.

        :returns: cached FFMPEG instance.
        """
        if self.__ffmpeg is None:
            self.__ffmpeg = self.ffmpeg_wrapper(
                input=self.__source, **self.__kwargs)

            for source in self.__extra:
                self.__ffmpeg.add_input(source)

            for output in self.__results:
                for codec in output.codecs:
                    if codec.connected:
                        continue
                    self.get_stream(codec.kind).connect_dest(codec)
                self.__ffmpeg.add_output(output)

        return self.__ffmpeg

    @property
    def video(self) -> Vector:
        """
        :returns: a vector with single video input stream
        """
        return Vector(self.get_stream(VIDEO))

    @property
    def audio(self) -> Vector:
        """
        :returns: a vector with single audio input stream
        """
        return Vector(self.get_stream(AUDIO))

    def get_stream(self, kind: StreamType) -> inputs.Stream:
        """
        :param kind: desired stream kind
        :return: first stream of desired kind from input file
        :raises KeyError: if no streams of this kind found.
        """
        for stream in self.__source.streams:
            if stream.kind == kind:
                return stream
        raise KeyError(kind)

    def get_codecs(self, kind: StreamType) -> Vector:
        """
        :param kind: desired vector kind
        :return: a vector of all codecs of desired kind for each output.
        """
        result = []
        for output in self.__results:
            result.append(output.get_free_codec(kind, create=False))
        return Vector(result)

    def add_input(self, source: inputs.Input) -> inputs.Input:
        """
        Adds additional input file to ffmpeg
        :param source: additional input file
        :returns: connected input
        """
        self.validate_input_file(source)
        self.__extra.append(source)
        return source
