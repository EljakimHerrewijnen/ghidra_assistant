Adding A New Architecture
=========================

Goal
----

This guide is for maintainers who want to add a new concrete-device
architecture. It is not an end-user workflow. The point is to explain the
minimum set of moving parts needed to make a new target architecture coherent in
the existing design.

Required Pieces
---------------

1. A new debugger backend subclass of ``BaseArch_debugger``.
2. A concrete state mapping class for the storage page.
3. A device hook file that binds transport read and write functions.
4. Tests or executable examples that prove the new path works.
5. Documentation updates for the new architecture and its diagrams.

Debugger Backend Contract
-------------------------

The new debugger backend must inherit from
``utils/debugger/debugger_archs/base_arch.py`` and implement the pieces that are
architecture-dependent.

At minimum, implement:

- memory read parameter packing and ``memdump_region(...)``
- memory write parameter packing and ``memwrite_region(...)``
- ``get_debugger_location()``
- ``jump_to(...)``
- ``sync_state()``
- ``restore_stack_and_jump(...)``
- ``fetch_special_regs()`` when the architecture has meaningful special state

If the architecture uses a vector table, trap table, or other architecture-
specific breakpoint entry mechanism, that also belongs here.

Minimal backend skeleton:

.. code-block:: python

   from ghidra_assistant.utils.debugger.debugger_archs.base_arch import BaseArch_debugger

   class GA_newarch_debugger(BaseArch_debugger):
     def memdump_region(self, offset, size):
       ...

     def memwrite_region(self, address, data):
       ...

     def get_debugger_location(self):
       ...

     def jump_to(self, address):
       ...

     def sync_state(self):
       ...

     def restore_stack_and_jump(self, address, stack: bytes = b""):
       ...

Concrete State Mapping
----------------------

The next required component is a state object that maps logical register or
control fields onto the storage page used by the target stub.

ARM64 is the richest example.
RISC-V is the simpler example.

The state class should answer these questions clearly:

- what offsets correspond to general registers
- what offsets correspond to special registers
- which fields are synced automatically and which require explicit calls
- how the host writes jump targets or continuation metadata into the storage
  page

Device Integration
------------------

The architecture is not usable until a device hook file wires it into
``ConcreteDevice``.

That hook file must:

- instantiate the new debugger backend
- bind transport ``read`` and ``write`` methods
- assign it to ``cd.arch_dbg``
- call ``cd.copy_functions()``

Hook-file integration sketch:

.. code-block:: python

   def device_setup(cd):
     transport = Transport()
     cd.arch = "NEWARCH"
     cd.arch_dbg = GA_newarch_debugger(0x101000, 0x100000, 0x102000)
     cd.arch_dbg.read = transport.read
     cd.arch_dbg.write = transport.write
     cd.copy_functions()

Reference Implementations
-------------------------

Use these as models, in order:

- ``GA_arm64_debugger`` for the richest end-to-end reference
- ``GA_riscv_debugger`` for a simpler modern backend
- ``ARM64_Concrete_State`` for a detailed storage-backed state map

Practical Acceptance Criteria
-----------------------------

Before treating a new architecture as documented and supported, it should be
able to do at least these things:

- identify the debugger stub location
- read target memory
- write target memory
- synchronize stored state back into live execution state
- resume execution at a chosen address

Features such as stepping, trap hijacking, or MMU helpers can be added after
that baseline works.

TODO:DIAGRAM:Add a maintainer-facing component map showing ``BaseArch_debugger``, the new debugger subclass, the new concrete state class, the device hook file, optional assembler helpers, and the required test and documentation outputs.