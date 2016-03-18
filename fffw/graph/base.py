# coding: utf-8

# $Id: $


VIDEO, AUDIO = object(), object()


class Dest(object):
    """ Вершина, соответстсвующая выходному аудио или видео потоку.

    Должна подключаться ровно к одному выводу фильтра
    """

    def __init__(self, name, kind):
        """
        :param name: внутреннее имя потока ("v:0", "a:1")
        :type name: str
        :param kind: тип потока VIDEO или AUDIO
        :type kind: object
        """

        self._name = name
        self._edge = None
        self.kind = kind

    @property
    def id(self):
        """ Возвращает идентификатор вершины для использования в описании
        filter_graph."""
        return self._name

    def connect_edge(self, edge):
        """ Подсоединяет к выходному потоку ребро графа.

        Должна вызываться только из методов Node.
        При подсоединении присваивает ребру идентификатор.

        :param edge: ребро, к которому необходимо подсоединить выходной поток
        :type edge: Edge
        :return None
        """
        if not isinstance(edge, Edge):
            raise ValueError("Only edge allowed")
        if self._edge is not None:
            raise RuntimeError("Dest is already connected to %s" % self._edge)
        self._edge = edge
        self._edge.id = self.id

    def __repr__(self):
        return "Dest('[%s]')" % self.id

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def render(self, namer):
        # за него уже все отрендерели
        return []


class Edge(object):
    """ Ребро графа, описывающее поток данных внутри ffmpeg."""

    # noinspection PyShadowingBuiltins
    def __init__(self, input=None, output=None):
        """
        :param input: входная вершина
        :type input: Source|Node
        :param output: выходная вершина
        :type output: Dest|Node
        """
        self._id = None
        self._input = input
        self._output = output

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
        """ Подключает вершину к ребру в качестве источника.

        :param src: подключаемый исходный поток или фильтр
        :type src: Source|Node
        :return: None
        """
        if self._input is not None:
            raise ValueError("edge already connected to input %s" % self._input)
        self._input = src

    def _connect_dest(self, dest):
        """ Подключает вершину к ребру в качестве выходного потока.

        :param dest: подключаемый выходной поток или фильтр
        :type dest: Dest|Node
        :return: возвращает подключенную вершину
        :rtype: Dest|Node
        """
        if self._output is not None:
            raise ValueError("edge already connected to output %s"
                             % self._output)
        self._output = dest
        return dest

    def render(self, namer):
        """ Возвращает список описаний ребер графа в виде строк

        :param namer: функция, генерирующая уникальные идентификаторы ребер
        :type namer: (name: str) -> str
        :return: список описаний вида "[v:0]yadif[v:t1]", "[v:t1]scale[out]"
        :rtype: List[str]
        """
        if not self.id:
            self.id = namer(self._output.name)
        return self._output.render(namer)


