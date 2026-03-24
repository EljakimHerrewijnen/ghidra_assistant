===========
GA Emulator
===========

The GA emulator is a setup layer on top of `Unicorn <https://www.unicorn-engine.org/>`_. It populates the emulator's memory and registers from one of several sources: a Ghidra project (via any backend), a concrete device snapshot, or an existing memory dump.

Memory is represented as a list of ``GA_Memory_Segment`` objects, each with a start address, size, content, and RWX permissions. Registers are stored in ``GA_Em_Snapshot``, which can be pickled and reloaded for offline replay.

Snapshot workflow
-----------------

1. Dump memory and registers from a live target via ``ConcreteDevice``.
2. Save the state to disk with ``GA_Em_Snapshot.save_to_file(path)``.
3. Load the snapshot into Unicorn and run or single-step.

Device-specific emulator setup
--------------------------------

For each target a small ``GA_emulator.py`` file provides two hooks:

.. code-block:: python

    def emulator_setup(em: "GA_Emulator"):
        # map additional MMIO regions, register hook callbacks, etc.
        pass

    def emulator_main(em: "GA_Emulator"):
        # start emulation or run a test case
        pass

Pass the path to this file when constructing ``GA_Emulator`` (analogous to how ``ConcreteDevice`` loads device hooks).

