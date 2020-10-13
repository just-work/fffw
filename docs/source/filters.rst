Filters
=======

Split
-----

``Split`` is used when you need to reuse same stream as an input for multiple
filters or codecs.

.. note::
  ``Split`` should not be used if desired stream is connected directly to codecs
  and is not used elsewhere in filter graph.

.. autoclass:: fffw.encoding.filters.Split
   :noindex:

Example
^^^^^^^
.. code-block:: python

  split = ffmpeg.video | Split(VIDEO, output_count=3)

  split | scale1
  split | scale2
  split | scale3

Concat
------

``Concat`` combines two or more streams together, one after another. Resulting
order is FIFO.


.. autoclass:: fffw.encoding.filters.Concat
   :noindex:

Example
^^^^^^^
.. code-block:: python

  concat = Concat(VIDEO, input_count=3)

  preroll | concat
  source | concat
  postroll | concat

Overlay
-------

``Overlay`` combines two video streams together, one above another. Most common
use case is adding a logo to a video stream. First input is "bottom layer",
second one is "top layer". Top layer position can be adjusted by ``x`` and ``y``
arguments.

.. autoclass:: fffw.encoding.filters.Overlay
   :noindex:

Example
^^^^^^^
.. code-block:: python

  overlay = source | Overlay(x=100, y=100)
  logo | overlay

Scale
-----

``Scale`` changes video dimensions. It has more capabilities like changing
pixel format but that is not covered by filter implementation (please, inherit).

.. autoclass:: fffw.encoding.filters.Scale
   :noindex:

Example
^^^^^^^
.. code-block:: python

  scale = source | Scale(width=1920, height=1080)

Trim
----

``Trim`` leaves only frames that match ``start`` - ``end`` interval.

.. note::
  Without ``SetPTS`` filter trim does not adjust first frame timestamp, so
  resulting stream will have duration equal to ``Trim.end`` value, while first
  ``Trim.start`` seconds first frame will be shown frozen.

.. autoclass:: fffw.encoding.filters.Trim
   :noindex:

Example
^^^^^^^
.. code-block:: python

  cut = source | Trim(VIDEO, start=60.0, end=120.0) | SetPTS(VIDEO)


SetPTS
------

``SetPTS`` adjusts frame presentation timestamps.

.. note::
  The only supported mode that transforms metadata correctly is
  ``PTS-STARTPTS``, which aligns first frame to zero timestamp.

.. autoclass:: fffw.encoding.filters.SetPTS
   :noindex:

Example
^^^^^^^
.. code-block:: python

  cut = source | Trim(AUDIO, start=60.0, end=120.0) | SetPTS(AUDIO)

Format
------

``Format`` filter changes video stream pixel format.

.. autoclass:: fffw.encoding.filters.Format
   :noindex:

Example
^^^^^^^
.. code-block:: python
  hw = source | Format('nv12') | Upload(Device(hardware='cuda', name='foo'))

Upload
------

``Upload`` send video frames from host memory to gpu card.

.. autoclass:: fffw.encoding.filters.Upload
   :noindex:
