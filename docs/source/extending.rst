Extending fffw
==============

The aim of ``fffw`` library is to provide mechanics for preparing ``ffmpeg``
command line arguments, not to cover all possible params. It provides all
necessary base classes to extend input file handling, filtering and output
configuration.

Before writing code it's useful to read section :ref:`command-line-structure`.

Extending FFMPEG
----------------

If you need to add more flags to common section of ``ffmpeg``, just extend
main wrapper:

.. literalinclude:: ../../examples/extending.py

Alternate inputs
----------------

Files are not the only sources for ``ffmpeg``. Audio/video streams could be read
from network or hardware devices. Below there is a sample implementation of
`screen grabbing input <http://ffmpeg.org/ffmpeg-all.html#X11-grabbing>`_.

.. literalinclude:: ../../examples/grabbing.py

Implement filters
-----------------

There are many useful filters in ``ffmpeg``. I.e. you may use
`scale2ref <http://ffmpeg.org/ffmpeg-all.html#scale2ref>`_ to scale one video
to fit another one.

.. literalinclude:: ../../examples/filters.py

Configure muxer
---------------

There are lot's of formats supported by ``ffmpeg``. Internet video streaming
often uses HLS protocol to provide better experience. HLS muxer has a bunch of
options to tune.

.. literalinclude:: ../../examples/hls.py
