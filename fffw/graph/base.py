__all__ = [
    'StreamType',
    'AUDIO',
    'VIDEO',
]

import abc
from collections import Counter
from enum import Enum
from typing import Dict, Any, TypeVar, Type, overload
from typing import Optional, List, Union

from fffw.graph.meta import Meta


class StreamType(Enum):
    VIDEO = 'v'
    AUDIO = 'a'


VIDEO = StreamType.VIDEO
AUDIO = StreamType.AUDIO


class Namer:
    """ Unique stream identifiers generator."""
    _stack: List["Namer"] = []

    @classmethod
    def name(cls, edge: "Edge") -> str:
        current = cls._stack[0]
        return current._name(edge)

    def __init__(self) -> None:
        self._counters: Dict[str, int] = Counter()
        self._cache: Dict[int, str] = dict()

    def __enter__(self) -> "Namer":
        self._stack.append(self)
        return self._stack[0]

    def __exit__(self, *_: Any) -> None:
        self._stack.pop(-1)

    def _name(self, edge: "Edge") -> str:
        if id(edge) not in self._cache:
            node = edge.input
            if isinstance(node, Node):
                prefix = f'{node.kind.value}:{node.name}'
                # generating unique edge id by src node kind and name
                name = f'{prefix}{self._counters[prefix]}'
                self._counters[prefix] += 1
            else:
                name = node.name
            # caching edge name for idempotency
            self._cache[id(edge)] = name
        return self._cache[id(edge)]


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

    def __init__(self, name: str, kind: StreamType) -> None:
        """
        :param name: internal ffmpeg stream name ("v:0", "a:1")
        :param kind: stream kind (VIDEO/AUDIO)
        """
        self._edge: Optional[Edge] = None
        self._kind = kind
        self._name = name

    def __repr__(self) -> str:
        return f"Dest('{self.name}')"

    @property
    def name(self) -> str:
        return self._name

    @property
    def kind(self) -> StreamType:
        return self._kind

    @property
    def meta(self) -> Optional[Meta]:
        return self.get_meta_data(self)

    @property
    def edge(self) -> Optional["Edge"]:
        return self._edge

    def get_meta_data(self, dst: OutputType) -> Optional[Meta]:
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
        if isinstance(self.output, Dest):
            return self.output.name
        edge = self
        node = self.input
        while not getattr(node, 'enabled', True) and isinstance(node, Node):
            if node.inputs[0] is None:
                raise RuntimeError("Node input is None")
            edge = node.inputs[0]
            node = edge.input
        return Namer.name(edge)

    def _connect_source(self, src: Union["Source", "Node"]) -> None:
        """ Connects input node to the edge.

        :param src: source stream or filter output node.
        """
        if self.__input is not None:
            raise RuntimeError("edge already connected to input %s"
                               % self.__input)
        self.__input = src

    def _connect_dest(self,
                      dest: Union["Dest", "Node"]) -> Union["Dest", "Node"]:
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


