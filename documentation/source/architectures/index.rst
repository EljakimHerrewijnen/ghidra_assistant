Architectures
=============

This section documents the architecture-specific behavior that sits on top of
the generic concrete-device and emulator abstractions.

The order here is intentional.

- ARM64 is the most detailed because it is the richest implementation.
- RISC-V follows as the next most relevant maintained path.
- ARM/Thumb has an explicit documentation space as an older and less-complete
  path.
- The extension guide explains how to add a new architecture without treating
  every older or partial implementation as equal.

.. toctree::
  :hidden:
  :maxdepth: 2

  arm64/index
  riscv/index
  arm_thumb/index
  adding_a_new_architecture/index

This is also where the example-driven material lives.

ARM64 is the primary example architecture today, including the Raspberry Pi 4
bring-up and follow-on examples for stepping and page-table work. RISC-V is the
next strongest maintained path. ARM/Thumb remains documented as an older
secondary path, and the extension guide is aimed at maintainers adding a new
backend.