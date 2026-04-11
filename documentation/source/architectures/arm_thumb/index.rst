ARM/Thumb
=========

Scope
-----

This page is the documentation space for the older ARM and Thumb architecture
paths.

The documentation set still focuses primarily on ARM64 and RISC-V because those
paths are covered in more depth. ARM/Thumb remains relevant, but it should be
treated as a secondary path until the backend-specific details are documented
here.

Current Position
----------------

Use this section when you need to document or review:

- older 32-bit ARM concrete-debugger behavior
- Thumb-specific execution or stepping notes
- ARM/Thumb bring-up details that do not belong on the generic protocol page

Current Documented Facts
------------------------

The clearest documented protocol difference today is in the memory-operation
packing used by the concrete debugger layer.

- ARM64 uses 64-bit address-oriented packing for most memory operations.
- ARM/Thumb and older ARM paths use 32-bit oriented parameter layouts.

Protocol Shape
--------------

ARM/Thumb still sits inside the same overall concrete-device transport model as
the other architectures.

- the shared command words remain the same: ``PEEK``, ``POKE``, ``SYNC``,
	``SPEC``, and ``REST``
- the main documented architecture difference is the 32-bit parameter layout
	used for memory operations
- ARM/Thumb-specific trap, hook, or stepping behavior should be documented here
	rather than on the generic protocol page

You can see that distinction called out in the concrete-device protocol page,
which is where the shared transport model is described.

Backend Focus
-------------

As this section grows, it should collect the ARM/Thumb-specific details that do
not belong on the generic protocol page:

- backend overview for the older ARM and Thumb debugger implementations
- memory-operation packing specifics for 32-bit targets
- state-model and special-register behavior
- stepping, hook, or trap-entry differences relative to ARM64
- any target bring-up caveats that are specific to older ARM systems

Current Limitations
-------------------

This page is intentionally short for now.

- there is not yet an end-to-end ARM/Thumb walkthrough here
- the current docs mention ARM/Thumb mainly at the protocol-difference level
- backend-specific implementation notes still need to be pulled into this
	section over time