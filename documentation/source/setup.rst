=====
Setup
=====

Requirements
------------

- Python 3.12+
- `PDM <https://pdm-project.org/>`_ for dependency management
- `Ghidra <https://github.com/NationalSecurityAgency/ghidra>`_
- `ghydraMCP <https://github.com/LaurieWired/GhidraMCP>`_ Ghidra plugin (for the default ``mcp_hydra`` backend)

Install the Python environment
------------------------------

.. code-block:: console

    pipx install pdm        # install PDM once
    pdm sync -d             # create venv and install all dependencies

Ghidra setup (mcp_hydra backend)
---------------------------------

The default backend, ``mcp_hydra``, communicates with the `ghydraMCP <https://github.com/LaurieWired/GhidraMCP>`_ plugin. Install the plugin in Ghidra, then enable it via *File → Configure → ghydraMCP*. The plugin exposes a REST API on ``http://127.0.0.1:8192`` by default.

If Ghidra runs on a different host or port, set environment variables before running the GA:

.. code-block:: console

    export GHIDRA_HYDRA_HOST=192.168.1.10
    export GHIDRA_HYDRA_PORT=8192

Usage
-----

.. code-block:: python

    from ghidra_assistant.ghidra_assistant import GhidraAssistant

    ga = GhidraAssistant()           # uses mcp_hydra by default
    ga = GhidraAssistant('mcp_hydra', project_name='MyProject', file_name='firmware.bin')

Run the entry-point directly:

.. code-block:: console

    pdm run ghidra-assistant

VsCode
------

The GA works well with VS Code. The ``.vscode/launch.json`` in the repository provides a ready-made debug configuration.

Alternative backends
--------------------

``ghidra_bridge``
    Legacy Python bridge. Install the server-side script in Ghidra via the Script Manager, then run it. Requires the ``ghidra_bridge`` Python package.

``pyhidra``
    Headless/embedded Ghidra via the ``pyhidra`` package. Useful for scripted analysis without a running Ghidra GUI.

``mcp``
    Connects to a simpler HTTP MCP server. Fewer features than ``mcp_hydra``.

Pass the backend name when constructing ``GhidraAssistant``:

.. code-block:: python

    ga = GhidraAssistant(backend='ghidra_bridge')

Building the Gupje stub (optional)
-----------------------------------

To use ``ConcreteDevice`` with a real target, you need the Gupje stub compiled for your device. Clone `Gupje <https://github.com/EljakimHerrewijnen/Gupje>`_ and follow its build instructions. An Android NDK is required for ARM targets:

.. code-block:: console

    export ANDROID_NDK_ROOT=/path/to/android-ndk
    make -f devices/<your_device>/Makefile
