Transcoding
===========

Data Model
----------

This section explains ``ffmpeg``/``fffw`` data model in details.

ffmpeg command line structure
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Let's look on short command line produced by ``fffw`` in :ref:`quick-start-example`: ::

  ffmpeg -loglevel level+info -y \
  -t 5.0 -i input.mp4 \
  -filter_complex "[0:v]scale=w=1280:h=720[vout0]" \
  -map "[vout0]" -c:v libx264 \
  -map 0:a -c:a aac \
  output.mp4

First section contains common ``ffmpeg`` flags:
  * ``-loglevel`` - logging setup
  * ``-y`` - overwrite mode

Second part contains parameters related to input files:
  * ``-t`` - total input read duration
  * ``-i`` - input file name

After that there is a ``-filter_complex`` parameter that describes stream
processing graph. In details we'll discuss it in section :ref:`filter-graph`.

Next part contains codecs parameters:
  * ``-map`` - what is an input for this codec, input stream or graph edge.
  * ``-c:v`` - video codec identifier.
  * ``-c:a`` - audio codec identifier.

This section usually contains lot's of codec-specific parameter like bitrate or
number of audio channels.

The last part is output file definition section. Usually it's just output file
name (``output.mp4``) but it may contain some ``muxer`` parameters.

.. _filter-graph:

Filter graph definition
^^^^^^^^^^^^^^^^^^^^^^^

``ffmpeg`` provides a very powerful tool for video and audio stream processing -
filter graph. This graph contains ``filters`` - nodes connected with named
``edges``.

* ``filter`` is a node that receives one or more input streams and produces one
  or more output streams.
* Each ``stream`` is a sequence of frames (video or audio)
* Another node is an ``input stream``: it is a starting node for graph that
  starts from decoder (a thing that receives chunks of encoded video from
  ``demuxer`` and decodes it to a raw image / audio sample sequence).
* And the last type of node is a ``codec``: it is an output node for graph that
  receives a raw video/audio stream from filter graph, compress it and pass
  to a ``muxer`` which writes resulting file.

There are two syntaxes to define edges between graph nodes:

* Short syntax describes a linear
  sequence of filters::

    deint,crop=0:10:1920:1060,scale=1280:720

  This syntax means has no named edges and means that three filters
  (deinterlace, crop and scale) are applied subsequently to a single video
  stream.

* Full syntax describes complicate graph filter::

    [0:v]scale=100:100[logo];
    [1:v][logo]overlay=x=1800:y=100[vout0]

  This syntax has named input stream identifiers (``[0:v]``, ``[1:v]``) and
  named edges (``[logo]``, ``[vout0]``) to have control about how nodes are
  connected to each other and to codecs.

Implementation
--------------

Let's look how this command line structure is implemented in ``fffw``.

Common ffmpeg flags
^^^^^^^^^^^^^^^^^^^

:py:class:`fffw.encoding.FFMPEG` is responsible for rendering common flags like
``overwrite`` or ``loglevel``. There are a lot of other flags that are not
covered by included implementation and should be added manually via ``FFMPEG``
inheritance as discussed in :doc:`extending`.

.. code-block:: python

  from fffw.encoding import FFMPEG
  ff = FFMPEG(overwrite=True)

Input file flags
^^^^^^^^^^^^^^^^

Input files in ``fffw`` are described by :py:class:`Input` which stores a list
of :py:class:`Stream` objects. When ``Input`` is a file, ``Stream`` is a video
or audio stream in this file. An ``Input`` could also be a capture device like
``x11grab`` or a network client like ``hls``.

You may initialize ``Input`` directly or use :py:func:`input_file` helper.

Each ``Stream`` can contain metadata - information about dimensions, duration,
bitrate and another characteristics described by :py:class:`VideoMeta` and
:py:class:`AudioMeta`.

For an input file you can set such flags as ``fast seek`` or ``input format``.

.. literalinclude:: ../../examples/inputs.py

Filter complex
^^^^^^^^^^^^^^

:py:class:`FilterComplex` hides all the complexity of properly linking filters
together. It is also responsible for tracing metadata transformations (like
dimensions change in ``Scale`` filter or duration change in ``Trim``).

.. literalinclude:: ../../examples/overlay.py

Output files
^^^^^^^^^^^^

FFMPEG results are defined by :py:class:`fffw.encoding.Output`, which contains
a list of :py:class:`fffw.encoding.Codec` representing video and audio streams
in destination file encoded by some codecs.

* Each codec has ``-map`` parameter which links it either to input stream or to
  a destination node in filter graph
* Codec defines a set of encoding parameters like ``bitrate`` or number of audio
  channels. These parameters are not defined by ``fffw`` library and should be
  defined via inheritance as discussed in :doc:`extending`.
* After codec list definition follows a set of muxing parameters (like
  ``format``) and destination file name. There parameters are kept by
  ``Output`` instance
* FFMPEG may have multiple outputs.

.. literalinclude:: ../../examples/multi_bitrate.py


Usage
-----

To process something with ``fffw`` you need:

1. Create ``FFMPEG`` instance
2. Add one or more ``Input`` files to it
3. If necessary, initialize some processing graph
4. Add one or more ``Output`` files
5. Run command with :py:meth:`fffw.encoding.ffmpeg.FFMPEG.run`
