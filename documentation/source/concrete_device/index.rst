Concrete Device And Gupje
=========================

The concrete-device path is the second major workflow in the project. It is the
host-side counterpart to a Gupje stub running on a real target.

.. toctree::
   :hidden:
   :maxdepth: 2

   overview
   protocol_and_memory_model
   device_hook_files

Use this section when you already have code execution on a target and want to
turn that foothold into a reusable host-side debugger workflow.

The overview page explains the moving parts. The protocol page covers the wire
format and the storage-backed state model. The hook-file page shows how a real
target integration binds transport code and an architecture debugger backend
into ``ConcreteDevice``.