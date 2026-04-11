Ghidra Workflow
===============

The Ghidra integration path is the main entry point for most users of the
project. It is built around a thin public wrapper, a backend router, and one
preferred backend implementation.

.. toctree::
   :hidden:
   :maxdepth: 2

   connection_and_backends
   analysis_workflow

Use this section when your script starts from a live Ghidra session.

The connection page explains how the backend is selected and how the active
program instance is chosen. The analysis page then shows the common operations
you actually script against: function enumeration, detailed function fetches,
memory access, metadata queries, and xref-driven automation.