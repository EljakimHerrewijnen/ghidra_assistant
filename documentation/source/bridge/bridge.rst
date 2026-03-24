===============
Ghidra Backends
===============

The ``Ghidra`` class in ``ghidra_connect.py`` selects and delegates to one of several backends. All backends expose the same interface (``GhidraBackend``), so the rest of the code is backend-agnostic.

.. code-block:: python

    from ghidra_assistant.ghidra_assistant import GhidraAssistant

    ga = GhidraAssistant()                     # mcp_hydra (default)
    ga = GhidraAssistant('mcp_hydra',
                         project_name='Foo',
                         file_name='bar.bin')  # select a specific instance
    ga = GhidraAssistant('ghidra_bridge')      # legacy bridge

mcp_hydra (default)
-------------------

Connects to the `ghydraMCP <https://github.com/LaurieWired/GhidraMCP>`_ Ghidra plugin via a HATEOAS-style REST API. On startup the backend queries ``GET /instances`` and automatically selects the running Ghidra session. If multiple sessions are open, pass ``project_name`` and/or ``file_name`` to disambiguate.

Environment variables:

- ``GHIDRA_HYDRA_HOST`` — default ``127.0.0.1``
- ``GHIDRA_HYDRA_PORT`` — default ``8192``

This is the richest backend and supports reading/writing memory, renaming/retyping functions and variables, cross-references, decompilation, and disassembly.

mcp
---

A simpler HTTP backend that targets an older, non-HATEOAS server plugin. Fewer features than ``mcp_hydra``. Useful as a lightweight fallback.

ghidra_bridge
-------------

Legacy backend using `ghidra_bridge <https://github.com/justfoxing/ghidra_bridge>`_, which bridges Jython (Ghidra's built-in Python 2) to Python 3 over a local socket. Requires the ``ghidra_bridge`` server script to be running inside Ghidra.

pyhidra
-------

Embeds a headless Ghidra instance in the current process via ``pyhidra``. Useful for automated analysis scripts that do not need a running Ghidra GUI.

GhidraBackend interface
-----------------------

All backends implement the ``GhidraBackend`` base class (``utils/ghidra/ghidra_backend.py``). The key members are:

.. code-block:: python

    backend.functions            # iterable of GhidraFunctionBasic
    backend.get_function(basic)  # -> GhidraFunction (with disassembly, bytes, xrefs)
    backend.cursor               # int: currently selected address in the Ghidra UI
    backend.read_memory(addr, n) # -> bytes
    backend.write_mem(addr, data)

Data structures:

- ``GhidraFunctionBasic`` — address, name, arg list, return type
- ``GhidraFunction`` — extends Basic with raw bytes, disassembly, decompiled C, incoming/outgoing cross-references
- ``GhidraFunctionArgument`` — name, type, storage location
