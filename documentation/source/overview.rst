Overview
========

Ghidra Assistant is a Python project for combining three related capabilities:

- analysis and annotation inside Ghidra
- live interaction with a real target through Gupje and ``ConcreteDevice``
- emulation through a backend abstraction, primarily Unicorn

The codebase is not a single monolithic debugger. It is a set of layers that
can be used together or independently depending on the workflow.

Minimal Examples
----------------

Ghidra-backed analysis:

.. code-block:: python

   from ghidra_assistant.ghidra_assistant import GhidraAssistant

   ga = GhidraAssistant()
   current = next(iter(ga.ghidra.functions))
   print(current.name, current.address)

Concrete target access:

.. code-block:: python

   from ghidra_assistant.concrete_device import ConcreteDevice

   cd = ConcreteDevice(target_dev="my_device.py")
   cd.test_connection()
   first_page = cd.mem[0x100000:0x101000]
   print(len(first_page))

Emulator-backed execution:

.. code-block:: python

   from ghidra_assistant.utils.emulator.base_emulator import BaseEmulator

   emu = BaseEmulator("arm64", "arm", backend="unicorn")
   emu.mem_map(0x1000, 0x1000, 7)
   emu.set_register("PC", 0x1000)

Core Components
---------------

``GhidraAssistant``
   The top-level convenience wrapper in
   ``src/ghidra_assistant/ghidra_assistant.py``. It mainly selects a Ghidra
   backend and exposes it as ``ga.ghidra``.

``Ghidra``
   The backend router in ``utils/ghidra/ghidra_connect.py``. It delegates to
   one of several backends, with ``mcp_hydra`` as the default and most complete
   implementation.

``ConcreteDevice``
   The real-device abstraction in ``src/ghidra_assistant/concrete_device.py``.
   It loads a device hook file, binds transport functions such as ``read`` and
   ``write``, and delegates architecture-specific debugger behavior to an
   ``arch_dbg`` instance.

Architecture debugger backends
   Host-side implementations of the protocol spoken to a Gupje stub on the
   target. ARM64 is the deepest implementation. RISC-V is the next strongest.

``BaseEmulator``
   The backend-agnostic emulator facade in
   ``utils/emulator/base_emulator.py``. It normalizes architecture names and
   forwards memory, register, and execution operations to a backend such as
   Unicorn or angr.

Primary Workflows
-----------------

Ghidra analysis workflow
   Use ``GhidraAssistant`` with the default ``mcp_hydra`` backend to list
   functions, fetch decompilation and disassembly, read memory, and modify the
   current program through the Ghidra plugin API.

Concrete-device workflow
   Use ``ConcreteDevice`` together with a Gupje stub running on the target to
   read and write target memory, synchronize processor state, install
   debugger-specific breakpoints or vectors, and resume execution.

Architecture deep-dive workflow
   Use the ARM64 and RISC-V implementation details to understand how the host
   debugger, storage-backed state model, stepping logic, and page-table helpers
   work internally.

Emulator workflow
   Use ``BaseEmulator`` or an architecture wrapper such as ``ARM64Emulator`` or
   ``RiscvEmulator`` for offline execution, snapshot replay, or testing.




Or all of these together:
- Use the concrete_device to populate a Ghidra project with code and state from an actual device.
- Use an emulator for *hardware in the middle* emulation of IO and devices while helping to reverse the functionality of a firmware.

ConcreteDevice To Ghidra Example
--------------------------------

The following sequence diagram summarizes the same host-side workflow.

.. drawio-viewer:: images/concrete-device-to-ghidra-sequence.drawio
   :height: 420px

.. code-block:: python

   from ghidra_assistant.concrete_device import ConcreteDevice
   from ghidra_assistant.ghidra_assistant import GhidraAssistant

   dump_base = 0x100000
   dump_size = 0x1000

   # The device hook file is responsible for transport setup and any
   # target-specific Gupje bring-up.
   cd = ConcreteDevice(target_dev="my_device.py")
   cd.test_connection()

   memory = cd.mem[dump_base:dump_base + dump_size]

   ga = GhidraAssistant()
   ga.ghidra.memory_create_segment(
      "target_dump",
      dump_base,
      len(memory),
      read=True,
      write=True,
      execute=False,
   )
   ga.ghidra.write_mem(dump_base, memory)