# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## What this is

`hatch-angee` is a **published Hatchling plugin** — the single implementation of
Angee's addon build machinery. Angee addon repos add it to their build requires
so they carry **no `hatch_build.py`** of their own; they reference the hooks by
name (or use the bundled build backend) instead. It is consumed at build time by
addon repos **and in-process by Angee's host and explicit build tooling**, which
call the manifest/discovery/compile/project library.

## Commands

Standard Hatchling package with a pytest suite:

```bash
uv build          # or: python -m build / hatch build → dist/*.whl + *.tar.gz
uv run pytest     # unit tests plus end-to-end downstream wheel builds
```

To exercise the hooks, build a **downstream addon repo** that depends on this
package — the hooks only fire against a tree containing `addon.toml` markers.
The suite covers the library primitives and end-to-end builds against throwaway
downstream addon trees.

## Architecture

The package owns addon manifest parsing, discovery, dependency compilation, the
generated pyproject dependency block, and two Hatchling hooks.

**Discovery (`discovery.py:discover`)** — the shared primitive. Walks every
`addon.toml` under the given roots (pruning `node_modules`, `.venv`, `dist`,
etc.; **following directory symlinks** with a resolved-path cycle guard, since
stack layouts symlink checkouts into source trees) and yields
`(addon_dir, manifest)` pairs — roots in caller order (the precedence
contract), each root's markers sorted by relative path parts, physical
duplicates deduped to the first root. Both hooks discover addons this exact
way, so the package is **layout-agnostic**: single-addon, `src/` layout, or
multi-addon bundle all work with no config.

**Two hooks, both keyed off those markers:**

- `AddonEntryPointsHook` (metadata hook, name `angee-addons`) — generates the
  `angee.addons` entry points as `name -> name` (the import anchor is the addon
  name). Baked into `entry_points.txt`; the Angee runtime enumerates this group
  over `uv.lock` to list available addons. This is why depending repos declare
  `dynamic = ["entry-points"]`.

- `AddonSourcesBuildHook` (wheel build hook, name `angee-addon-sources`) — ships
  each addon's non-Python "seam" trees (`web/`, `templates/`, `skills/`) into the
  wheel at the addon's **import path** (`vendor.crm` → `vendor/crm/...`), so a
  downstream install resolves them with no separate npm publish.

**Two non-obvious rules in the build hook** (`hooks.py:AddonSourcesBuildHook`):

1. **Force-include only when a remap is needed.** If an addon's source path
   already equals its import path (normal flat/`src` layout), hatchling's default
   file walk already ships the seams correctly — force-including would collide, so
   the hook skips it. It force-includes *only* when source dir ≠ import path (e.g.
   a multi-root bundle shipping `addons/angee/iam` as `angee/iam`); such repos must
   exclude the source seam from the default walk. `_ship` pulls `src/`, `bin/`, and
   `package.json` from each seam.
2. **Editable builds no-op** — `version == "editable"` returns early, because the
   seams already resolve from the source roots on `sys.path`; copying them into
   site-packages would duplicate the namespace.

`addon-discovery` (hook config) names project-relative roots searched by both
hooks; omitted preserves whole-project discovery and an empty list disables it.
`extra-web` names glob roots of *non-addon* web packages
(framework-internal shared libs with no `addon.toml`) to ship verbatim. A normal
addon repo configures none.

## Two ways a downstream repo wires this in

1. **`hatchling` backend + named hook tables** (the explicit escape hatch):
   ```toml
   [build-system]
   requires = ["hatchling", "hatch-angee"]
   build-backend = "hatchling.build"

   [project]
   dynamic = ["entry-points"]
   [tool.hatch.metadata.hooks.angee-addons]
   [tool.hatch.build.targets.wheel.hooks.angee-addon-sources]
   ```
   The hooks resolve by name via `plugin.py`, registered through
   `[project.entry-points.hatch] angee = "hatch_angee.plugin"` in *this* repo's
   `pyproject.toml`.

2. **`hatch_angee.build` backend** (the default front door, `build.py`) — set
   `build-backend = "hatch_angee.build"` and the repo declares *nothing else*: no
   hook tables, no `dynamic`. The backend re-exports hatchling's full PEP 517
   surface and overrides only `build_wheel` / `build_editable`, where `_enable()`
   injects both hooks into the builder's raw config and appends `entry-points` to
   `dynamic` — equivalent to the repo having declared the tables itself. Backend
   config goes in `[tool.hatch-angee]` (e.g. `addon-discovery`, `extra-web`).

When changing hook behavior, keep the two wiring paths in sync: `build.py:_enable`
must inject the same hook names (`angee-addons`, `angee-addon-sources`) that
`plugin.py` registers and that depending repos reference by name.
