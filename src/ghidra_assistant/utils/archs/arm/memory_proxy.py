class MemoryProxy:
    """Convenient byte-addressable view over a Unicorn memory instance."""

    def __init__(self, uc):
        self.uc = uc

    def __getitem__(self, item):
        if isinstance(item, slice):
            if item.step not in (None, 1):
                raise ValueError('Memory slice step must be 1 or None')
            start = item.start or 0
            stop = item.stop
            if stop is None:
                raise ValueError('Open-ended slice not supported')
            return self.uc.mem_read(start, stop - start)
        if isinstance(item, int):
            return self.uc.mem_read(item, 1)[0]
        raise TypeError('Index must be int or slice')

    def __setitem__(self, item, value):
        if isinstance(item, slice):
            if item.step not in (None, 1):
                raise ValueError('Memory slice step must be 1 or None')
            start = item.start or 0
            stop = item.stop
            if stop is None:
                raise ValueError('Open-ended slice not supported')
            if not isinstance(value, (bytes, bytearray)):
                raise TypeError('Slice assignment requires bytes-like')
            if (stop - start) != len(value):
                raise ValueError('Slice length mismatch')
            self.uc.mem_write(start, value)
            return
        if isinstance(item, int):
            if not isinstance(value, int) or not (0 <= value <= 0xFF):
                raise TypeError('Single-byte assignment requires int 0..255')
            self.uc.mem_write(item, bytes([value]))
            return
        raise TypeError('Index must be int or slice')