class Node(object):
    """ Вершина графа, описывающая фильтр ffmpeg."""

    kind = None  # тип фильтра
    name = None  # название фильтра
    input_count = 1  # количество входов
    output_count = 1  # количество выходов

    def __init__(self, enabled=True):
        if not enabled:
            assert self.input_count == 1
            assert self.output_count == 1
        self.enabled = enabled
        self.inputs = [None] * self.input_count
        self.outputs = [None] * self.output_count

    def render(self, namer):
        """ Возвращает список описаний ребер графа в виде строк

        Первым элементом списка является строка, соответствующая текущему
        фильтру (см. get_filter_cmd)

        :param namer: функция, генерирующая уникальные идентификаторы ребер
        :type namer: (name: str) -> str
        :return: список описаний вида "[v:0]yadif[v:t1]", "[v:t1]scale[out]"
        :rtype: List[str]
        """
        if not self.enabled:
            return self.outputs[0].render(namer)

        result = [self.get_filter_cmd(namer)]

        for dest in self.outputs:
            if isinstance(dest.output, Dest):
                continue
            result.extend(dest.render(namer))
        return result

    def get_filter_cmd(self, namer):
        """ Возвращает строку-описание фильтра.

        Возвращаемое значение имеет формат [IN] FILTER ARGS [OUT]
        где IN, OUT - списки id ребер входов и выходов соответственно,
        FILTER - название фильтра, ARGS - параметры фильтра

        :param namer: функция, генерирующая уникальные идентификаторы ребер
        :type namer: (str) -> str
        :return: строка-описание текущего фильтра
        :rtype: str
        """
        inputs = []
        outputs = []
        for edge in self.inputs:
            if not edge.id:
                edge.id = namer(self.name)
            inputs.append("[%s]" % edge.id)

        for edge in self.outputs:
            node = edge.output
            if isinstance(node, Node) and not node.enabled:
                # если следующая вершина у графа выключена, используем
                # id ребра, следующего за ней
                edge = node.outputs[0]
            if not edge.id:
                edge.id = namer(self.name)
            outputs.append("[%s]" % edge.id)
        return ''.join(inputs) + self.name + self.args + ''.join(outputs)

    @property
    def args(self):
        """ Генерирует список параметров фильтра в виде строки.

        :rtype: str
        """
        return ''

    def connect_edge(self, edge):
        """ Подключает ребро к одному из своих входов

        :param edge: ребро, соответствующее источнику данных
        :type edge: Edge
        :return: None
        """
        if not isinstance(edge, Edge):
            raise ValueError("only edge allowed")
        self.inputs[self.inputs.index(None)] = edge

    def connect_dest(self, other):
        """ Подключает другой фильтр или выходной поток к одному из выходов.

        :param other: следующий по цепочке фильтр или выходной поток
        :type other: Node|Dest
        :return: фильтр, подключенный к текущему
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


class Source(object):
    """ Вершина, соответствующая исходному потоку аудио или видео данных.

    Должен подключаться ровно к одному ребру графа
    """
    def __init__(self, name, kind):
        """
        :param name: внутреннее имя потока ("v:0", "a:1")
        :type name: str
        :param kind: тип потока VIDEO или AUDIO
        :type kind: object
        """
        self._name = name
        self._edge = None
        self._kind = kind

    @property
    def id(self):
        """ Возвращает идентификатор вершины для использования в описании
        filter_graph."""
        return self._name

    @property
    def edge(self):
        """ Возвращает ребро, подключенное к источнику
        :rtype: fffw.graph.base.Edge|NoneType
        """
        return self._edge

    @property
    def kind(self):
        """ Возвращает тип потока """
        return self._kind

    def connect(self, other):
        """ Подсоединяет источник к входу фильтра

        :param other: фильтр, потребляющий данный источник
        :type other: fffw.graph.base.Node
        :return возвращает фильтр, к которому подсоединен источник
        :rtype: fffw.graph.base.Node
        """
        if not isinstance(other, Node):
            raise ValueError("only node allowed")
        if self._edge is not None:
            raise RuntimeError("Source %s is already connected to %s"
                               % (self.id, self._edge))
        self._edge = Edge(input=self, output=other)
        self._edge.id = self.id
        other.connect_edge(self._edge)
        return other

    def render(self, namer):
        """ Возвращает список описаний ребер графа в виде строк

        :param namer: функция, генерирующая уникальные идентификаторы ребер
        :type namer: (name: str) -> str
        :return: список описаний вида "[v:0]yadif[v:t1]", "[v:t1]scale[out]"
        :rtype: List[str]
        """
        edge = self._edge
        node = edge.output
        # если следующая вершина отключена, используем ID ребра, следующего
        # за ней
        if isinstance(node, Node) and not node.enabled:
            edge = node.outputs[0]
        return edge.render(namer)

    def __repr__(self):
        return "Source('[%s]')" % self.id


class Input(object):
    """ Хелпер для группировки входных потоков по типам."""
    def __init__(self, streams, kind):
        """
        :type streams: List[Source]
        """
        self.streams = streams
        self.kind = kind

    def connect_dest(self, other):
        """ Подключает первый неподключенный источник к фильтру
        :param other: фильтр
        :type other: Node
        :return подключенный фильтр
        :rtype: Node
        """

        for stream in self.streams:
            if stream.edge is None:
                return stream.connect(other)
        raise IndexError("No free sources")

    def __or__(self, other):
        """
        :type other: Node
        :rtype: Node
        """
        if not isinstance(other, Node):
            return NotImplemented
        return self.connect_dest(other)
