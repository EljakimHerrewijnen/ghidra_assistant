Device Hook Files
=================

There are two main workflows for using the Ghidra Assistant on a concrete device:

    1. Import the ghidra_assistant package and use the ``ConcreteDevice`` class directly in a Python
      script
    2. Create a custom device hook file that binds transport functions and selects an architecture debugger, then use the ``ConcreteDevice`` class with the hook file as a parameter.

Role Of Hook Files
------------------

The project does not hard-code transports or target devices into the core
library. Instead, ``ConcreteDevice`` loads a Python file at runtime and lets it
provide the missing target-specific glue.

This hook-file pattern keeps the framework generic while allowing a single
target integration to define:

- transport specifics
- address layout changes
- architecture debugger selection
- device-specific startup actions

Minimal Pattern
---------------

The minimum practical hook file usually provides:

- ``device_setup(cd)``
- optionally ``device_main(cd, args)``

Inside ``device_setup(cd)``, the usual steps are:

1. instantiate or bind the transport implementation
2. select the architecture debugger backend
3. assign ``cd.arch_dbg``
4. bind ``cd.arch_dbg.read`` and ``cd.arch_dbg.write`` to the transport
5. call ``cd.copy_functions()``

Skeleton Example
----------------

.. code-block:: python

   from ghidra_assistant.utils.debugger.debugger_archs.ga_arm64 import GA_arm64_debugger

   class Transport:
       def read(self, length: int) -> bytes:
           ...

       def write(self, data: bytes) -> None:
           ...

   def device_setup(cd):
       transport = Transport()

       cd.arch = "ARM64"
       cd.ga_debugger_location = 0x100000
       cd.ga_vbar_location = 0x101000
       cd.ga_storage_location = 0x102000
       cd.ga_stack_location = 0x103000

       cd.arch_dbg = GA_arm64_debugger(
           cd.ga_vbar_location,
           cd.ga_debugger_location,
           cd.ga_storage_location,
       )
       cd.arch_dbg.read = transport.read
       cd.arch_dbg.write = transport.write
       cd.copy_functions()

   def device_main(cd, args):
       cd.test_connection()

Hook File Scope
---------------

Hook files should stay focused on target-specific integration. They should not
reimplement architecture-debugger logic that already belongs in the core source
tree.

Good hook-file responsibilities:

- transport binding
- target-specific addresses
- bootstrapping or probing steps
- invoking the existing debugger backend

Poor hook-file responsibilities:

- reimplementing memory packet formats
- embedding architecture register layouts
- duplicating generic debugger behavior already present in ``BaseArch_debugger``

Using the hook file:

.. code-block:: python

    from ghidra_assistant.concrete_device import ConcreteDevice

    cd = ConcreteDevice(target_dev="my_device.py")
    cd.test_connection()
    print(hex(cd.get_debugger_location()))

TODO:DIAGRAM:Add a device-hook wiring diagram showing ``device_setup(cd)``, transport creation, ``arch_dbg`` setup, and ``copy_functions()``.