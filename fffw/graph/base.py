__all__ = [
    'StreamType',
    'AUDIO',
    'VIDEO',
]

import abc
from enum import Enum, auto
from typing import Callable, Optional, List, Union


class StreamType(Enum):
    VIDEO = auto()
    AUDIO = auto()


VIDEO = StreamType.VIDEO
AUDIO = StreamType.AUDIO

Namer = Callable[[str], str]
""" Callable type for generating unique stream identifiers."""


class Renderable(metaclass=abc.ABCMeta):
    """
    Abstract class base for filter graph edges/nodes traversing and rendering.
    """

    @abc.abstractmethod
    def render(self,
               namer: Namer,
               name: Optional[str] = None,
               partial: bool = False) -> List[str]:
        """ Returns a list of filter_graph edge descriptions.

        :param namer: callable used to generate unique edge identifiers
        :param name: edge identifier
        :param partial: partially formatted graph render mode floag
        :return: edge description list ["[v:0]yadif[v:t1]", "[v:t1]scale[out]"]
        """
        raise NotImplementedError()


class NameMixin:
    """
    A mixin for single-time object name initialization
    """

    def __init__(self, name: Optional[str] = None):
        super().__init__()
        self.__name: Optional[str] = name

    @property
    def name(self) -> Optional[str]:
        return self.__name

    @name.setter
    def name(self, value: str) -> None:
        """ Set name only once."""
        if self.__name is not None:
            raise RuntimeError("Name is already set")
        self.__name = value


class Dest(Renderable, NameMixin):
    """
    Audio/video output stream node.

    Must connect to single filter output only.
    """

    def __init__(self, name: str, kind: StreamType) -> None:
        """
        :param name: internal ffmpeg stream name ("v:0", "a:1")
        :param kind: stream kind (VIDEO/AUDIO)
        """
        super().__init__(name=name)
        self._edge: Optional[Edge] = None
        self.kind = kind

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
        self._edge.name = self.name
        return edge

    def __repr__(self) -> str:
        return f"Dest('{self.name}')"

    def render(self, namer: Namer, name: Optional[str] = None,
               partial: bool = False) -> List[str]:
        # Previous nodes/edges already rendered destination node.
        return []


InputType = Union[None, "Source", "Node"]
OutputType = Union[None, "Dest", "Node"]


class Edge(Renderable, NameMixin):
    """ Internal ffmpeg data stream graph."""

    # noinspection PyShadowingBuiltins
    def __init__(self,
                 input: InputType = None,
                 output: OutputType = None) -> None:
        """
        :param input: input node
        :param output: output node
        """
        super().__init__()
        self.__input = input
        self.__output = output

    def __repr__(self):
        return f'Edge#{self.name}[{self.input}, {self.output}]'

    @property
    def input(self):
        return self.__input

    @property
    def output(self):
        return self.__output

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

    def render(self,
               namer: Namer,
               name: Optional[str] = None,
               partial: bool = False) -> List[str]:
        if not self.__output:
            if partial:
                return []
            raise RuntimeError("output is none")
        if self.name is None:
            if self.__output.name is None:
                raise RuntimeError("output name is not set")
            self.name = namer(self.__output.name)
        return self.__output.render(namer, name=name, partial=partial)


class Node(Renderable):
    """ Graph node describing ffmpeg filter."""

    kind: StreamType  # filter type (VIDEO/AUDIO)
    name: str  # filter name
    input_count: int = 1  # number of inputs
    output_count: int = 1  # number of outputs

    def __init__(self, enabled=True):
        if not enabled:
            assert self.input_count == 1
            assert self.output_count == 1
        self.enabled = enabled
        self.inputs: List[Optional[Edge]] = [None] * self.input_count
        self.outputs: List[Optional[Edge]] = [None] * self.output_count

    def __repr__(self):
        inputs = [f"[{str(i.name if i else '---')}]" for i in self.inputs]
        outputs = [f"[{str(i.name if i else '---')}]" for i in self.outputs]
        return f"{''.join(inputs)}{self.name}{''.join(outputs)}"

    def render(self, namer: Namer, name: Optional[str] = None,
               partial: bool = False) -> List[str]:
        if not self.enabled:
            # filter skipped, input is connected to output directly
            next_edge = self.outputs[0]
            if next_edge is None:
                if partial:
                    return []
                raise RuntimeError("output is None")
            return next_edge.render(namer, name=name, partial=partial)

        result = [self.get_filter_cmd(namer, gid=name, partial=partial)]

        for dest in self.outputs:
            if dest is None:
                if partial:
                    continue
                raise RuntimeError("destination is none")
            if isinstance(dest.output, Dest):
                continue
            result.extend(dest.render(namer, partial=partial))
        return result

    # noinspection PyShadowingBuiltins
    def get_filter_cmd(self, namer: Namer,
                       gid: Optional[str] = None,
                       partial: bool = False) -> str:
        """
        Returns filter description.

        output format is like [IN] FILTER ARGS [OUT]
        where IN, OUT - lists of input/output edge id,
        FILTER - fiter name, ARGS - filter params

        :param namer: callable used to generate unique edge identifiers
        :param gid: edge identifier
        :param partial: partially formatted graph render mode floag
        :return: current description string like "[v:0]yadif[v:t1]"
        """
        inputs = []
        outputs = []
        for edge in self.inputs:
            if edge is None:
                raise RuntimeError("input is none")
            if edge.name is None:
                edge.name = namer(self.name)
            inputs.append("[%s]" % str(gid or edge.name))

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
            if edge.name is None:
                edge.name = namer(self.name)
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


class Source(Renderable, NameMixin):
    """ Graph node containing audio or video input.

    Must connect to single graph edge only as a source
    """

    def __init__(self, name: Optional[str], kind: StreamType) -> None:
        """
        :param name: ffmpeg internal input stream name ("v:0", "a:1")
        :param kind: stream type (VIDEO/AUDIO)
        """
        super().__init__(name=name)
        self._edge: Optional[Edge] = None
        self._kind = kind

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
        edge.name = self.name
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

    def render(self,
               namer: Namer,
               name: Optional[str] = None,
               partial: bool = False) -> List[str]:
        if self._edge is None:
            if partial:
                return []
            raise RuntimeError("Source is not ready for render")

        node = self._edge.output
        # if output node is disabled, use next edge identifier.
        if isinstance(node, Node) and not node.enabled:
            name = self._edge.name
            edge: Optional[Edge] = node.outputs[0]
            if edge is None:
                if partial:
                    return []
                raise RuntimeError("Skipped node is not ready for render")
        else:
            edge = self._edge
            name = None
        return edge.render(namer, name=name, partial=partial)

    def __repr__(self):
        return f"Source('[{self.name}]')"