class Node(Traversable):
    """ Graph node describing ffmpeg filter."""

    kind: StreamType  # filter type (VIDEO/AUDIO)
    name: str  # filter name
    input_count: int = 1  # number of inputs
    output_count: int = 1  # number of outputs

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.inputs: List[Optional[Edge]] = [None] * self.input_count
        self.outputs: List[Optional[Edge]] = [None] * self.output_count

    def __repr__(self) -> str:
        inputs = [f"[{str(i.name if i else '---')}]" for i in self.inputs]
        outputs = [f"[{str(i.name if i else '---')}]" for i in self.outputs]
        return f"{''.join(inputs)}{self.name}{''.join(outputs)}"

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
    def enabled(self) -> bool:
        return self.__enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        if not value:
            assert self.input_count == 1
            assert self.output_count == 1
        self.__enabled = value

    @property
    def args(self) -> str:
        """
        Generates filter params as a string
        """
        return ''

    # noinspection PyMethodMayBeStatic
    def transform(self, *metadata: Meta) -> Meta:
        """ Apply filter changes to stream metadata."""
        return metadata[0]

    def get_meta_data(self, dst: OutputType) -> Optional[Meta]:
        metadata = []
        for edge in self.inputs:
            if edge is None:
                raise RuntimeError("Input not connected")
            meta = edge.get_meta_data(self)
            if meta is None:
                return None
            metadata.append(meta)

        meta = self.transform(*metadata)

        for edge in self.outputs:
            if edge is None:
                continue
            if edge.output is dst:
                return meta
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
            inputs.append(f"[{edge.name}]")

        for edge in self.outputs:
            if edge is None:
                if partial:
                    outputs.append('[---]')
                    continue
                raise RuntimeError("output is none")
            node = edge.output
            while isinstance(node, Node) and not node.enabled:
                # if next node is disabled, use next edge id
                if node.outputs[0] is None and partial:
                    break
                edge = node.outputs[0]
                if edge is None:
                    raise RuntimeError("output is none")
                node = edge.output
            outputs.append(f"[{edge.name}]")
        args = '=' + self.args if self.args else ''
        return ''.join(inputs) + self.name + args + ''.join(outputs)

    def connect_edge(self, edge: "Edge") -> "Edge":
        """ Connects and edge to one of filter inputs

        :param edge: input stream edge
        :returns: connected edge
        """
        if not isinstance(edge, Edge):
            raise ValueError("only edge allowed")
        self.inputs[self.inputs.index(None)] = edge
        return edge

    def connect_dest(self,
                     other: Union["Node", "Dest"]) -> Union["Node", "Dest"]:
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


class Source(Traversable):
    """ Graph node containing audio or video input.

    Must connect to single graph edge only as a source
    """

    def __init__(self, name: Optional[str], kind: StreamType,
                 meta: Optional[Meta] = None) -> None:
        """
        :param name: ffmpeg internal input stream name ("v:0", "a:1")
        :param kind: stream type (VIDEO/AUDIO)
        :param meta: stream metadata
        """
        self._edge: Optional[Edge] = None
        self._destinations: List[Edge] = []
        self._kind = kind
        self._name = name
        self._meta = meta

    def __repr__(self) -> str:
        return f"Source('[{self.name}]')"

    def __or__(self, other: Node) -> Node:
        """
        Connect a filter to a source
        :return: connected filter
        """
        if not isinstance(other, Node):
            return NotImplemented
        return self.connect_edge(other)

    def __gt__(self, other: Dest) -> Dest:
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
        return bool(self._edge or self._destinations)

    @property
    def name(self) -> str:
        if self._name is None:
            raise RuntimeError("Source name not set")
        return self._name

    @property
    def edge(self) -> Optional["Edge"]:
        """
        :returns: an edge connected to current source.
        """
        return self._edge

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

    def connect_edge(self, other: Node) -> Node:
        # FIXME: check dest?
        if self._edge is not None:
            raise RuntimeError("Source %s is already connected to %s"
                               % (self.name, self._edge))
        edge = Edge(input=self, output=other)
        self._edge = other.connect_edge(edge)
        return other

    def connect_dest(self, other: Dest) -> Dest:
        # FIXME: check edge?
        if not isinstance(other, Dest):
            raise ValueError("only node or dest allowed")
        edge = Edge(input=self, output=other)
        other.connect_edge(edge)
        self._destinations.append(edge)
        return other

    def get_meta_data(self, dst: OutputType) -> Optional[Meta]:
        return self._meta

    def render(self, partial: bool = False) -> List[str]:
        if self._edge is None:
            return []

        node = self._edge.output
        # if output node is disabled, use next edge identifier.
        if isinstance(node, Node) and not node.enabled:
            edge: Optional[Edge] = node.outputs[0]
            if edge is None:
                if partial:
                    return []
                raise RuntimeError("Skipped node is not ready for render")
        else:
            edge = self._edge
        return edge.render(partial=partial)


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
