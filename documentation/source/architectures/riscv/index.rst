RISC-V
======

Scope
-----

RISC-V support covers both emulator-side and concrete-debugger-side flows. It
is less feature-rich than ARM64 but already has a coherent architecture.

Main Components
---------------

``GA_riscv_debugger``
   Concrete debugger backend in ``utils/debugger/debugger_archs/ga_riscv.py``.

``RISCV_Concrete_State`` and bit-width variants
   Concrete state mapping helpers for real-target use.

``RiscvEmulator``
   Emulator wrapper in ``utils/archs/riscv/riscv_emulator.py``.

``RiscvProcessorState``
   Register-centric emulator state helper in
   ``utils/archs/riscv/riscv_processor_state.py``.

``RiscvStepper``
   Instruction-step helper in ``utils/archs/riscv/riscv_stepper.py``.

Basic Emulator Example
----------------------

.. code-block:: python

   from ghidra_assistant.utils.archs.riscv.riscv_emulator import RiscvEmulator
   from ghidra_assistant.utils.archs.riscv.riscv_stepper import RiscvStepper

   emu = RiscvEmulator(bits=64)
   emu.mem_map(0x1000, 0x1000, 7)
   emu.pc = 0x1000

   stepper = RiscvStepper(emu)
   print(hex(stepper.get_next_addr()))

Concrete Debugger Path
----------------------

The RISC-V concrete debugger path shares the same overall transport model as
ARM64 but changes the packing logic to fit rv32 or rv64.

The backend handles:

- address packing for 32-bit and 64-bit targets
- shared ``PEEK`` and ``POKE`` behavior via the base class
- basic state synchronization
- restore-and-jump behavior

The biggest functional caveat today is that ``add_hook(...)`` is not yet
implemented in the RISC-V concrete backend.

Concrete backend example:

.. code-block:: python

   from ghidra_assistant.utils.debugger.debugger_archs.ga_riscv import GA_riscv64_debugger

   dbg = GA_riscv64_debugger(0x101000, 0x100000, 0x102000)
   print(hex(dbg.storage_addr))

Emulator Path
-------------

The RISC-V emulator side is more streamlined. ``RiscvEmulator`` exposes a
backend-driven emulation surface with convenient register aliases such as
``a0``, ``sp``, and ``ra``.

``RiscvProcessorState`` adds:

- ABI alias resolution
- masked register reads and writes for the active bit width
- a printable context view
- context restore support

Stepping
--------

``RiscvStepper`` focuses on emulator-side stepping. It decodes the current
instruction, reasons about control flow, and then executes a single instruction
through Unicorn's count-based stepping support.

The stepper has explicit handling for:

- unconditional jumps
- conditional branches
- ``ret``
- ``jalr``

This makes it an important example of how architecture-specific control-flow
logic sits on top of the generic emulator backend.

Processor-state example:

.. code-block:: python

   from ghidra_assistant.utils.archs.riscv.riscv_processor_state import RiscvProcessorState

   state = RiscvProcessorState(emu)
   state.a0 = 0x1234
   print(state.get_ctx(as_dict=True))

TODO:DIAGRAM:Add a RISC-V execution diagram showing the concrete-debugger track, the emulator track, and the current maturity gap between emulator stepping and concrete hooking.