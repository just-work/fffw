__all__ = [
    'StreamType',
    'AUDIO',
    'VIDEO',
]

import abc
from collections import Counter
from enum import Enum
from typing import Optional, List, Union, Dict, Any


class StreamType(Enum):
    VIDEO = 'v'
    AUDIO = 'a'


VIDEO = StreamType.VIDEO
AUDIO = StreamType.AUDIO


class Singleton(type):
    stack: List["Namer"]

    @property
    def current(self) -> "Namer":
        return self.stack[0]


class Namer(metaclass=Singleton):
    """ Unique stream identifiers generator."""
    stack: List["Namer"] = []

    def __init__(self) -> None:
        self.counters: Dict[str, int] = Counter()
        self.cache: Dict[int, str] = dict()

    def name(self, edge: "Edge") -> str:
        if id(edge) not in self.cache:
            node = edge.input
            if isinstance(node, Node):
                prefix = f'{node.kind.value}:{node.name}'
                # generating unique edge id by src node kind and name
                name = f'{prefix}{self.counters[prefix]}'
                self.counters[prefix] += 1
            else:
                name = node.name
            # caching edge name for idempotency
            self.cache[id(edge)] = name
        return self.cache[id(edge)]

    def __enter__(self) -> "Namer":
        self.stack.append(self)
        return self.stack[0]

    def __exit__(self, *_: Any) -> None:
        self.stack.pop(-1)


class Renderable(metaclass=abc.ABCMeta):
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


class NameMixin:
    """
    A mixin for single-time object name initialization
    """

    def __init__(self, name: str):
        super().__init__()
        self.__name: str = name

    @property
    def name(self) -> Optional[str]:
        return self.__name


class Dest(Renderable):
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
        self.kind = kind
        self.__name = name

    @property
    def name(self) -> str:
        return self.name

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

    def __repr__(self) -> str:
        return f"Dest('{self.name}')"

    def render(self, partial: bool = False) -> List[str]:
        # Previous nodes/edges already rendered destination node.
        return []


InputType = Union["Source", "Node"]
OutputType = Union["Dest", "Node"]


class Edge(Renderable):
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

        When connected to destination, uses dest name as edge name.
        When connected to other filters, looks for source node, skipping
        disabled nodes.
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
        return Namer.current.name(edge)

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

    def render(self, partial: bool = False) -> List[str]:
        if not self.__output:
            if partial:
                return []
            raise RuntimeError("output is none")
        return self.__output.render(partial=partial)


class Node(Renderable):
    """ Graph node describing ffmpeg filter."""

    kind: StreamType  # filter type (VIDEO/AUDIO)
    name: str  # filter name
    input_count: int = 1  # number of inputs
    output_count: int = 1  # number of outputs

    def __init__(self, enabled: bool = True):
        if not enabled:
            assert self.input_count == 1
            assert self.output_count == 1
        self.__enabled = enabled
        self.inputs: List[Optional[Edge]] = [None] * self.input_count
        self.outputs: List[Optional[Edge]] = [None] * self.output_count

    def __repr__(self) -> str:
        inputs = [f"[{str(i.name if i else '---')}]" for i in self.inputs]
        outputs = [f"[{str(i.name if i else '---')}]" for i in self.outputs]
        return f"{''.join(inputs)}{self.name}{''.join(outputs)}"

    @property
    def enabled(self) -> bool:
        return self.__enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self.__enabled = value

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

    @property
    def args(self) -> str:
        """
        Generates filter params as a string
        """
        return ''

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

    def __or__(self, other: Union["Node", "Dest"]) -> Union["Node", "Dest"]:
        """
        connect output edge to node
        :return: connected edge
        """
        if not isinstance(other, (Node, Dest)):
            return NotImplemented
        return self.connect_dest(other)


class Source(Renderable):
    """ Graph node containing audio or video input.

    Must connect to single graph edge only as a source
    """

    def __init__(self, name: Optional[str], kind: StreamType) -> None:
        """
        :param name: ffmpeg internal input stream name ("v:0", "a:1")
        :param kind: stream type (VIDEO/AUDIO)
        """
        self._edge: Optional[Edge] = None
        self._kind = kind
        self.__name = name

    @property
    def name(self) -> str:
        if self.__name is None:
            raise RuntimeError("Source name not set")
        return self.__name

    @property
    def edge(self) -> Optional["Edge"]:
        """ Returns an edge connected to current source.
        :rtype: fffw.graph.base.Edge|NoneType
        """
        return self._edge

    @property
    def kind(self) -> StreamType:
        """ Returns stream type."""
        return self._kind

    def connect(self, other: Node) -> Node:
        """ Connects a source to a filter or output

        :param other: filter consuming current input stream
        :return filter connected to current stream
        """
        if not isinstance(other, Node):
            raise ValueError("only node allowed")
        if self._edge is not None and not getattr(other, 'map', None):
            raise RuntimeError("Source %s is already connected to %s"
                               % (self.name, self._edge))
        edge = Edge(input=self, output=other)
        self._edge = self._edge or other.connect_edge(edge)
        return other

    def __or__(self, other: Node) -> Node:
        """
        Connect a filter to a source
        :return: connected filter
        """
        if not isinstance(other, Node):
            return NotImplemented
        return self.connect(other)

    def render(self, partial: bool = False) -> List[str]:
        if self._edge is None:
            if partial:
                return []
            raise RuntimeError("Source is not ready for render")

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

    def __repr__(self) -> str:
        return f"Source('[{self.name}]')"
