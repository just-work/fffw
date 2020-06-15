Transcoding
===========

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


