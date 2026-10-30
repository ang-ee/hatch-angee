# hatch-angee

A small PEP 517 backend for one in-place Angee addon per distribution. Hatchling
owns metadata and archives; this backend supplies package layout, direct-reference
defaults and an opt-in addon entry point through Hatchling's native metadata hook.

```toml
build-system = { requires = ["hatch-angee>=1.1,<2"], build-backend = "hatch_angee" }

[project]
name = "acme-notes"
version = "1.0.0"
keywords = ["notes", "productivity"]
dynamic = ["entry-points"]
```

Put this file inside `addons/acme/notes/`, alongside its Python package content.
The hook generates `acme.notes = "acme.notes"` in the `angee.addons` group. It
normalizes the distribution name, uses its first hyphen to separate the namespace,
and turns remaining hyphens into underscores: `acme-integrate-notes` becomes
`acme.integrate_notes`. This rule uses no parent checkout and also works from an
unpacked sdist. A missing namespace or a mismatched package directory is an error.

Use an explicit entry point instead of `dynamic = ["entry-points"]` for a different
package layout, an explicit Django AppConfig or additional entry-point groups:

```toml
[project.entry-points."angee.addons"]
"acme.notes" = "acme.notes.apps.NotesConfig"
```

The backend remaps files into `acme/notes/`, includes package data, and points an
editable install at the namespace root. Explicit `tool.hatch.build` settings win.
Keep repository ignore rules at its root; nested ignore files can shadow them.

Direct-reference dependencies are allowed by default. Set
`tool.hatch.metadata.allow-direct-references = false` to require Hatchling to
reject them. Requirements, versions, licenses and keywords remain authored native
metadata; the backend does not infer them or read `tool.angee`. Marketplace tags
use `project.keywords` and reach the wheel's standard `Keywords` metadata without
a category adapter. The authored `pyproject.toml` is preserved in every archive.

Installed consumers discover the addon through `importlib.metadata`. Catalogues
that also inspect source or packaged `pyproject.toml` must support the dynamic
declaration before migrating their addons; an omitted static entry-point table
does not mean that a built distribution has no addon entry point.

Build with `uv build --wheel`, or build a wheel from the self-contained sdist.
Run `uv run --extra dev pytest` for backend and distribution contracts.
