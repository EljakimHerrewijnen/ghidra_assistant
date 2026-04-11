ConcreteDevice Overview
=======================

Purpose
-------

``ConcreteDevice`` in ``src/ghidra_assistant/concrete_device.py`` is the host
abstraction for a real target device. It does not implement a transport by
itself. Instead, it loads a device-specific hook file and delegates
architecture-specific behavior to an ``arch_dbg`` object.

The class is designed to sit between:

- your Python tooling on the host
- a device-specific transport implementation such as USB or UART
- a Gupje stub running on the target
- an architecture debugger backend such as ``GA_arm64_debugger``

Key Responsibilities
--------------------

``ConcreteDevice`` is responsible for:

- loading a device hook file through ``insert_hooks_from_file(...)``
- storing the standard debugger memory addresses
- exposing the slice-based ``mem`` helper for memory reads and writes
- binding host calls such as ``memdump_region`` and ``jump_to`` to the current
  architecture debugger through ``copy_functions()``

It is intentionally not the place where architecture-specific packet formats or
register layouts are defined. Those live in the architecture debugger and state
classes.

Example Session
---------------

.. code-block:: python

  from ghidra_assistant.concrete_device import ConcreteDevice

  cd = ConcreteDevice(target_dev="my_device.py")
  cd.test_connection()

  page = cd.mem[0x100000:0x101000]
  print(len(page))

  cd.mem[0x100100:0x100104] = b"ABCD"
  cd.ping()

Control Flow
------------

Think of the stack like this:

1. your script uses ``ConcreteDevice``
2. ``ConcreteDevice`` loads a device hook file
3. the hook file binds transport ``read`` and ``write`` functions
4. the hook file installs an architecture debugger instance in ``cd.arch_dbg``
5. ``copy_functions()`` forwards memory and execution helpers to that backend
6. the backend speaks the Gupje command protocol to the target

Reserved Memory Regions
-----------------------

By convention, four 4 KiB pages are reserved on the target:

+------------------------+-------------+
| Purpose                | Address     |
+========================+=============+
| Debugger stub          | ``0x100000``|
+------------------------+-------------+
| VBAR or trap page      | ``0x101000``|
+------------------------+-------------+
| Storage page           | ``0x102000``|
+------------------------+-------------+
| Debugger stack         | ``0x103000``|
+------------------------+-------------+

These defaults can be changed with ``relocate_debugger(...)`` as long as the
regions remain properly separated.

Relocation example:

.. code-block:: python

   cd.relocate_debugger(
     vbar_location=0x201000,
     debugger_location=0x202000,
     storage_location=0x203000,
   )

TODO:DIAGRAM:Add a ConcreteDevice stack diagram showing the host script, ``ConcreteDevice``, the device hook file, the architecture debugger backend, the transport boundary, the Gupje stub, and the reserved debugger regions.