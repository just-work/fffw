import re
import subprocess
from logging import getLogger


def quote(token):
    """ Escapes a token for command line."""
    token = ensure_text(token)
    if re.search(r'[ ()[\];]', token):
        return '"%s"' % token.replace('\"', '\\"')
    return token


def ensure_binary(x):
    """ Recursively ensures that all values except collections are bytes."""
    if isinstance(x, tuple):
        return tuple(ensure_binary(y) for y in x)
    if isinstance(x, list):
        return list(ensure_binary(y) for y in x)
    if isinstance(x, str):
        return x.encode("utf-8")
    if not isinstance(x, bytes):
        return str(x).encode("utf-8")
    return x


def ensure_text(x):
    """ Recursively ensures that all values except collections are strings."""
    if isinstance(x, tuple):
        return tuple(ensure_text(y) for y in x)
    if isinstance(x, list):
        return list(ensure_text(y) for y in x)
    if isinstance(x, bytes):
        return x.decode("utf-8")
    return str(x)


class BaseWrapper:
    """
    Base class for generating command line arguments from params.

    Values meanings:
    * True: flag presense
    * False/None: flag absense
    * List/Tuple: param name is repeated multiple times with values
    * Callable: function call result is added to result
    * All other: param name and value are added to result
    """
    arguments = []
    """type arguments: List[Tuple[str, str]]"""

    def __init_args(self):
        self._key_mapping = {}
        self._args = {}
        self._args_order = []
        for (name, key) in self.arguments:
            self._key_mapping[name] = key
            self._args[name] = None
            self._args_order.append(name)

    def __init__(self, **kw):
        self.__init_args()
        for k, v in kw.items():
            setattr(self, k, v)
        self._output = ''
        cls = self.__class__
        self.logger = getLogger("%s.%s" % (cls.__module__, cls.__name__))

    def __setattr__(self, key, value):
        if key in getattr(self, '_key_mapping', {}):
            self._args[key] = value
        else:
            object.__setattr__(self, key, value)

    def get_args(self):
        result = []
        for k in self._args_order:
            v = self._args[k]
            if v is not None and v is not False:
                param = self._key_mapping[k]
                if callable(v):
                    value = v()
                    if isinstance(value, list):
                        result.extend(value)
                    else:
                        result.append(value)
                elif isinstance(v, list):
                    for item in v:
                        result.extend([param.strip(), item])
                elif v is True:
                    result.append(param.strip())
                else:
                    if param.endswith(' '):
                        result.extend([param.strip(), str(v)])
                    else:
                        result.append("%s%s" % (param, v))

        return list(map(ensure_binary, result))

    def set_args(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get_cmd(self):
        return ' '.join(map(quote, ensure_text(self.get_args())))

    def handle_stderr(self, line):
        self.logger.debug(line.strip())
        self._output += line

    def run(self):
        self._output = ''
        self.logger.info(self.get_cmd())
        args = self.get_args()

        with subprocess.Popen(args, stderr=subprocess.PIPE) as proc:
            while True:
                line = proc.stderr.readline()
                if not line:
                    break
                line = ensure_text(line)
                self.handle_stderr(line)
        self.logger.info("%s return code is %s", args[0], proc.returncode)
        return proc.returncode, self._output
