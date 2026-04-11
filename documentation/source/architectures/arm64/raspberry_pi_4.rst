Raspberry Pi 4
==============

This is the first concrete ARM64 example in the documentation.

It is based on the ``rpi4_gupje`` codebase, available locally at
``/home/eljakim/Source/Gupje/devices/rpi4_gupje`` and mirrored at
``https://github.com/EljakimHerrewijnen/rpi4_gupje``.

The value of this example is that it is not a toy host-only script. It shows a
complete ARM64 path:

- boot a controllable target environment in QEMU
- upload the Gupje debugger stub
- bind transport functions into ``ConcreteDevice``
- exercise ARM64 stepping and ARM64 state or MMU helpers

Quick Start
-----------

The local README for ``rpi4_gupje`` gives the full build sequence. The short
version is:

1. Install QEMU for ARM.
2. Create a Python environment and install the repository requirements.
3. Build the bare-metal Raspberry Pi image.
4. Build the Gupje debugger payload for the Raspberry Pi target.
5. Run ``qemu.py`` to start the target and upload the debugger.

Typical setup commands:

.. code-block:: console

   sudo apt install qemu-system-arm
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt

   cd rpi4-baremetal-uart
   make

   cd /home/eljakim/Source/Gupje
   make -f devices/rpi4_gupje/Makefile

Then start the target:

.. code-block:: console

   cd /home/eljakim/Source/Gupje/devices/rpi4_gupje
   python3 qemu.py

What ``qemu.py`` does
---------------------

``qemu.py`` is the bring-up example. It starts QEMU, waits for the UART banner,
uploads ``debugger.bin``, and constructs a ``ConcreteDevice`` that is already
wired for ARM64.

The important parts are:

- start ``qemu-system-aarch64`` with the Raspberry Pi machine model
- wait for ``SEND DEBUGGER`` on the serial line
- upload the debugger payload and verify the ``JUMP`` and ``GiAs`` replies
- create a ``RaspberryPi4`` transport object with ``read`` and ``write``
- attach ``GA_arm64_debugger`` and call ``copy_functions()``

The result is a ready-to-use ``cd`` object that the other examples import.

Example 1: Bring-Up And ConcreteDevice Wiring
---------------------------------------------

The transport setup happens inside ``RaspberryPi4.setup_concrete_device(...)``.
This is the smallest useful example of a real ARM64 hook-up:

.. code-block:: python

   concrete_device.arch = "ARM64"
   concrete_device.ga_debugger_location = 0x81000
   concrete_device.ga_vbar_location = 0x82000
   concrete_device.ga_storage_location = 0x85000
   concrete_device.ga_stack_location = 0x83000

   concrete_device.arch_dbg = GA_arm64_debugger(
       concrete_device.ga_vbar_location,
       concrete_device.ga_debugger_location,
       concrete_device.ga_storage_location,
   )
   concrete_device.arch_dbg.read = self.read
   concrete_device.arch_dbg.write = self.write
   concrete_device.copy_functions()

That pattern maps directly onto the ``ConcreteDevice`` and hook-file material in
the main documentation.

Example 2: ARM64 Stepper
------------------------

The stepper example lives in
``examples/arm64_stepper/example_stepper.py``.

Run it from its example directory:

.. code-block:: console

   cd /home/eljakim/Source/Gupje/devices/rpi4_gupje/examples/arm64_stepper
   python3 example_stepper.py

This script imports the ready-made ``cd`` object from ``qemu.py``, writes a
small ARM64 code fragment into a code cave, and then runs ``ARM64Stepper`` over
it.

The example is useful because the shellcode deliberately mixes different branch
forms:

- ``b.eq``
- signed compare and branch behavior
- carry-flag dependent branching
- ``cbz``
- ``tbz``
- ``csel`` and ``ccmp``

The important lines are:

.. code-block:: python

   shellcode_bin = ks.asm(SHELLCODE, as_bytes=True)[0]
   cd.memwrite_region(CODE_CAVE, shellcode_bin)

   cd.arch_dbg.state.NZCV = 0b0
   stepper = ARM64Stepper(cd, CODE_CAVE, True)
   stepper.run(stepper.pc, CODE_CAVE + len(shellcode_bin) - 4)

Use this example when you want to understand how the host predicts control flow
and temporarily patches execution on a concrete ARM64 target.

Example 3: ARM64 Paging And MMU State
-------------------------------------

The paging example lives in
``examples/arm64_paging/example_pagetables.py``.

Run it from the repository root or from the example directory:

.. code-block:: console

   cd /home/eljakim/Source/Gupje/devices/rpi4_gupje/examples/arm64_paging
   python3 example_pagetables.py

This example is earlier and smaller than the stepper example, but it is still a
useful starting point for the MMU-related parts of the ARM64 implementation.

Right now it shows how to treat system state as editable host-side data:

.. code-block:: python

   new_sctrl_el1 = SCTLR_EL1(cd.arch_dbg.state.SCTLR_EL1)
   new_sctrl_el1.mmu = 1
   cd.arch_dbg.state.sctlr_el1 = new_sctrl_el1.value

That is the same storage-backed model described in the ARM64 page: host code
updates a field on the state object, and the concrete debugger later uses that
state to affect live execution.

The current memory map for this example is also documented in
``examples/arm64_paging/pagetable_layout.txt``:

.. code-block:: text

   0x0, 1G, CODE, CODE
   0xfe201000, 4K, DEVICE, UART0

How To Read These Examples
--------------------------

Read them in this order:

1. ``qemu.py`` for transport setup and debugger upload.
2. ``arm64_stepper/example_stepper.py`` for control-flow stepping.
3. ``arm64_paging/example_pagetables.py`` for state and MMU experiments.

That order matches the way the ARM64 support is layered in
``ghidra_assistant`` itself: target bring-up first, execution control second,
and MMU-heavy inspection after the basic debugger loop works.