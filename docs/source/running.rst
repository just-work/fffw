Running FFMPEG
==============

``fffw`` provides a :py:class:`BaseWrapper <fffw.wrapper.base.BaseWrapper>`
class that allows:

* describing program arguments (including flags, multi-value and positional
  arguments)
* running command synchronously
* checking program output for error markers

Below is an example that runs ``mediainfo`` and checks output for "error" text.

.. literalinclude:: ../../examples/wrapper.py
