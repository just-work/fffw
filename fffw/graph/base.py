__all__ = [
    'VIDEO',
    'AUDIO',
]


VIDEO, AUDIO = object(), object()


class Dest:
    """
    Audio/video output stream node.

    Must connect to single filter output only.
    """

    def __init__(self, name, kind):
        """
        :param name: internal ffmpeg stream name ("v:0", "a:1")
        :type name: str
        :param kind: stream kind (VIDEO/AUDIO)
        :type kind: object
        """

        self._name = name
        self._edge = None
        self.kind = kind

    @property
    def id(self):
        """ Returns node identifier used in filter_graph description."""
        return self._name

    def connect_edge(self, edge):
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
        self._edge.id = self.id
        return edge

    def __repr__(self):
        return "Dest('[%s]')" % self.id

    # noinspection PyMethodMayBeStatic,PyUnusedLocal,PyShadowingBuiltins
    def render(self, namer, id=None, partial=False):
        # Previous nodes/edges rendered this already.
        return []


class Edge:
    """ Internal ffmpeg data stream graph."""

    # noinspection PyShadowingBuiltins
    def __init__(self, input=None, output=None):
        """
        :param input: input node
        :type input: Source|Node
        :param output: output node
        :type output: Dest|Node
        """
        self._id = None
        self._input = input
        self._output = output

    def __repr__(self):
        return 'Edge#{id}[{input}, {output}]'.format(
            id=self._id, input=self._input, output=self._output)

    @property
    def id(self):
        return self._id

    @property
    def input(self):
        return self._input

    @property
    def output(self):
        return self._output

    @id.setter
    def id(self, value):
        if self._id is None:
            self._id = value
        else:
            raise RuntimeError("id already set")

    def _connect_source(self, src):
        """ Connects input node to the edge.

        :param src: source stream or filter output node.
        :type src: Source|Node
        :return: None
        """
        if self._input is not None:
            raise ValueError("edge already connected to input %s" % self._input)
        self._input = src

    def _connect_dest(self, dest):
        """ Connects output node to the edge.

        :param dest: output stream or filter input node
        :type dest: Dest|Node
        :return: connected node
        :rtype: Dest|Node
        """
        if self._output is not None:
            raise ValueError("edge already connected to output %s"
                             % self._output)
        self._output = dest
        return dest

    # noinspection PyShadowingBuiltins
    def render(self, namer, id=None, partial=False):
        """ Returns a list of edge descriptions.

        :param namer: callable used to generate unique edge identifiers
        :type namer: (name: str) -> str
        :param id: edge identifier
        :type id: str
        :param partial: partially formatted graph render mode floag
        :type partial: bool
        :return: edge description list ["[v:0]yadif[v:t1]", "[v:t1]scale[out]"]
        :rtype: List[str]
        """
        if not self.id:
            self.id = namer(self._output.name)
        if not self._output and partial:
            return []
        return self._output.render(namer, id=id, partial=partial)


