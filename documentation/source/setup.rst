Setup
=====

This page describes the minimum setup required to use the supported Ghidra and
concrete-device workflows.

Python Environment
------------------

The project targets Python 3.12 or newer and uses PDM for packaging and local
development.

.. code-block:: console

   pipx install pdm
   pdm sync -d

The package can then be executed either as a module or through the console
script defined in ``pyproject.toml``.

.. code-block:: console

   pdm run python -m ghidra_assistant.ghidra_assistant
   pdm run ghidra-assistant

Ghidra Setup
------------

The recommended backend is ``mcp_hydra``. It connects to the
``ghydraMCP`` plugin through its HTTP API.

Minimum setup steps:

1. Install Ghidra.
2. Install the ``ghydraMCP`` plugin in Ghidra.
3. Enable the plugin in the current Ghidra tool configuration.
4. Ensure the HTTP endpoint is reachable.

The default controller endpoint expected by the code is:

.. code-block:: text

   http://127.0.0.1:8192/

If the host or port differs, set the environment variables used by
``MCPHydraBackend``.

.. code-block:: console

   export GHIDRA_HYDRA_HOST=127.0.0.1
   export GHIDRA_HYDRA_PORT=8192

Basic Ghidra Connection Check
-----------------------------

.. code-block:: python

   from ghidra_assistant.ghidra_assistant import GhidraAssistant

   ga = GhidraAssistant()
   print(ga.ghidra.selected_instance)
   print(ga.ghidra.get_program_info())

If multiple Ghidra windows are open, disambiguate using ``file_name`` and
optionally ``project_name``.

.. code-block:: python

   ga = GhidraAssistant(
       backend="mcp_hydra",
       file_name="firmware_v2.elf",
       project_name="MyProject",
   )

You can also check that the function list is reachable:

.. code-block:: python

   for index, fn in enumerate(ga.ghidra.functions):
      print(fn.name, fn.address)
      if index == 4:
         break

Concrete-Device Prerequisites
-----------------------------

To use ``ConcreteDevice`` on a real target, you need more than the Python
package itself.

You need:

- a target where code execution has already been obtained
- a `Gupje stub <https://github.com/EljakimHerrewijnen/Gupje>`_ compiled for the target architecture and transport
- a Python device hook file that binds host-side transport functions to
  ``ConcreteDevice``
- a compatible architecture debugger backend such as ``GA_arm64_debugger`` or
  ``GA_riscv_debugger``

At a minimum, the host-side hook code must provide:

- a transport ``read(length)`` function
- a transport ``write(data)`` function
- an ``arch_dbg`` instance attached to the ``ConcreteDevice``
- a call to ``copy_functions()`` so the device delegates memory and control
  methods to the architecture debugger implementation

Typical host-side bring-up:

.. code-block:: python

   from ghidra_assistant.concrete_device import ConcreteDevice

   cd = ConcreteDevice(target_dev="my_device.py")
   cd.test_connection()
   print(cd.get_debugger_location())

TODO:DIAGRAM:Add a setup prerequisites diagram covering the Python environment, Ghidra, ``ghydraMCP``, the HTTP endpoint, the device hook file, and the target running Gupje.

Tests
-----

The project uses pytest.

.. code-block:: console

   pdm run python -m pytest -q

To focus on the unit tests only:

.. code-block:: console

   pdm run python -m pytest tests/unit -q

Scope Notes
-----------

The repository does not include its own standalone Ghidra-side plugin. Instead,
it integrates with external backends such as ``ghydraMCP`` and the older MCP or
bridge-based paths.

The primary documented workflows in the remainder of this documentation assume:

- ``mcp_hydra`` for Ghidra integration
- ``ConcreteDevice`` plus Gupje for real targets
- Unicorn as the primary emulator backend