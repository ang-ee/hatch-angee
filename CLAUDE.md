# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`hatch-angee` is a **published Hatchling plugin** — the single implementation of
Angee's addon build machinery. Angee addon repos add it to their build requires
so they carry **no `hatch_build.py`** of their own; they reference the hooks by
name (or use the bundled build backend) instead. It is a build-*time* dependency,
not a runtime library.

## Commands

Standard Hatchling package, no test suite or lint config in the repo:

```bash
uv build          # or: python -m build / hatch build → dist/*.whl + *.tar.gz
```

To exercise the hooks, build a **downstream addon repo** that depends on this
package — the hooks only fire against a tree containing `addon.toml` markers.
There is no unit test harness here; verification is end-to-end via a real build.

## Architecture

Four files under `src/hatch_angee/`. The whole package is two hooks plus two ways
to wire them in.

**Discovery (`hooks.py:iter_addons`)** — the shared primitive. `rglob`s every
`addon.toml` under the project root (pruning `node_modules`, `.venv`, `dist`,
etc.), reads `[addon].name`, and yields `(name, addon_dir)` sorted for build
determinism. Both hooks discover addons this exact way, so the package is
**layout-agnostic**: single-addon, `src/` layout, or multi-addon bundle all work
with no config.

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

`extra-web` (hook config) names glob roots of *non-addon* web packages
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
   config goes in `[tool.hatch-angee]` (e.g. `extra-web`).

When changing hook behavior, keep the two wiring paths in sync: `build.py:_enable`
must inject the same hook names (`angee-addons`, `angee-addon-sources`) that
`plugin.py` registers and that depending repos reference by name.
