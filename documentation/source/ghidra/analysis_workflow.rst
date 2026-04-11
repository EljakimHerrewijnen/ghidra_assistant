Analysis Workflow
=================

Function Enumeration
--------------------

The simplest starting point is to enumerate functions through
``ga.ghidra.functions``.

.. code-block:: python

   from ghidra_assistant.ghidra_assistant import GhidraAssistant

   ga = GhidraAssistant()

   for fn in ga.ghidra.functions:
       print(fn.name, fn.address)

Under ``mcp_hydra``, each item is materialized as a ``GhidraFunctionBasic`` and
contains the minimum identity needed for later detailed queries.

If you already know an address, you can query the matching function directly:

.. code-block:: python

   current = ga.ghidra.get_function_at(0x401000)
   if current is not None:
      print(current.name, current.prototype)

Detailed Function Fetch
-----------------------

Use ``get_function(...)`` when you need more than a name and address.

.. code-block:: python

   basic = next(iter(ga.ghidra.functions))
   detailed = ga.ghidra.get_function(basic)

   print(detailed.name)
   print(detailed.prototype)
   print(detailed.decompiled_code)
   print(detailed.incoming_refs)

In the Hydra backend, this call combines several backend operations:

- function disassembly
- decompilation
- variable discovery
- incoming and outgoing xrefs
- best-effort function bytes through the memory API

TODO:DIAGRAM:Add a Ghidra function-query data-flow diagram showing function enumeration, detail queries, and assembly into a ``GhidraFunction`` object.

Memory Access
-------------

The backend exposes memory helpers directly and also through a slice-based
``mem`` helper.

.. code-block:: python

   data = ga.ghidra.read_memory(0x401000, 0x40)
   header = ga.ghidra.mem[0x401000:0x401040]
   print(data.hex())
   print(header[:8])

On ``mcp_hydra``, memory writes and segment creation are also available.

.. code-block:: python

   ga.ghidra.memory_create_segment(
       name=".loader_data",
       address=0x401000,
       size=0x1000,
       read=True,
       write=True,
       execute=False,
   )

   ga.ghidra.write_mem(0x401000, b"\x90\x90")

Program metadata and current cursor:

.. code-block:: python

   print(hex(ga.ghidra.cursor))
   print(ga.ghidra.get_project_info())
   print(ga.ghidra.get_program_info())

Program Navigation And Metadata
-------------------------------

Metadata helpers in the Hydra path include:

- ``selected_instance`` for the chosen Ghidra window
- ``get_project_info()`` for project-level metadata
- ``get_program_info()`` for the active program
- ``cursor`` for the current address in the UI

Xrefs And Analysis Helpers
--------------------------

The backend provides both xref-specific and broader analysis helpers. These are
practical when building automation on top of Ghidra's current program model.

Examples include:

- ``get_xrefs_to(address)``
- ``get_xrefs_from(address)``
- ``get_function_xrefs(address)``
- ``analysis_callgraph(...)``
- ``analysis_dataflow(...)``

Example xref query:

.. code-block:: python

   xrefs_to = ga.ghidra.get_xrefs_to("0x401000")
   xrefs_from = ga.ghidra.get_xrefs_from("0x401000")
   print(xrefs_to)
   print(xrefs_from)

Example analysis query:

.. code-block:: python

   result = ga.ghidra.analysis_callgraph(address="0x401000", max_depth=2)
   print(result)

Usage Pattern
-------------

For most scripts, the best pattern is:

1. instantiate ``GhidraAssistant`` with ``mcp_hydra``
2. select the intended program instance explicitly when needed
3. enumerate candidate functions
4. fetch detailed function objects only when required
5. use memory and xref helpers to drive targeted automation

This keeps backend traffic focused and avoids loading more data than necessary.