class Node:
    """ Graph node describing ffmpeg filter."""

    kind = None  # filter type (VIDEO/AUDIO)
    name = None  # filter name
    input_count = 1  # number of inputs
    output_count = 1  # number of outputs

    def __init__(self, enabled=True):
        if not enabled:
            assert self.input_count == 1
            assert self.output_count == 1
        self.enabled = enabled
        self.inputs = [None] * self.input_count
        self.outputs = [None] * self.output_count

    def __repr__(self):
        inputs = [('[%s]' % str(i.id if i else '---')) for i in self.inputs]
        outputs = [('[%s]' % str(i.id if i else '---')) for i in self.outputs]
        return '%s%s%s' % (''.join(inputs), self.name, ''.join(outputs))

    # noinspection PyShadowingBuiltins
    def render(self, namer, id=None, partial=False):
        """ Returns a list of edge descriptions.

        First element is a current filter description (see get_filter_cmd)

        :param namer: callable used to generate unique edge identifiers
        :type namer: (name: str) -> str
        :param id: edge identifier
        :type id: str
        :param partial: partially formatted graph render mode floag
        :type partial: bool
        :return: edge description list ["[v:0]yadif[v:t1]", "[v:t1]scale[out]"]
        :rtype: List[str]
        """
        if not self.enabled:
            # filter skipped, input is connected to output directly
            next_edge = self.outputs[0]
            if partial and not next_edge:
                return []
            return next_edge.render(namer, id=id, partial=partial)

        result = [self.get_filter_cmd(namer, id=id, partial=partial)]

        for dest in self.outputs:
            if dest is None and partial:
                continue
            if isinstance(dest.output, Dest):
                continue
            result.extend(dest.render(namer, partial=partial))
        return result

    # noinspection PyShadowingBuiltins
    def get_filter_cmd(self, namer, id=None, partial=False):
        """
        Returns filter description.

        output format is like [IN] FILTER ARGS [OUT]
        where IN, OUT - lists of input/output edge id,
        FILTER - fiter name, ARGS - filter params

        :param namer: callable used to generate unique edge identifiers
        :type namer: (name: str) -> str
        :param id: edge identifier
        :type id: str
        :param partial: partially formatted graph render mode floag
        :type partial: bool
        :return: current description string like "[v:0]yadif[v:t1]"
        :rtype: str
        """
        inputs = []
        outputs = []
        for edge in self.inputs:
            if not edge.id:
                edge.id = namer(self.name)
            inputs.append("[%s]" % str(id or edge.id))

        for edge in self.outputs:
            if edge is None and partial:
                outputs.append('[---]')
                continue
            node = edge.output
            while isinstance(node, Node) and not node.enabled:
                # if next node is disabled, use next edge id
                if node.outputs[0] is None and partial:
                    break
                edge = node.outputs[0]
                node = edge.output
            if not edge.id:
                edge.id = namer(self.name)
            outputs.append("[%s]" % edge.id)
        args = '=' + self.args if self.args else ''
        return ''.join(inputs) + self.name + args + ''.join(outputs)

    @property
    def args(self):
        """ Generates filter params as a string

        :rtype: str
        """
        return ''

    def connect_edge(self, edge):
        """ Connects and edge to one of filter inputs

        :param edge: input stream edge
        :type edge: Edge
        :return: None
        """
        if not isinstance(edge, Edge):
            raise ValueError("only edge allowed")
        self.inputs[self.inputs.index(None)] = edge
        return edge

    def connect_dest(self, other):
        """ Connects next filter or output to one of filter outputs.

        :param other: next filter or output stream
        :type other: Node|Dest
        :return: next filter or output stream, connected to current stream
        :rtype: Node|Dest
        """
        if not isinstance(other, (Node, Dest)):
            raise ValueError("only node and dest allowed")
        edge = Edge(input=self, output=other)
        self.outputs[self.outputs.index(None)] = edge
        other.connect_edge(edge)
        return other

    def __or__(self, other):
        """
        :type other: Node | Dest
        :return: other
        :rtype: Node | Dest
        """
        if not isinstance(other, (Node, Dest)):
            return NotImplemented
        return self.connect_dest(other)


class Source:
    """ Graph node containing audio or video input.

    Must connect to single graph edge only as a source
    """
    def __init__(self, name, kind):
        """
        :param name: ffmpeg internal input stream name ("v:0", "a:1")
        :type name: str|None
        :param kind: stream type (VIDEO/AUDIO)
        :type kind: object
        """
        self._name = name
        self._edge = None
        self._kind = kind

    @property
    def id(self):
        """ Returns node identifier used in filter_graph description."""
        return self._name

    @property
    def edge(self):
        """ Returns an edge connected to current source.
        :rtype: fffw.graph.base.Edge|NoneType
        """
        return self._edge

    @property
    def kind(self):
        """ Returns stream type."""
        return self._kind

    def connect(self, other):
        """ Connects a source to a filter or output

        :param other: filter consuming current input stream
        :type other: fffw.graph.base.Node
        :return filter connected to current stream
        :rtype: fffw.graph.base.Node
        """
        if not isinstance(other, Node):
            raise ValueError("only node allowed")
        if self._edge is not None and not getattr(other, 'map', None):
            raise RuntimeError("Source %s is already connected to %s"
                               % (self.id, self._edge))
        edge = Edge(input=self, output=other)
        edge.id = self.id
        self._edge = self._edge or other.connect_edge(edge)
        return other

    def __or__(self, other):
        """
        :type other: Node
        :return: other
        :rtype: Node
        """
        if not isinstance(other, Node):
            return NotImplemented
        return self.connect(other)

    # noinspection PyShadowingBuiltins
    def render(self, namer, partial=False):
        """ Returns a list of edge descriptions.

        First element is a current filter description (see get_filter_cmd)

        :param namer: callable used to generate unique edge identifiers
        :type namer: (name: str) -> str
        :param id: edge identifier
        :type id: str
        :param partial: partially formatted graph render mode floag
        :type partial: bool
        :return: edge description list ["[v:0]yadif[v:t1]", "[v:t1]scale[out]"]
        :rtype: List[str]
        """
        edge = self._edge
        if partial and not edge:
            return []

        id = edge.id
        node = edge.output
        # if output node is disabled, use next edge identifier.
        if isinstance(node, Node) and not node.enabled:
            edge = node.outputs[0]
        else:
            id = None
        return edge.render(namer, id=id, partial=partial)

    def __repr__(self):
        return "Source('[%s]')" % self.id
