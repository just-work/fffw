# fffw
## FFMPEG filter wrapper

![build](https://github.com/just-work/fffw/workflows/build/badge.svg?branch=master)
[![PyPI version](https://badge.fury.io/py/fffw.svg)](http://badge.fury.io/py/fffw)
[![codecov](https://codecov.io/gh/just-work/fffw/branch/master/graph/badge.svg)](https://codecov.io/gh/just-work/fffw)


[FFMPEG](https://github.com/FFmpeg/FFmpeg) command line tools.

1. *fffw.scaler.Scaler* image transformation size computing helper
2. *fffw.graph.FilterComplex* ffmpeg filter graph helper.
3. *fffw.encoding.FFMPEG* ffmpeg command wrapper for encoding and muxing. 

TBD:

* [ ] sphinx documentation - manual and auto docs
* [x] typing
* [x] coverage measure
* [x] MyPy integration
* [x] license

### PyCharm MyPy plugin
```
dmypy run -- --config-file=mypy.ini .
```
