from __future__ import annotations

import importlib


class AngrMemory:
    def __init__(self, backend: "AngrBackend"):
        self.backend = backend

    def __getitem__(self, key):
        if isinstance(key, slice):
            start = key.start
            stop = key.stop
            return self.backend.mem_read(start, stop - start)
        if isinstance(key, int):
            return self.backend.mem_read(key, 1)[0]
        raise TypeError("Invalid argument type")

    def __setitem__(self, key, value):
        if isinstance(key, slice):
            start = key.start
            self.backend.mem_write(start, value)
            return
        if isinstance(key, int):
            self.backend.mem_write(key, bytes([value & 0xFF]))
            return
        raise TypeError("Invalid argument type")


class AngrBackend:
    def __init__(self, arch: str, mode: str) -> None:
        self.arch = arch
        self.mode = mode

        try:
            angr = importlib.import_module("angr")
            cle = importlib.import_module("cle")
            io = importlib.import_module("io")
            so = importlib.import_module("angr.sim_options")
        except ImportError as exc:
            raise RuntimeError("angr backend requires angr and cle to be installed") from exc

        arch_map = {
            "arm64": "aarch64",
            "arm": "arm",
        }
        if self.arch not in arch_map:
            raise ValueError(f"Unsupported arch '{self.arch}' for angr backend")

        if self.arch == "arm" and self.mode not in ("arm", "thumb"):
            raise ValueError(f"Unsupported mode '{self.mode}' for arch '{self.arch}'")

        blob = io.BytesIO(b"\x00" * 0x100)
        self.loader = cle.Loader(
            blob,
            main_opts={
                "backend": "blob",
                "arch": arch_map[self.arch],
                "base_addr": 0x0,
                "entry_point": 0x0,
            },
            auto_load_libs=False,
        )
        self.proj = angr.Project(self.loader)
        self.state = self.proj.factory.blank_state(addr=0x0)
        self.state.options.add(so.ZERO_FILL_UNCONSTRAINED_MEMORY)
        self.state.options.add(so.ZERO_FILL_UNCONSTRAINED_REGISTERS)
        self.mem = AngrMemory(self)

    def mem_map(self, addr: int, size: int, perms: int):
        return self.state.memory.map_region(addr, size, perms, init_zero=True)

    def mem_unmap(self, addr: int, size: int):
        raise NotImplementedError("angr backend does not currently support mem_unmap")

    def mem_read(self, addr: int, size: int) -> bytes:
        data = self.state.memory.load(addr, size)
        if hasattr(data, "concrete_value") and isinstance(data.concrete_value, int):
            return int(data.concrete_value).to_bytes(size, byteorder="big", signed=False)
        if hasattr(data, "args") and len(data.args) == 1 and isinstance(data.args[0], bytes):
            return data.args[0]
        return self.state.solver.eval(data, cast_to=bytes)

    def mem_write(self, addr: int, data: bytes):
        return self.state.memory.store(addr, data)

    def mem_regions(self):
        pages = getattr(self.state.memory, "_pages", {})
        regions = []
        for page_index, page in pages.items():
            start = int(page_index) * 0x1000
            end = start + 0x1000 - 1
            perms = getattr(page, "permissions", 0)
            concrete_value = getattr(perms, "concrete_value", None)
            if concrete_value is not None:
                perms = int(concrete_value)
            elif not isinstance(perms, int):
                perms = 0
            regions.append((start, end, perms))
        return sorted(regions)

    def emu_start(self, begin: int, end: int = 0):
        self.state.addr = begin
        self.simgr = self.proj.factory.simulation_manager(self.state)
        if end:
            self.simgr.run(until=lambda simgr: any(s.addr == end for s in simgr.active))
        else:
            self.simgr.run()
        if self.simgr.active:
            self.state = self.simgr.active[0]
        return self.simgr

    def emu_stop(self):
        # Not a primitive operation in angr; keep as a no-op for API parity.
        return None

    def hook_code(self, begin: int, end: int, hook):
        length = max(1, end - begin)
        return self.proj.hook(begin, hook, length=length)

    def hook_mem_read(self, begin: int, end: int, hook):
        return None

    def hook_mem_write(self, begin: int, end: int, hook):
        return None

    def _normalize_register_name(self, name: str) -> str:
        normalized = name.lower()
        if self.arch == "arm64":
            aliases = {
                "lr": "x30",
                "fp": "x29",
            }
            return aliases.get(normalized, normalized)

        # arm backend
        if normalized.startswith("x") and normalized[1:].isdigit():
            return f"r{int(normalized[1:])}"
        aliases = {
            "fp": "r11",
        }
        return aliases.get(normalized, normalized)

    def get_register(self, name: str) -> int:
        register_name = self._normalize_register_name(name)
        reg = getattr(self.state.regs, register_name)
        if hasattr(reg, "concrete_value"):
            return int(reg.concrete_value)
        return int(self.state.solver.eval(reg))

    def set_register(self, name: str, value: int):
        register_name = self._normalize_register_name(name)
        setattr(self.state.regs, register_name, int(value))



def create_angr_backend(arch: str, mode: str, **_backend_kwargs):
    return AngrBackend(arch, mode)
