Protocol And Memory Model
=========================

Protocol Shape
--------------

The host-side debugger backends derive from ``BaseArch_debugger`` in
``utils/debugger/debugger_archs/base_arch.py``. The base class provides common
PEEK and POKE behavior through shared helper methods.

The transport contract is intentionally simple:

- send a 4-byte command word
- send command-specific parameters if needed
- stream data or receive data
- exchange acknowledgements where the protocol requires them

Common Command Words
--------------------

The concrete backends use a small set of command words repeatedly:

``PING``
   Simple connectivity check.

``PEEK``
   Read memory from the target.

``POKE``
   Write memory to the target.

``SELF``
   Ask the stub for its main debugger location.

``SYNC``
   Push state from the storage page back into live hardware registers.

``SPEC``
   Fetch architecture-specific special-register state into the storage page.

``REST``
   Restore state and resume execution at the jump address stored in the storage
   page.

``JUMP``
   Transfer control to an address without the full restore path.

``FLSH``
   Flush caches where the target stub supports it.

Shared PEEK/POKE Behavior
-------------------------

The common behavior lives in ``_memdump_region_impl(...)`` and
``_memwrite_region_impl(...)``.

``_memdump_region_impl(...)``
   Sends ``PEEK``, sends the architecture-specific address-and-size payload,
   receives data in blocks, and acknowledges each block.

``_memwrite_region_impl(...)``
   Sends ``POKE``, sends the architecture-specific address-and-size payload,
   writes the data in blocks, and expects ``OK`` responses from the target.

Host-side examples:

.. code-block:: python

   data = cd.memdump_region(0x400000, 0x40)
   print(data.hex())

.. code-block:: python

   cd.memwrite_region(0x400000, b"\x01\x02\x03\x04")
   cd.sync_state()

.. code-block:: python

   cd.fetch_special_regs()
   cd.restore_stack_and_jump(0x400800)

Architecture Differences
------------------------

The command words are shared, but the address packing differs by architecture.

ARM64
   Uses ``struct.pack('<QI', address, size)`` for most memory operations.

ARM Thumb and older ARM paths
   Use 32-bit oriented parameter layouts.

RISC-V
   Uses either a 64-bit or 32-bit packing path depending on the configured
   target bit width.

Storage-Backed State Model
--------------------------

The concrete debugger model relies on a storage page in target memory. The host
reads and writes logical register fields by writing offsets inside that page.

This is the central idea behind classes such as ``ARM64_Concrete_State`` and
``RISCV_Concrete_State``:

- read a field from the target by dumping the corresponding storage offset
- write a field by patching the corresponding offset
- call ``SYNC`` or the special-register sync path when the live hardware state
  should be updated

That design makes the protocol simpler because many state edits become regular
memory writes rather than bespoke transport commands.

State update example:

.. code-block:: python

   state = cd.arch_dbg.state
   state.DEBUGGER_JUMP = 0x400800
   state.X0 = 0x1234
   cd.sync_state()

TODO:DIAGRAM:Add a debugger command-sequence diagram showing the host debugger backend, the transport layer, the Gupje stub, one ``PEEK`` exchange, one ``POKE`` exchange, and where ``SYNC`` and ``REST`` interact with the storage page.

TODO:DIAGRAM:Add a storage-backed state-sync diagram showing the host state object, storage-page offsets, target registers, and the sync or restore paths.