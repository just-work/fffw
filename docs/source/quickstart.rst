Quick Start
===========

System Requirements
^^^^^^^^^^^^^^^^^^^

Obviously, to work with `FFMPEG <http://ffmpeg.org/>`_ you need to install it.
In Ubuntu-20.04 this is:

    apt-get install ffmpeg

You may also need `MediaInfo <https://mediaarea.net/en/MediaInfo>`_ to get
information about video and audio streams in your files. But this is not
required.

    apt-get install mediainfo

Python Requirements
^^^^^^^^^^^^^^^^^^^

Install ``fffw`` from `PyPI <https://pypi.org/>`_:

    pip install fffw

Write your first command
^^^^^^^^^^^^^^^^^^^^^^^^

.. literalinclude:: ../../examples/transcode.py

This will print something like this (unless you really have ``input.mp4``)::

    ffmpeg -loglevel level+info -y -i input.mp4 -filter_complex "[0:v]scale=w=1280:h=720[vout0]" -map "[vout0]" -c:v libx264 -map 0:a -c:a aac output.mp4
    [error] input.mp4: No such file or directory

That's all. You just opened input file, passed video stream to scale filter and
then encoded results with ``libx264`` and ``aac`` codecs to an output file.
