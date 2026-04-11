# ARM64
This folder contains the ARM64 support code for the `Gupje debugger<https://github.com/EljakimHerrewijnen/Gupje>`_.

There are two steppers:

- ``ARM64Stepper`` predicts the next instruction address, places a temporary jump-to-debugger hook there, runs the current instruction, and stops again when execution reaches that hook. If the hook would overlap the current instruction window, it falls back to displaced stepping from scratch memory.
- ``ARM64ExceptionStepper`` extends ``ARM64Stepper`` for synchronous exception instructions such as ``smc``, ``svc``, ``hvc``, and ``brk``. Instead of relying on a normal next-PC hook, it temporarily routes exceptions through the debugger VBAR so the exception returns control to the debugger after a single step.

