Ghidra Assistant
================

Ghidra Assistant is a Python toolkit for tying together binary analysis in
Ghidra, real-device debugging through Gupje, and backend-driven emulation.

This documentation is written around practical workflows and examples rather
than around the package layout.

The quickest way to read it is:

- start with setup
- move to the Ghidra or ConcreteDevice workflow depending on where your script starts
- use the architecture pages when you need implementation detail or a target-specific example
- use the emulator page when you want offline execution or replay

Current coverage is strongest in ARM64. The first end-to-end example page is
`the Raspberry Pi 4 <https://github.com/EljakimHerrewijnen/rpi4_gupje>`_ ARM64 bring-up under the architecture section.

.. note::

   The Ghidra and concrete-device paths are the primary supported workflows.
   The emulator layer is documented as a secondary path because parts of it are
   still changing.


.. caution::

   Most of the documentation was written by an LLM and is incomplete.


Gupje
-----

The main feature of this module is that it provides a Python interface to the `Gupje stub <https://github.com/EljakimHerrewijnen/Gupje>`_ running on the target device.


.. drawio-viewer:: images/concrete-device-to-ghidra-sequence.drawio
   :height: 420px


.. toctree::
   :maxdepth: 2
   :caption: Overview:

   overview
   setup


.. toctree::
   :maxdepth: 2
   :caption: Ghidra:

   ghidra/index

.. toctree::
   :maxdepth: 2
   :caption: Concrete Device:

   concrete_device/index


.. toctree::
   :maxdepth: 2
   :caption: Architectures:

   architectures/index

.. toctree::
   :maxdepth: 2
   :caption: Emulator:

   emulator/index

