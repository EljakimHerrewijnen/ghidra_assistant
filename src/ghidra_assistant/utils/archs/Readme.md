# Architectures

Architecture-specific emulator and debugger support. Each architecture lives in its own sub-directory and provides:

- An emulator class wrapping Unicorn (`arm_emulator.py`, `arm64_emulator.py`)
- A processor state class for the concrete (hardware) debugger (`armT_processor_state.py`, `arm64_processor_state.py`)
- Architecture-specific assembler/disassembler helpers (`asm_arm64.py`, `asm_utils.py`)

Currently supported:

| Architecture | Emulator | Debugger | Notes |
|--------------|----------|----------|-------|
| ARM64        | ✓        | ✓        | EL3/EL1, MMU parsing |
| ARM Thumb    | ✓        | ✓        | Basic register state |
| ARM          | partial  | –        | Minimal |
| RISC-V       | ✓        | ✓        | rv32/rv64 emulator + debugger backend |
