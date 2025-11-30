"""Fuse-based memory filesystem helpers for exposing Unicorn regions as files."""

from __future__ import annotations

import os
import stat
import threading
from typing import Dict, List, Optional, Tuple

try:  # pragma: no cover - optional dependency
    from fuse import FUSE, Operations  # type: ignore
    _HAVE_FUSEPY = True
except Exception:  # pragma: no cover
    FUSE = None  # type: ignore
    class Operations:  # type: ignore
        pass
    _HAVE_FUSEPY = False

__all__ = ["EmuMemoryFS", "mount_in_background"]


def _region_filename(base: int, end: int) -> str:
    return f"region_{base:08x}_{end:08x}.bin"


class EmuMemoryFS(Operations):  # pragma: no cover
    """Expose Unicorn memory regions as files backed by uc.mem_read/write."""

    def __init__(self, emulator, regions: List[Tuple[int, int, int]]):
        self.emu = emulator
        self.regions: Dict[str, Tuple[int, int, int]] = {
            '/' + _region_filename(base, end): (base, end, perms)
            for base, end, perms in regions
        }
        try:
            self._start_time = int(os.path.getmtime(__file__))
        except Exception:
            self._start_time = 0

    def readdir(self, path, fh):
        yield '.'
        yield '..'
        if path == '/':
            for p in self.regions:
                yield p[1:]

    def getattr(self, path, fh=None):
        if path in ('', '/'):
            return {
                'st_mode': stat.S_IFDIR | 0o755,
                'st_nlink': 2,
                'st_ctime': self._start_time,
                'st_mtime': self._start_time,
                'st_atime': self._start_time,
            }
        region = self.regions.get(path)
        if not region:
            raise FileNotFoundError
        base, end, perms = region
        size = end - base
        mode_bits = 0o644 if (perms & 2) else 0o444
        return {
            'st_mode': stat.S_IFREG | mode_bits,
            'st_nlink': 1,
            'st_size': size,
            'st_ctime': self._start_time,
            'st_mtime': self._start_time,
            'st_atime': self._start_time,
        }

    def open(self, path, flags):
        if path not in self.regions:
            raise FileNotFoundError
        base, end, perms = self.regions[path]
        writable = bool(perms & 2)
        access_mode = flags & 0x3
        if access_mode in (1, 2) and not writable:
            raise PermissionError
        return 0

    def read(self, path, size, offset, fh):
        region = self.regions.get(path)
        if not region:
            raise FileNotFoundError
        base, end, _ = region
        region_size = end - base
        if offset >= region_size:
            return b''
        size = min(size, region_size - offset)
        return bytes(self.emu.uc.mem_read(base + offset, size))

    def write(self, path, data, offset, fh):
        region = self.regions.get(path)
        if not region:
            raise FileNotFoundError
        base, end, perms = region
        if not (perms & 2):
            raise PermissionError
        region_size = end - base
        if offset >= region_size:
            return 0
        write_len = min(len(data), region_size - offset)
        if write_len > 0:
            self.emu.uc.mem_write(base + offset, data[:write_len])
        return write_len

    def truncate(self, path, length):
        if path not in self.regions and path != '/':
            raise FileNotFoundError
        return 0

    def create(self, path, mode, fi=None):
        raise PermissionError

    def unlink(self, path):
        raise PermissionError

    def rename(self, old, new):
        raise PermissionError


def mount_in_background(emulator, mountpoint: str) -> Optional[threading.Thread]:
    """Attempt to mount the memory FS in a background thread."""

    if not _HAVE_FUSEPY:
        return None
    regions = list(emulator.uc.mem_regions())
    fs = EmuMemoryFS(emulator, regions)
    os.makedirs(mountpoint, exist_ok=True)

    def _run():
        try:
            FUSE(fs, mountpoint, foreground=True, allow_other=False)  # type: ignore
        except Exception:
            pass

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t
