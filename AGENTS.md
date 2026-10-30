# hatch-angee

This published PEP 517 backend supplies layout and metadata defaults over native
Hatchling for one in-place addon distribution. One `angee.addons` entry-point key
owns layout. Explicit entry points remain authored; `dynamic = ["entry-points"]`
opts into the native metadata hook described in README.md. Authored project files
are never rewritten. Native Hatchling configuration overrides defaults, including
the default `allow-direct-references = true`. Hatchling is the only dependency.

Do not add runtime APIs, manifest parsing, discovery or compilers. The metadata
hook owns only the opted-in addon entry point. Standard `project.keywords` carries
marketplace tags unchanged; capability facts stay with their addons. Never read
`tool.angee`, compute requirements or inherit metadata from a workspace parent.

Use `make check` for lint, strict type checking and tests; use `uv build` for archives.
Changes to the backend must cover wheel, editable, sdist and metadata entrypoints.
Keep builds deterministic and preserve authored PEP 621 metadata.
