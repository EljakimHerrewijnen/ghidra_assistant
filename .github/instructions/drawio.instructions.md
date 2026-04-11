---
description: "Use when creating or editing draw.io diagrams so the XML is structurally valid, opens reliably, and fits technical documentation for ghidra_assistant."
applyTo: "**/*.drawio"
---

# Draw.io Generation Rules

Generate raw `.drawio` XML only. Do not wrap the output in Markdown fences and do not add explanation text before or after the XML.

## Mandatory Structure

Every generated file must:

1. Start with exactly:

   `<?xml version="1.0" encoding="UTF-8"?>`

2. Use the mxGraph hierarchy:

   `mxfile -> diagram -> mxGraphModel -> root -> mxCell`

3. Include both required root cells:

   `<mxCell id="0"/>`
   `<mxCell id="1" parent="0"/>`

4. Use infinite canvas for documentation diagrams:

   `<mxGraphModel dx="1422" dy="762" grid="1" gridSize="10" page="0">`

## Cell Rules

- Use sequential numeric IDs starting at `2`.
- Create all vertices before creating any edges.
- Every top-level visible cell must use `parent="1"` unless it is inside a group or swimlane.
- Every vertex must include `vertex="1"`.
- Every edge must include `edge="1"`, `source`, and `target`.
- Every `<mxGeometry>` must include `as="geometry"`.
- Edge geometry should use `relative="1"`.

## XML Safety Rules

- Output only valid XML.
- Never use literal `\n` inside `value` attributes.
- Do not place physical newlines inside `value="..."` attributes.
- Avoid raw `&`, `<`, and `>` in labels.
- Do not quote colour values inside `style`; use `fillColor=#0078D4`, not `fillColor="#0078D4"`.

## Preferred Styles

Use simple shapes that render well in technical docs:

- Process or component: `rounded=0;whiteSpace=wrap;html=1;`
- Entry or exit: `rounded=1;whiteSpace=wrap;html=1;`
- Decision: `rhombus;whiteSpace=wrap;html=1;`
- Database or state store: `shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;`
- Container or subsystem: `swimlane;whiteSpace=wrap;html=1;`

## Documentation Context

For this repository, diagrams will usually describe one of these:

- Ghidra integration flows
- Assistant request and response paths
- Emulator backend architecture
- Debugger architecture by ISA
- Processor state or stepping flows
- Documentation navigation or setup workflows

Prefer labels and structures that match the codebase vocabulary:

- `Ghidra Assistant`
- `Concrete Device`
- `Ghidra Backend`
- `MCP Backend`
- `Emulator Backend`
- `Debugger Backend`
- `RISC-V Stepper`
- `ARM64 Emulator`

## Layout Guidance

- Use top-to-bottom flow for processes and setup guides.
- Use left-to-right flow for backend pipelines.
- Use swimlanes or grouped containers for subsystem boundaries.
- Keep diagrams readable in static documentation pages; avoid overly dense layouts.

## Final Checklist

Before outputting the file, verify that:

- The first line is the XML declaration.
- `page="0"` is used.
- Root cells `0` and `1` exist.
- IDs are unique and sequential.
- All edges reference existing vertices.
- All geometry tags include `as="geometry"`.
- The output is raw XML only.