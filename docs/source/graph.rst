Filter Graph
============

Building filter graph is the most complicated part of ``fffw`` library.
Let's see how different parts are combined together to build this graph.

.. code-block:: python

  ff = FFMPEG()

Input streams
-------------

.. code-block:: python

  video = Stream(VIDEO)
  audio = Stream(AUDIO)
  source = Input(input_file='input.mp4', streams=(video, audio))
  ff < source # ff.add_input(source)

In this example we use "stdin redirection operator" (``<``) to add new input
file to ``FFMPEG`` instance. We could call
:py:meth:`fffw.encoding.ffmpeg.FFMPEG.add_input` if short variant is not
appropriate.

Connect to filters
------------------

.. code-block:: python

  scale = ff.video | Crop(w=1920, h=1080) | Scale(1280, 720)

:py:attr:`fffw.encoding.ffmpeg.FFMPEG.video` returns first available video
stream across all inputs connected to ``FFMPEG`` that is not yet connected to
filter graph. "Pipe" operator connects an input stream (or a filter) to first
available input for next filter.

* If you need to point specific input stream, you may do it
  like::

    vol = Volume(20)
    source.streams[1] | vol  # audio.connect_dest(vol)

* Pipelines are useful if a stream is processed with long filter chain
* When a filter has multiple inputs, it can be used more than once as an
  argument for :py:meth:`connect_dest`::

    overlay = Overlay(x=100, y=100)
    main_video_stream | overlay
    logo_video_stream | overlay

* When a filter has multiple outputs, :py:meth:`connect_dest` method may be
  called multiple times for different filters::

    split = video | Split(VIDEO, output_count=3)
    split | Scale(1280, 720)
    split | Scale(960, 540)
    split | Scale(640, 360)

.. note::
  each ``Stream`` may be used in filter graph only once, so use ``Split`` filter
  to reuse same input stream.

Output to codecs
----------------

Each stream in filter graph must be connected to an output codec. This is done
via "stdout redirection operator"::

  video_codec = VideoCodec('libx264')
  audio_codec = AudioCodec('libfdk_aac')
  output = Output(output_file='output.mp4',
                  codecs=[video_codec, audio_codec])

  overlay > video_codec

* Each codec consumes single stream from filter graph or from input file
* Free codec in output file is mapped automatically to a first available input
  stream of same kind. This can be changed by connecting input stream directly
  to a codec::

    ff.audio > audio_codec

* An input stream can be connected to multiple codecs (i.e. in different output
  files).
* Input stream can be used in filter graph only once (use
  :py:class:`fffw.encoding.filters.Split` to handle that).

Write files
-----------

To write any output file you must connect it to ffmpeg as an output using
"stdout redirection operator"::

  ff > output  # ff.add_output(output)

.. note::
  Connecting ``Output`` to ``FFMPEG`` is obligatorily; without that no output
  file arguments will be generated.