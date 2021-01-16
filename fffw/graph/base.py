import abc
from collections import Counter
from copy import deepcopy
from typing import Dict, Any, TypeVar, Type, overload
from typing import Optional, List, Union

from fffw.graph.meta import Meta, StreamType

InputType = Union["Source", "Node"]
OutputType = Union["Dest", "Node"]


class Traversable(metaclass=abc.ABCMeta):
    """
    Abstract class base for filter graph edges/nodes traversing and rendering.
    """

    @abc.abstractmethod
    def render(self, partial: bool = False) -> List[str]:
        """
        Returns a list of filter_graph edge descriptions.

        This method must be called in Namer context.

        :param partial: partially formatted graph render mode flag
        :return: edge description list ["[v:0]yadif[v:t1]", "[v:t1]scale[out]"]
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_meta_data(self, dst: OutputType) -> Optional[Meta]:
        """
        :param dst: destination node
        :return: metadata passed to destination node after transformation
        """
        raise NotImplementedError()


class Dest(Traversable):
    """
    Audio/video output stream node.

    Must connect to single filter output only.
    """
    kind: StreamType
    _edge: Optional["Edge"] = None

    def __repr__(self) -> str:
        return f"Dest('{self.name}')"

    @property
    def name(self) -> str:
        """
        :returns: edge name (i.e. [vout0]) for codec `-map` argument only.
        """
        if self._edge is None:
            raise RuntimeError("Dest not connected")
        name = self._edge.name
        if ':' in name:
            # dest is connected directly to the source, name is rendered from
            # source ffmpeg stream specifier
            return name
        return f'[{self._edge.name}]'

    @property
    def meta(self) -> Optional[Meta]:
        metadata = self.get_meta_data(self)
        if metadata is None:
            return None
        return self.transform(metadata)

    def transform(self, *metadata: Meta) -> Meta:
        """ Apply codec changes to stream metadata."""
        return metadata[0]

    @property
    def edge(self) -> Optional["Edge"]:
        return self._edge

    def get_meta_data(self, dst: OutputType = None) -> Optional[Meta]:
        if self._edge is None:
            raise RuntimeError("Dest not connected")
        return self._edge.get_meta_data(self)

    def connect_edge(self, edge: "Edge") -> "Edge":
        """ Connects and edge to output stream.

        Should be called only from Node methods. Initializes edge identifier.

        :param edge: edge to connect output stream to.
        :type edge: Edge
        :return None
        """
        if not isinstance(edge, Edge):
            raise ValueError("Only edge allowed")
        if self._edge is not None:
            raise RuntimeError("Dest is already connected to %s" % self._edge)
        self._edge = edge
        return edge

    def render(self, partial: bool = False) -> List[str]:
        # Previous nodes/edges already rendered destination node.
        return []


class Edge(Traversable):
    """ Internal ffmpeg data stream graph."""

    # noinspection PyShadowingBuiltins
    def __init__(self, input: InputType, output: OutputType) -> None:
        """
        :param input: input node
        :param output: output node
        """
        super().__init__()
        self.__input = input
        self.__output = output

    def __repr__(self) -> str:
        return f'Edge#{self.name}[{self.input}, {self.output}]'

    @property
    def kind(self) -> StreamType:
        return self.__input.kind

    @property
    def input(self) -> InputType:
        return self.__input

    @property
    def output(self) -> OutputType:
        return self.__output

    @property
    def name(self) -> str:
        """
        Get actual name for edge from source node.

        Property must be accessed within Namer context.

        :returns: edge identifier generated from output node name if connected
        to Dest, or a  name of last enabled filter before (and including)
        current node.
        """
        # For edges connected to other filters disabled source nodes are skipped
        edge = self
        node = self.input
        while not getattr(node, 'enabled', True) and isinstance(node, Node):
            if node.inputs[0] is None:
                raise RuntimeError("Node input is None")
            edge = node.inputs[0]
            node = edge.input
        if isinstance(self.output, Dest):
            if isinstance(node, Source):
                # If a Dest is connected directly to a source, render source
                # node name as ffmpeg stream specifier, i.e. '0:v'
                return node.name
            else:
                # For final edges name is generated from destination node, like
                # [vout0] or [aout1]
                return Namer.name(self)
        return Namer.name(edge)

    def _connect_source(self, src: InputType) -> None:
        """ Connects input node to the edge.

        :param src: source stream or filter output node.
        """
        if self.__input is not None:
            raise RuntimeError("edge already connected to input %s"
                               % self.__input)
        self.__input = src

    @overload
    def _connect_dest(self, dest: "Node") -> "Node":
        ...

    @overload
    def _connect_dest(self, dest: Dest) -> Dest:
        ...

    def _connect_dest(self, dest: OutputType) -> OutputType:
        """ Connects output node to the edge.

        :param dest: output stream or filter input node
        :return: connected node
        """
        if self.__output is not None:
            raise RuntimeError("edge already connected to output %s"
                               % self.__output)
        self.__output = dest
        return dest

    def get_meta_data(self, dst: OutputType) -> Optional[Meta]:
        return self.__input.get_meta_data(dst)

    def render(self, partial: bool = False) -> List[str]:
        if not self.__output:
            if partial:
                return []
            raise RuntimeError("output is none")
        return self.__output.render(partial=partial)

    def reconnect(self, dest: OutputType) -> None:
        """
        Allows to detach an edge from one output and connect to another one.
        """
        if isinstance(self.__output, Node):
            inputs = self.__output.inputs
            inputs[inputs.index(self)] = None
        self.__output = dest
        dest.connect_edge(self)


D = TypeVar('D', bound=Dest)


class Node(Traversable, abc.ABC):
    """ Graph node describing ffmpeg filter."""
    # Should be overridden in derived classes
    kind: StreamType  # filter type (VIDEO/AUDIO)
    filter: str  # filter name

    input_count: int = 1  # number of inputs
    output_count: int = 1  # number of outputs

    def __repr__(self) -> str:
        inputs = [f"[{str(i.name if i else '---')}]" for i in self.inputs]
        outputs = [f"[{str(i.name if i else '---')}]" for i in self.outputs]
        return f"{''.join(inputs)}{self.filter}{''.join(outputs)}"

    def __or__(self, other: "Node") -> "Node":
        """
        connect output edge to node
        :return: connected node
        """
        if not isinstance(other, Node):
            return NotImplemented
        return self.connect_dest(other)

    def __gt__(self, other: Dest) -> Dest:
        """
        connects output edge to destination
        :param other: destination codec
        :return: connected codec
        """
        if not isinstance(other, Dest):
            return NotImplemented
        return self.connect_dest(other)

    @property
    @abc.abstractmethod
    def args(self) -> str:
        raise NotImplementedError()

    @property
    def inputs(self) -> List[Optional[Edge]]:
        """
        :returns: list of placeholders for input edges.
        """
        if 'inputs' not in self.__dict__:
            self.__dict__['inputs'] = [None] * self.input_count
        return self.__dict__['inputs']

    @property
    def outputs(self) -> List[Optional[Edge]]:
        """
        :returns: list of placeholders for output edges.
        """
        if 'outputs' not in self.__dict__:
            self.__dict__['outputs'] = [None] * self.output_count
        return self.__dict__['outputs']

    @property
    def enabled(self) -> bool:
        return self.__dict__.get('enabled', True)

    @enabled.setter
    def enabled(self, value: bool) -> None:
        if not value:
            assert self.input_count == 1
            assert self.output_count == 1
        self.__dict__['enabled'] = value

    @property
    def meta(self) -> Optional[Meta]:
        """ Compute metadata for current node."""
        metadata = []
        for edge in self.inputs:
            if edge is None:
                raise RuntimeError("Input not connected")
            meta = edge.get_meta_data(self)
            if meta is None:
                return None
            metadata.append(meta)

        return self.transform(*metadata)

    # noinspection PyMethodMayBeStatic
    def transform(self, *metadata: Meta) -> Meta:
        """ Apply filter changes to stream metadata."""
        return metadata[0]

    def get_meta_data(self, dst: OutputType) -> Optional[Meta]:
        """ Returns metadata for selected destination."""
        for edge in self.outputs:
            if edge is None:
                continue
            if edge.output is dst:
                return self.meta
        else:
            raise KeyError(dst)

    def render(self, partial: bool = False) -> List[str]:
        if not self.enabled:
            # filter skipped, input is connected to output directly
            next_edge = self.outputs[0]
            if next_edge is None:
                if partial:
                    return []
                raise RuntimeError("output is None")
            return next_edge.render(partial=partial)

        result = [self.get_filter_cmd(partial=partial)]

        for dest in self.outputs:
            if dest is None:
                if partial:
                    continue
                raise RuntimeError("destination is none")
            if isinstance(dest.output, Dest):
                continue
            result.extend(dest.render(partial=partial))
        return result

    def get_filter_cmd(self, partial: bool = False) -> str:
        """
        Returns filter description.

        output format is like [IN] FILTER ARGS [OUT]
        where IN, OUT - lists of input/output edge id,
        FILTER - filter name, ARGS - filter params

        :param partial: partially formatted graph render mode flag
        :return: current description string like "[v:0]yadif[v:t1]"
        """
        inputs = []
        outputs = []
        for edge in self.inputs:
            if edge is None:
                raise RuntimeError("input is none")
            # Add Source name (i.e. 0:v) or unique node name (v:scale1) as
            # filter input.
            inputs.append(f'[{edge.name}]')

        for edge in self.outputs:
            if edge is None:
                if partial:
                    # outputs not connected, using a stub.
                    outputs.append('[---]')
                    continue
                raise RuntimeError("output is none")
            # Skip outgoing disabled nodes till Dest node, to get proper
            # output name if current node is last enabled before destination.
            node = edge.output
            while isinstance(node, Node) and not node.enabled:
                # if next node is disabled, use next edge id
                if node.outputs[0] is None and partial:
                    break
                edge = node.outputs[0]
                if edge is None:
                    raise RuntimeError("output is none")
                node = edge.output
            # Add unique output edge name (vout0 or a:volume1) to filter output
            outputs.append(f"[{edge.name}]")
        args = '=' + self.args if self.args else ''
        return ''.join(inputs) + self.filter + args + ''.join(outputs)

    def connect_edge(self, edge: "Edge") -> "Edge":
        """ Connects and edge to one of filter inputs

        :param edge: input stream edge
        :returns: connected edge
        """
        if not isinstance(edge, Edge):
            raise ValueError("only edge allowed")
        self.inputs[self.inputs.index(None)] = edge
        return edge

    @overload
    def connect_dest(self, other: "Node") -> "Node":
        ...

    @overload
    def connect_dest(self, other: Dest) -> Dest:
        ...

    def connect_dest(self, other: OutputType) -> OutputType:
        """ Connects next filter or output to one of filter outputs.

        :param other: next filter or output stream
        :return: next filter or output stream, connected to current stream
        """
        if not isinstance(other, (Node, Dest)):
            raise ValueError("only node and dest allowed")
        edge = Edge(input=self, output=other)
        self.outputs[self.outputs.index(None)] = edge
        other.connect_edge(edge)
        return other


N = TypeVar('N', bound=Node)


class Source(Traversable, metaclass=abc.ABCMeta):
    """ Graph node containing audio or video input.

    Must connect to single graph edge only as a source
    """

    def __init__(self, kind: StreamType,
                 meta: Optional[Meta] = None) -> None:
        """
        :param kind: stream type (VIDEO/AUDIO)
        :param meta: stream metadata
        """
        self._outputs: List[Edge] = []
        self._kind = kind
        self._meta = deepcopy(meta)

    def __repr__(self) -> str:
        return f"Source('[{self.name}]')"

    def __or__(self, other: N) -> N:
        """
        Connect a filter to a source
        :return: connected filter
        """
        if not isinstance(other, Node):
            return NotImplemented
        return self.connect_dest(other)

    def __gt__(self, other: D) -> D:
        """
        Connects a codec to a source
        :param other: codec that will process current source stream
        :return: destination object
        """
        if not isinstance(other, Dest):
            return NotImplemented
        return self.connect_dest(other)

    @property
    def connected(self) -> bool:
        return bool(self._outputs)

    @property
    @abc.abstractmethod
    def name(self) -> str:
        raise NotImplementedError()

    @property
    def kind(self) -> StreamType:
        """
        :returns: stream type
        """
        return self._kind

    @property
    def meta(self) -> Optional[Meta]:
        """
        :returns: stream metadata
        """
        return self._meta

    @overload
    def connect_dest(self, other: N) -> N:
        ...

    @overload
    def connect_dest(self, other: D) -> D:
        ...

    def connect_dest(self, other: OutputType) -> OutputType:
        if not isinstance(other, (Node, Dest)):
            raise ValueError("only node or dest allowed")
        edge = Edge(input=self, output=other)
        other.connect_edge(edge)
        self._outputs.append(edge)
        return other

    def get_meta_data(self, dst: OutputType) -> Optional[Meta]:
        return self._meta

    def render(self, partial: bool = False) -> List[str]:
        result = []
        edge: Optional[Edge]
        for edge in self._outputs:
            node = edge.output
            # if output node is disabled, use next edge identifier.
            if isinstance(node, Node) and not node.enabled:
                edge = node.outputs[0]
                if edge is None:
                    if partial:
                        return []
                    raise RuntimeError("Skipped node is not ready for render")
            result.extend(edge.render(partial=partial))
        return result


Obj = TypeVar('Obj')


class Once:
    """ Property that must be set exactly once."""

    def __init__(self, attr_name: str) -> None:
        """
        :param attr_name: instance attribute name
        """
        self.attr_name = attr_name

    def __get__(self, instance: Obj, owner: Type[Obj]) -> Any:
        try:
            return instance.__dict__[self.attr_name]
        except KeyError:
            raise RuntimeError(f"{self.attr_name} is not initialized")

    def __set__(self, instance: Obj, value: Any) -> None:
        if self.attr_name in instance.__dict__:
            raise RuntimeError(f"{self.attr_name} already initialized")
        instance.__dict__[self.attr_name] = value


class Namer:
    """ Unique stream identifiers generator."""
    _stack: List["Namer"] = []

    @classmethod
    def name(cls, obj: Edge) -> str:
        current = cls._stack[0]
        return current._name(obj)

    def __init__(self) -> None:
        self._counters: Dict[str, int] = Counter()
        self._cache: Dict[int, str] = dict()

    def __enter__(self) -> "Namer":
        self._stack.append(self)
        return self._stack[0]

    def __exit__(self, *_: Any) -> None:
        self._stack.pop(-1)

    def _name(self, edge: Edge) -> str:
        """
        Generates name for an edge in filter graph.

        :param edge: edge that needs to be named
        :returns: unique Dest name if edge leads to destination (i.e. vout0),
        Source name if edge starts from input stream (i.e. 0:v) or unique
        input Node name generated from node filter (i.e. v:overlay1).
        """
        if id(edge) not in self._cache:
            src = edge.input
            dst = edge.output
            if isinstance(dst, Dest):
                prefix = f'{dst.kind.value}out'
                # generating unique edge id by dst kind
                name = f'{prefix}{self._counters[prefix]}'
                self._counters[prefix] += 1
            elif isinstance(src, Node):
                prefix = f'{src.kind.value}:{src.filter}'
                # generating unique edge id by src node kind and name
                name = f'{prefix}{self._counters[prefix]}'
                self._counters[prefix] += 1
            else:
                name = f'{src.name}'
            # caching edge name for idempotency
            self._cache[id(edge)] = name
        return self._cache[id(edge)]
