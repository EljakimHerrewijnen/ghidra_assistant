ARM64
=====

ARM64 In This Repository
------------------------

ARM64 is the deepest architecture implementation in the repository. It is the
best reference for understanding how the concrete debugger, the storage-backed
state model, and the MMU helpers are intended to work together.

The first end-to-end target example for this architecture is the Raspberry Pi 4
bring-up built around the ``rpi4_gupje`` repository. That example shows how the
transport setup, debugger upload, ``ConcreteDevice`` wiring, and ARM64-specific
helpers fit together in a runnable environment.

.. toctree::
   :hidden:
   :maxdepth: 1

   raspberry_pi_4

Main Components
---------------

``GA_arm64_debugger``
   The host-side ARM64 concrete debugger backend in
   ``utils/debugger/debugger_archs/ga_arm64.py``.

``ARM64_Concrete_State``
   The storage-backed state abstraction in
   ``utils/archs/arm64/arm64_processor_state.py``.

``ARM64Stepper``
   The ARM64 single-step helper in
   ``utils/archs/arm64/arm64_stepper.py``.

ARM64 MMU helpers
   The register and page-table helpers under ``utils/archs/arm64/misc/`` and
   its ``MMU`` subdirectory.

Basic ARM64 Session
-------------------

.. code-block:: python

   from ghidra_assistant.concrete_device import ConcreteDevice

   cd = ConcreteDevice(target_dev="arm64_target.py")
   cd.fetch_special_regs()

   state = cd.arch_dbg.state
   print(hex(state.VBAR_EL3))
   print(hex(state.TTBR0_EL3))
   print(hex(state.SCTLR_EL3))

Debugger Responsibilities
-------------------------

``GA_arm64_debugger`` implements the ARM64-specific pieces that the base
debugger cannot express generically.

Important responsibilities include:

- packing ARM64 memory parameters for ``PEEK`` and ``POKE``
- generating a VBAR handler page through ``create_debugger_vbar(...)``
- pushing state changes back into hardware with ``sync_state()``
- fetching architecture-specific state with ``fetch_special_regs()``
- resuming execution with ``restore_and_jump(...)``

Storage-Backed State
--------------------

``ARM64_Concrete_State`` exposes the debugger storage page as register-like
properties. This means the host can work with fields such as:

- general-purpose registers ``X0`` through ``X30``
- stack pointer and link register views
- VBAR values
- TTBR values
- SCTLR values
- TCR values
- MAIR values
- ``CURRENT_EL`` and ``NZCV``
- debugger control fields such as the stored jump address and exception ID

The important design point is that these are not abstract Python-only values.
They are views over data stored in target memory and synchronized to live
hardware when the debugger issues the appropriate command.

VBAR Hijacking
--------------

One of the defining ARM64 features in this project is the generated VBAR page.

``create_debugger_vbar(...)`` constructs an exception-vector table that:

- records relevant state into the storage area
- records the exception identity
- branches into the debugger stub

This is how the project implements software-controlled trap entry for the
ARM64 concrete path. It is also why the reserved VBAR page is treated as a
first-class debugger region.

VBAR generation example:

.. code-block:: python

   vbar_blob = cd.arch_dbg.create_debugger_vbar(register="X15")
   cd.memwrite_region(cd.ga_vbar_location, vbar_blob)

Stepping Model
--------------

``ARM64Stepper`` provides a host-side stepping strategy that predicts the next
address, patches in a temporary debugger branch, resumes the target, and then
restores the overwritten instructions.

The stepper is responsible for:

- decoding the current instruction
- resolving branch behavior, including conditional branches
- consulting the current flag state through the stored ``NZCV`` view
- computing the next address
- restoring original bytes after the temporary hook fires

This makes stepping an orchestration problem between disassembly, state
inspection, and temporary patching.

Stepping example:

.. code-block:: python

   from ghidra_assistant.utils.archs.arm64.arm64_stepper import ARM64Stepper

   stepper = ARM64Stepper(cd, pc=0x400000, debug=True)
   print(hex(stepper.get_next_addr()))

TODO:DIAGRAM:Add an ARM64 stepper-flow diagram showing patch, resume, return, restore, and next-PC update behavior.

TODO: Describe the 16-byte absolute-branch limitation and how it can crash the target device.


Page-Table Walks And MMU State
------------------------------

The ARM64 MMU-related code is concentrated in the processor-state helpers and
the ``misc/MMU`` subtree.

At a high level, the page-table walk feature depends on these facts:

- the current TTBR value is exposed through ``ARM64_Concrete_State``
- system-control fields such as ``SCTLR_ELx``, ``TCR_ELx``, and ``MAIR_ELx``
  are also readable through the same state object
- the MMU helper classes interpret those values and parse the relevant table
  structures from target memory

The page walk is therefore not a standalone subsystem. It is a layered feature
built on top of:

1. concrete memory reads from the target
2. storage-backed system-register state
3. descriptor parsing helpers in the ARM64 MMU modules

Register-focused inspection example:

.. code-block:: python

   cd.fetch_special_regs()
   state = cd.arch_dbg.state
   print(state.get_special())
   print(hex(state.TTBR0_EL3))
   print(hex(state.MAIR_EL3))

TODO:DIAGRAM:Add an ARM64 debugger memory-layout diagram showing the debugger page, VBAR page, storage page, stack page, and a small annotated subset of storage-backed fields.

TODO:DIAGRAM:Add an ARM64 pagetable-walk diagram showing TTBR input, descriptor decoding, target memory reads, final mapping resolution, the role of ``ARM64_Concrete_State``, and the MMU helper classes.