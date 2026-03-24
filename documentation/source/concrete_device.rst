===============
Concrete Device
===============

``ConcreteDevice`` (``src/ghidra_assistant/concrete_device.py``) is the Python abstraction for a real hardware target. It wraps the `Gupje <https://github.com/EljakimHerrewijnen/Gupje>`_ stub running on the device and exposes a Pythonic API for memory access, register management, and breakpoint control.

Memory layout
-------------

Four 4 KiB pages must be reserved in device memory before the debugger can be used. The default locations are:

+------------------------+-------------+
| Purpose                | Address     |
+========================+=============+
| Debugger stub (code)   | ``0x100000``|
+------------------------+-------------+
| VBAR (vector table)    | ``0x101000``|
+------------------------+-------------+
| Storage (register dump)| ``0x102000``|
+------------------------+-------------+
| Debugger stack         | ``0x103000``|
+------------------------+-------------+

These can be relocated at any time with ``relocate_debugger(vbar, debugger, storage)``. The three regions must not overlap and must each be 4 KiB apart.

Memory access
-------------

The ``Mem`` helper attached to every ``ConcreteDevice`` instance supports Python slice notation:

.. code-block:: python

    data = cd.mem[0x100000:0x101000]   # read 4 KiB
    cd.mem[0x100000:0x100010] = b"\x00" * 16

Internally this calls ``memdump_region`` / ``memwrite_region``, which send PEEK / POKE commands to the Gupje stub.

Device file (hooks)
--------------------

Provide a Python file that defines ``device_setup`` (and optionally ``device_main``):

.. code-block:: python

    # my_device.py
    from ghidra_assistant.utils.debugger.debugger_archs.ga_arm64 import GA_arm64_debugger

    class _Transport:
        """Minimal read/write over your hardware transport."""
        def read(self, length: int) -> bytes:
            ...  # read from USB/UART/etc.

        def write(self, data: bytes) -> None:
            ...  # write to USB/UART/etc.

    def device_setup(cd):
        t = _Transport()

        cd.arch = "ARM64"
        cd.ga_debugger_location = 0x100000
        cd.ga_vbar_location     = 0x101000
        cd.ga_storage_location  = 0x102000
        cd.ga_stack_location    = 0x103000

        cd.arch_dbg = GA_arm64_debugger(
            cd.ga_vbar_location,
            cd.ga_debugger_location,
            cd.ga_storage_location,
        )
        cd.arch_dbg.read  = t.read
        cd.arch_dbg.write = t.write
        cd.copy_functions()  # binds arch_dbg methods onto cd

    def device_main(cd, args):
        """Called when the device file is run directly."""
        cd.test_connection()

Pass the path to this file when constructing ``ConcreteDevice``:

.. code-block:: python

    from ghidra_assistant.concrete_device import ConcreteDevice

    cd = ConcreteDevice(target_dev="my_device.py")
    cd.test_connection()
    data = cd.mem[0x100000:0x101000]

``copy_functions()``
--------------------

``copy_functions()`` copies the architecture-specific implementations from ``arch_dbg`` (e.g. ``GA_arm64_debugger``) onto the ``ConcreteDevice`` instance. Call it after assigning ``arch_dbg`` and binding transport functions so that calls like ``cd.memdump_region(...)`` dispatch to the correct architecture logic.

Probing memory
--------------

``auto_probe_memory()`` sweeps the address space and identifies readable regions. It recovers from transport timeouts automatically:

.. code-block:: python

    ranges = cd.auto_probe_memory(start=0, end=4 * GB, bs=1 * MB)
    for r in ranges:
        print(hex(r.address), r.size, r.name)
