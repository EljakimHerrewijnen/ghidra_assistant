# Debugger

Host-side implementation of the bare-metal debugger that controls a [Gupje](https://github.com/EljakimHerrewijnen/Gupje) stub running on a real device.

## Structure

- `base_arch.py` — abstract base class; all arch-specific debuggers inherit from this
- `ga_arm64.py` — ARM64 (AArch64) implementation; full command set, VBAR generation, MMU control
- `ga_arm.py` — ARM implementation
- `ga_arm_thumb.py` — ARM Thumb implementation

## Adding a new architecture

Subclass `BaseArch_debugger` and implement the methods that send commands to the Gupje stub (`memdump_region`, `memwrite_region`, `create_debugger_vbar`, `jump_to`, `restore_stack_and_jump`, `sync_state`, `fetch_special_regs`). See the debugger documentation for the full protocol.
