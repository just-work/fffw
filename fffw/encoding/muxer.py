from typing import List, Any, Tuple

from fffw.wrapper import BaseWrapper, ensure_binary

__all__ = [
    'FLVMuxer',
    'HLSMuxer',
    'MP3Muxer',
    'MP4Muxer',
    'NullMuxer',
    'Muxer',
    'TeeMuxer',
]


class Muxer(BaseWrapper):
    format: str

    def __init__(self, output: str, **kw: Any):
        self.__output = output
        super(Muxer, self).__init__(**kw)

    def __repr__(self) -> str:
        return "<%s>(%s)" % (
            self.output,
            self.get_opts()
        )

    @property
    def output(self) -> str:
        return self.__output

    @output.setter
    def output(self, value: str) -> None:
        self.__output = value

    def get_args(self) -> List[bytes]:
        args = super(Muxer, self).get_args()
        return ensure_binary(['-f', self.format]) + args

    def get_opts(self) -> str:
        """ Returns muxer options formatted with ':' delimiter."""
        return ':'.join('%s=%s' % (self.key_to_opt(k), self._args[k])
                        for k in self._args_order if self._args[k])

    def key_to_opt(self, k: str) -> str:
        return self._key_mapping[k].strip('- ')


class FLVMuxer(Muxer):
    format = 'flv'


class MP4Muxer(Muxer):
    format = 'mp4'


class MP3Muxer(Muxer):
    format = 'mp3'


class NullMuxer(Muxer):
    format = 'null'


class HLSMuxer(Muxer):
    format = 'hls'

    arguments = [
        ('method', '-method '),
        ('segment_size', '-hls_time '),
        ('manifest_size', '-hls_list_size '),
    ]


class TeeMuxer(Muxer):
    format = 'tee'

    def __init__(self, *muxers: Muxer) -> None:
        # tee muxer does not require output file argument, instead it aggregates
        # multiple other muxer definitions.
        # FIXME: fix typing for this.
        # noinspection PyTypeChecker
        super(TeeMuxer, self).__init__(None)  # type: ignore
        self.muxers = muxers

    @property
    def output(self) -> str:
        return '|'.join(['[f={format}{opts}]{output}'.format(
            format=m.format, opts=self._format_opts(m.get_opts()),
            output=m.output) for m in self.muxers])

    @output.setter
    def output(self, muxers: Tuple[Muxer]) -> None:
        for m in muxers:
            assert isinstance(m, Muxer)
        self.muxers = muxers

    @staticmethod
    def _format_opts(opts: str) -> str:
        return (':' + opts) if opts else ''
