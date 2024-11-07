# fffw
## FFMPEG filter wrapper

[![build](https://github.com/just-work/fffw/workflows/build/badge.svg?branch=master)](https://github.com/just-work/fffw/actions?query=event%3Apush+branch%3Amaster+workflow%3Abuild)
[![Coveralls](https://coveralls.io/repos/github/just-work/fffw/badge.svg?branch=master)](https://coveralls.io/github/just-work/fffw?branch=master)
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