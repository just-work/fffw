# fffw
## FFMPEG filter wrapper

![build](https://github.com/just-work/fffw/workflows/build/badge.svg?branch=master)
[![codecov](https://codecov.io/gh/just-work/fffw/branch/master/graph/badge.svg)](https://codecov.io/gh/just-work/fffw)
[![PyPI version](https://badge.fury.io/py/fffw.svg)](http://badge.fury.io/py/fffw)
[![Documentation Status](https://readthedocs.org/projects/fffw/badge/?version=latest)](https://fffw.readthedocs.io/en/latest/?badge=latest)


[FFMPEG](https://github.com/FFmpeg/FFmpeg) command line tools.


### PyCharm MyPy plugin
```
dmypy run -- --config-file=mypy.ini .
```

### Sphinx autodoc

```
cd docs/source && rm fffw*.rst
cd docs && sphinx-apidoc -o source ../fffw
```

### Sphinx documentation

```
cd docs && make html
```