Connection And Backends
=======================

Public Entry Point
------------------

The high-level entry point is ``GhidraAssistant`` in
``src/ghidra_assistant/ghidra_assistant.py``.

Its role is intentionally small:

- accept a backend name
- accept backend-specific keyword arguments
- construct a ``Ghidra`` backend router
- expose that router as ``ga.ghidra``

Typical usage:

.. code-block:: python

   from ghidra_assistant.ghidra_assistant import GhidraAssistant

   ga = GhidraAssistant()
   print(ga.ghidra.cursor)

Backend Router
--------------

The ``Ghidra`` class in ``utils/ghidra/ghidra_connect.py`` selects a concrete
backend and forwards attribute access to it.

Supported backend names are:

``mcp_hydra``
   Default and preferred backend.

``mcp``
   Legacy HTTP MCP server backend.

``ghidra_bridge``
   Legacy ``ghidra_bridge`` backend.

``auto``
   Best-effort fallback mode that tries Hydra first and then the older MCP
   backend.

Preferred Backend: ``mcp_hydra``
--------------------------------

The preferred implementation is ``MCPHydraBackend`` in
``utils/ghidra/mcp_hydra.py``.

This backend exposes the richest current API surface:

- discovery of active Ghidra instances through ``/instances``
- selection of a single instance using ``project_name`` and ``file_name``
- function enumeration through ``.functions``
- detailed function fetch through ``.get_function(...)``
- memory reads and writes
- segment creation and updates
- xref and analysis helpers

Instance Selection
------------------

When the backend starts, it first talks to the controller endpoint and fetches
the set of active Ghidra instances. If only one instance exists, it can select
it automatically. If several exist, it expects disambiguation.

Use ``file_name`` when there are multiple open programs:

.. code-block:: python

   ga = GhidraAssistant(
       backend="mcp_hydra",
       file_name="firmware_v2.elf",
   )

Use both ``project_name`` and ``file_name`` when more than one instance might
match the same program file name.

.. code-block:: python

   ga = GhidraAssistant(
       backend="mcp_hydra",
       project_name="SecureBootResearch",
       file_name="firmware_v2.elf",
   )

To inspect the selected instance and the active program metadata:

.. code-block:: python

   ga = GhidraAssistant(backend="mcp_hydra", file_name="firmware_v2.elf")

   print(ga.ghidra.selected_instance)
   print(ga.ghidra.get_project_info())
   print(ga.ghidra.get_program_info())

Secondary Backends
------------------

``MCPBackend`` in ``utils/ghidra/mcp_backend.py``
   This backend wraps an older HTTP API. It still exposes function lookup and
   memory read helpers, but it is narrower and should be treated as secondary.

``Py3BridgeGhidraBackend`` in ``utils/ghidra/py3_bridge_backend.py``
   This backend uses ``ghidra_bridge`` to execute against a live Ghidra process.
   It remains a compatibility path but is not the preferred default workflow.

Documentation Priority
----------------------

The rest of this documentation treats ``mcp_hydra`` as the default Ghidra
path. The older backends are documented only to explain compatibility and code
layout.

TODO:DIAGRAM:Add a Ghidra connection diagram showing ``GhidraAssistant`` as the public API, ``Ghidra`` as the routing layer, ``MCPHydraBackend`` as the primary branch, the secondary legacy backends, Hydra instance selection, and the selected program endpoints.