import collections

from fffw.graph.meta import StreamType
from fffw.graph import base
from fffw.encoding import inputs, outputs

__all__ = [
    'FilterComplex'
]


class FilterComplex:
    """ ffmpeg filter graph wrapper."""

    def __init__(self, input_list: inputs.InputList,
                 output_list: outputs.OutputList):
        """
        :param input_list: list of input files, containing video and audio
        streams.
        :param output_list: list of output files, with codecs defined.
        """
        self.__input_list = input_list
        self.__output_list = output_list

    def get_free_source(self, kind: StreamType) -> base.Source:
        """
        :param kind: stream type
        :return: first stream of this kind not connected to filter graph
        """
        for stream in self.__input_list.streams:
            if stream.kind != kind or stream.connected:
                continue
            return stream
        else:
            raise RuntimeError("No free streams")

    def render(self, partial: bool = False) -> str:
        """
        Returns filter_graph description in corresponding ffmpeg param syntax.
        """
        result = []
        with base.Namer():
            # Initialize namer context to track unique edge identifiers.
            # In name generation there is no access to namer, so it is accessed
            # via Namer singleton's method. Within context it is guaranteed that
            # same edges will receive same names and different edges will
            # receive unique names. This includes idempotent results for
            # subsequent render() calls for outer Namer context.
            for src in self.__input_list.streams:
                result.extend(src.render(partial=partial))

        # There are no visit checks in recurse graph traversing, so remove
        # duplicates respecting order of appearance.
        return ';'.join(collections.OrderedDict.fromkeys(result))

    def __str__(self) -> str:
        return self.render()
