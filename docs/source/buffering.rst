Buffering Detection
===================

``ffmpeg`` filter graph implementation doesn't provide any flow control and
there are situations where out-of-memory error can occur.

Reading multiple files
----------------------

.. blockdiag::

  blockdiag {
    Preroll -> Source -> Result;
    Source2 -> Backup;
      Preroll [color = green];
      Source [color = yellow, label = Source];
      Source2 [color = yellow, label = Source];
      Backup [label = "Backup source"];
    group {
      color = white;
      Source; Source2;
   }

  }

This situation describes a video processing pipeline where:

* preroll and source are decoded only once
* each video (result) starts with a common preroll
* each uncompressed source is transcoded in a "lossless" way to a relatively
  small file (backup source)

To produce first frame for second output (backup source), ``ffmpeg`` requests
first frame from source decoder. Decoded frame is pushed through filter graph
to both outputs, but preroll needs to be transcoded first. So, while "backup
source" receives frames one-by-one, decoded preroll is buffered in memory.

Instead, you may tell ``ffmpeg`` to read both input files for both outputs and
use ``trim`` filter to cut preroll from "backup source".

.. blockdiag::

  blockdiag {
    Preroll -> Source -> Result;
    Preroll2 -> Source2 -> Backup;
      Preroll [color = green];
      Preroll2 [color = gray, style = dashed, label = "Preroll (cut out)"];
      Source [color = yellow, label = Source];
      Source2 [color = yellow, label = Source];
      Backup [label = "Backup source"];
    group {
      color = white;
      Source; Source2;
    }
    group {
      color = white;
      Preroll; Preroll2;
    }
  }

Non-linear editing
------------------

.. blockdiag::

  blockdiag {
    Scene1 -> Scene2 -> Scene3;

    Scene2 [color = gray, style = dashed];

    group {
      orientation = portrait;
      Scene3 -> Result1;
    }

    group {
      orientation = portrait;
      Scene1 -> Result2;
    }
  }

In this example ``ffmpeg`` cuts out **Scene2** from source file and swaps
**Scene1** and **Scene3**, but **Result2** follows **Result1**. **Result2**
is decoded before **Result1**, so it is buffered in memory. The only way to
fix this is to decode source twice:

.. blockdiag::

  blockdiag {
    orientation = portrait;
    Source1 -> Scene3 -> Result1;
    Source2 -> Scene1 -> Result2;
    group {
      Source1;Scene3;Result1;
    }
    group {
      Source2;Scene1;Result2;
    }
  }

Buffering Prevention
--------------------

Both described situations are detected via
:py:meth:`FFMPEG.check_buffering <fffw.encoding.ffmpeg.FFMPEG.check_buffering>`
call.

* All inputs must have streams defined with proper metadata
* Filters that are used in filter graph must transform scenes in metadata
  properly (this is already done for
  :py:class:`Concat <fffw.encoding.filters.Concat>`,
  :py:class:`SetPTS <fffw.encoding.filters.SetPTS>` and
  :py:class:`Trim <fffw.encoding.filters.Trim>` filters).

.. literalinclude:: ../../examples/buffering.py
