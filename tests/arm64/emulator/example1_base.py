"""Base ARM64 emulator example test.

This file intentionally uses a custom name requested by the user:
`tests/arm64/emulator/example1_base.py`

Run it explicitly with pytest by passing the file path.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

# Ensure src/ is importable when running tests from repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

pytest.importorskip("unicorn")
pytest.importorskip("capstone")
pytest.importorskip("keystone")

from ghidra_assistant.utils.archs.arm64.arm64_emulator import ARM64UC_Emulator

def test_example1_base_map_read_write() -> None:
    """Map memory and verify read/write round-trip."""
    emu = ARM64UC_Emulator()
    base = 0x1000
    size = 0x1000

    emu.uc.mem_map(base, size)
    payload = b"\x01\x02\x03\x04"
    emu.uc.mem_write(base, payload)

    assert bytes(emu.uc.mem_read(base, len(payload))) == payload
    assert emu.is_mapped(base)


def test_example1_base_pc_roundtrip() -> None:
    """Check simple register property usage."""
    emu = ARM64UC_Emulator()
    emu.pc = 0x4000
    assert emu.pc == 0x4000
