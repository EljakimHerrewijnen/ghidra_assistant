from __future__ import annotations

import importlib
from typing import Any


def _build_arm64_reg_map() -> dict[str, tuple[int, int]]:
    reg_map: dict[str, tuple[int, int]] = {}
    for index in range(31):
        reg_map[f"X{index}"] = (index, 8)
        reg_map[f"W{index}"] = (index, 4)

    reg_map.update(
        {
            "SP": (31, 8),
            "PC": (32, 8),
            "NZCV": (33, 4),
            "LR": (30, 8),
            "FP": (29, 8),
            "X29": (29, 8),
            "X30": (30, 8),
            "W29": (29, 4),
            "W30": (30, 4),
        }
    )
    return reg_map


class HedgehogBackend:
    def __init__(
        self,
        arch: str,
        mode: str,
        *,
        cpu_type: str | None = None,
        library_path: str | None = None,
        backend: Any | None = None,
        machine_type: str | None = None,
        chardevs: dict[str, str] | None = None,
        property_bindings: dict[str, dict[str, str]] | None = None,
        serial_backends: dict[int, str] | None = None,
        **unknown_kwargs: Any,
    ) -> None:
        if unknown_kwargs:
            unknown = ", ".join(sorted(unknown_kwargs))
            raise TypeError(f"Unsupported hedgehog backend arguments: {unknown}")

        unsupported = []
        if machine_type is not None:
            unsupported.append("machine_type")
        if chardevs:
            unsupported.append("chardevs")
        if property_bindings:
            unsupported.append("property_bindings")
        if serial_backends:
            unsupported.append("serial_backends")
        if unsupported:
            names = ", ".join(unsupported)
            raise ValueError(
                "Hedgehog backend currently supports board-backed mode only; "
                f"unsupported arguments: {names}"
            )

        try:
            self._hh = importlib.import_module("qemu.hedgehog")
            from ..archs.arm.memory_proxy import MemoryProxy
        except ImportError as exc:
            raise RuntimeError(
                "hedgehog backend requires qemu.hedgehog to be installed; "
                "install the latest release wheel from "
                "https://github.com/EljakimHerrewijnen/qemu/releases/latest"
            ) from exc

        self.arch = arch
        self.mode = mode
        self._regions: list[tuple[int, int, int]] = []

        if arch != "arm64":
            raise ValueError(
                f"Unsupported arch '{arch}' for hedgehog backend; supported archs: arm64"
            )
        if mode not in ("arm", "aarch64"):
            raise ValueError(f"Unsupported mode '{mode}' for arch 'arm64'")

        self._reg_map = _build_arm64_reg_map()
        self._emu = self._hh.Hedgehog(
            self._hh.HEDGEHOG_ARCH_ARM64,
            self._hh.HEDGEHOG_MODE_ARM,
            cpu_type=cpu_type or "cortex-a53",
            library_path=library_path,
            backend=backend,
        )
        self.mem = MemoryProxy(self)

    def close(self) -> None:
        self._emu.close()

    def mem_map(self, addr: int, size: int, perms: int):
        self._emu.mem_map(addr, size, perms)
        self._regions.append((addr, addr + size - 1, perms))

    def mem_unmap(self, addr: int, size: int):
        raise NotImplementedError("hedgehog backend does not currently support mem_unmap")

    def mem_read(self, addr: int, size: int) -> bytes:
        return bytes(self._emu.mem_read(addr, size))

    def mem_write(self, addr: int, data: bytes):
        self._emu.mem_write(addr, data)

    def mem_regions(self):
        return sorted(self._regions)

    def emu_start(self, begin: int, end: int = 0):
        return self._emu.emu_start(begin, end)

    def emu_stop(self):
        return self._emu.emu_stop()

    def qemu_run(self, max_instructions: int = 0):
        return self._emu.qemu_run(max_instructions)

    def qemu_set_pc(self, address: int):
        return self._emu.qemu_set_pc(address)

    def qemu_get_pc(self) -> int:
        return int(self._emu.qemu_get_pc())

    def hook_code(self, begin: int, end: int, hook):
        callback = self._wrap_code_hook(hook)
        return self._emu.hook_add(self._hh.HEDGEHOG_HOOK_CODE, callback, begin=begin, end=end)

    def hook_mem_read(self, begin: int, end: int, hook):
        raise NotImplementedError(
            "hedgehog backend does not currently expose normal memory-read hooks via BaseEmulator"
        )

    def hook_mem_write(self, begin: int, end: int, hook):
        raise NotImplementedError(
            "hedgehog backend does not currently expose normal memory-write hooks via BaseEmulator"
        )

    def get_register(self, name: str) -> int:
        regno, size = self._resolve_register(name)
        if regno == 32:
            return int(self._emu.qemu_get_pc())
        return int(self._emu.reg_read(regno, size=size))

    def set_register(self, name: str, value: int):
        regno, size = self._resolve_register(name)
        if regno == 32:
            self._emu.qemu_set_pc(int(value))
            return

        payload = int(value).to_bytes(size, byteorder="little", signed=False)
        self._emu.reg_write(regno, payload)

    def _resolve_register(self, name: str) -> tuple[int, int]:
        key = name.upper()
        reg = self._reg_map.get(key)
        if reg is None:
            raise KeyError(f"Unsupported register '{name}'")
        return reg

    def _wrap_code_hook(self, hook):
        if hasattr(hook, "hook_unicorn"):
            return lambda _emu, address, size, user_data: hook.hook_unicorn(self, address, size, user_data)
        return hook


def create_hedgehog_backend(arch: str, mode: str, **backend_kwargs):
    return HedgehogBackend(arch, mode, **backend_kwargs)