Vectorize your code
===================

There are at least two situations when you apply same ffmpeg filters to a set of
files. First is adaptive streaming for internet video (a number of files with
same content and different bitrate are produced); second one is linear editing
(parts of video are cut from source and concatenated together to form new video
sequence). May be there are more, and ``fffw`` provides a way to handle stream
vector transformations.

SIMD Wrapper
------------

To use :py:class:`fffw.encoding.vector.SIMD` helper you'll need to initialize
input file with streams including meta. This is used to track changes applied to
input streams. Also, ``SIMD`` requires a list of outputs including codecs to be
able to connect input streams to corresponding outputs.

.. code-block:: python

  mi = MediaInfo.parse('input.mp4')
  video_meta, audio_meta = from_media_info(mi)
  video = Stream(VIDEO, video_meta)
  audio = Stream(AUDIO, audio_meta)

  source = input_file('input.mp4', video, audio)
  output1 = output_file('output1.mp4',
                        VideoCodec('libx264'),
                        AudioCodec('aac'))
  output2 = output_file('output2.mp5',
                        VideoCodec('libx265'),
                        AudioCodec('libfdk_aac'))

  simd = SIMD(source, output1, output2)

Apply filters
-------------

The easiest way to apply a filter to a stream vector is to pass it to "pipeline
operator" (``|``)::

  cursor = self.simd | Volume(30)

If a vector has only single element (i.e. input stream itself), no preliminary
splitting occurs. ``Split`` filter is added automatically if applied filter
vector contains distinct elements, like a filter with different parameters::

  simd.connect(Scale, params=[(1920, 1080), (1280, 720)])

Another way to manage applied filter is to pass a mask for a filter vector::

  simd.connect(Deint(), mask=[True, False])

This excludes applied filter from some of input streams, having ``False`` in
mask array.

Finalizing filter graph
-----------------------

At the end stream vector (``cursor``) must be connected to a codec vector::

  cursor > simd
  simd.ffmpeg.run()

This connects each stream vector element to a corresponding codec in ``simd``
output file list.

Complete example
----------------

This example shows two cases for vector stream processing: linear editing and
adaptive video streaming file generation.

.. literalinclude:: ../../examples/simd.py
