from __future__ import annotations

from ghidra_assistant.ghidra_assistant import GhidraAssistant


def test_coloring_example_from_legacy_test_py(monkeypatch) -> None:
    """Preserve the old test.py coloring example in ghidra_connection tests."""

    calls = []

    class _FakeGhidra:
        def set_background_color(self, addresses):
            calls.append(("set", addresses))

        def clear_background_color(self):
            calls.append(("clear", None))

    def _fake_setup(self):
        self.ghidra = _FakeGhidra()

    monkeypatch.setattr(GhidraAssistant, "setup", _fake_setup)

    ga = GhidraAssistant(backend="mcp_hydra")
    pc_values = [0x40000000 + i for i in range(0, 0x1000, 4)]

    ga.ghidra.set_background_color(pc_values)
    ga.ghidra.clear_background_color()

    assert calls[0][0] == "set"
    assert len(calls[0][1]) == 0x1000 // 4
    assert calls[0][1][0] == 0x40000000
    assert calls[0][1][-1] == 0x40000000 + 0xFFC
    assert calls[1] == ("clear", None)
