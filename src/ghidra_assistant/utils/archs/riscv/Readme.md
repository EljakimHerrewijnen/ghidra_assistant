# RISC-V

RISC-V architecture support for both emulator and concrete debugger flows.

## Contents

- `riscv_emulator.py` - Unicorn-backed emulator facade for rv32/rv64.
- `riscv_processor_state.py` - register-centric processor-state helper for emulation.
- `riscv_stepper.py` - instruction stepper for emulation.
- `riscv_concrete_state.py` - storage-mapped register state for concrete debugger backends.
- `riscv32/` and `riscv64/` - convenience wrappers for bitness-specific state and steppers.

## Notes

The debugger backend implementation lives in `utils/debugger/debugger_archs/ga_riscv.py`.

