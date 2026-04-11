Emulator
========

The emulator layer is present to support analysis and replay workflows, but it
is not the main focus of the project. Treat it as supporting infrastructure
rather than the first place to start.

Core API
--------

The current emulator implementation revolves around ``BaseEmulator`` in
``utils/emulator/base_emulator.py``. It provides a backend-agnostic facade for:

- memory mapping and memory access
- register reads and writes
- execution control
- lightweight hook registration

Primary Backend
---------------

The primary backend is ``UnicornBackend`` in
``utils/emulator/unicorn_backend.py``.

It supports:

- ARM64
- ARM
- RISC-V 32 and 64
- x86 and x86_64

The backend builds register maps lazily and provides a uniform API for the
common operations that ``BaseEmulator`` forwards.

Example with ``BaseEmulator``:

.. code-block:: python

	from ghidra_assistant.utils.emulator.base_emulator import BaseEmulator

	emu = BaseEmulator("arm64", "arm", backend="unicorn")
	emu.mem_map(0x1000, 0x1000, 7)
	emu.mem_write(0x1000, b"\x00\x00\x00\x00")
	emu.set_register("PC", 0x1000)

Hedgehog Backend
----------------

``HedgehogBackend`` lives in
``utils/emulator/hedgehog_backend.py``.

The current integration is intentionally narrow:

- board-backed mode only
- ARM64 only in the first implementation
- memory map, memory read and write, register access, execution, and code hooks
- the latest tested Hedgehog release fixes the plain ``emu_start(begin, 0)`` path, so the adapter now forwards directly to Hedgehog execution again
- no ``mem_unmap`` support yet
- no normal memory read or write hook bridging yet
- repeated Hedgehog create/close cycles are still unstable in one Python process

The dependency is optional. Install the latest release wheel from the QEMU fork
before selecting ``backend="hedgehog"``.

Example:

.. code-block:: python

	from ghidra_assistant.utils.emulator.base_emulator import BaseEmulator

	emu = BaseEmulator("arm64", "arm", backend="hedgehog")
	emu.mem_map(0x400000, 0x1000, 7)
	emu.mem_write(0x400000, b"\x1f\x20\x03\xd5")
	emu.set_register("PC", 0x400000)
	emu.emu_start(0x400000, 0)

Secondary Backend
-----------------

``AngrBackend`` exists in ``utils/emulator/angr_backend.py`` but should be
treated as a work-in-progress backend.

The current limits are:

- some operations are partial or no-op
- ``mem_unmap`` is not implemented
- the overall path is less complete than the Unicorn path

Architecture Wrappers
---------------------

Two architecture wrappers deserve mention because they are practical and align
with the current code:

- ``ARM64Emulator``
- ``RiscvEmulator``

These wrappers add architecture-specific convenience behavior such as register
aliases and local disassembly helpers while still relying on the backend-driven
emulator core.

Wrapper example:

.. code-block:: python

	from ghidra_assistant.utils.archs.arm64.arm64_emulator import ARM64Emulator

	emu = ARM64Emulator()
	emu.X0 = 0x1234
	emu.pc = 0x1000
	print(emu.get_registers())

Current Scope
-------------

This documentation intentionally keeps the emulator section lighter than the
Ghidra and concrete-device sections.

The project's most distinctive workflows are the Ghidra path and the
ConcreteDevice plus Gupje path, so this section stays focused on the emulator
surface that is already practical.

TODO:DIAGRAM:Add an emulator architecture diagram centered on ``BaseEmulator`` with backend registration, ``UnicornBackend`` as the primary branch, ``AngrBackend`` as a WIP branch, and architecture wrappers such as ``ARM64Emulator`` and ``RiscvEmulator``.