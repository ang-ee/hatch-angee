# hatch-angee

The one published implementation of Angee's addon machinery: the **build
backend** addon repos set as `build-backend`, and the **library** Angee's
composer calls in-process (manifest parsing, discovery, dependency
compilation, the generated pyproject block). An addon repo carries **no
`hatch_build.py`**, **no hook tables**, and **no `dynamic`** of its own — the
backend wires everything in.

```toml
# an addon repo's pyproject.toml — no Python hook code, no hook tables
[build-system]
requires = ["hatch-angee>=0.2"]          # pulls hatchling transitively
build-backend = "hatch_angee.build"

[project]
name = "vendor-crm"                      # the addon name, PEP 503-normalized (vendor.crm)
version = "0.1.0"
# no `dynamic = [...]` — the backend declares entry-points dynamic for you

[tool.hatch.build.targets.wheel]
packages = ["vendor"]                    # the import package(s) to ship
```

On a wheel/editable build the backend discovers every `addon.toml` in the repo
(pruning `node_modules`, `.venv`, `dist`, …) and:

- **generates** the `angee.addons` entry points (`name -> import anchor`) — the
  runtime enumerates these over `uv.lock` to list *available* addons;
- **ships** each addon's `web/`, `templates/`, `skills/` into the wheel at the
  addon's import path (`vendor.crm` → `vendor/crm/...`), layout-agnostic.

Backend config lives in `[tool.hatch-angee]` — e.g. `extra-web` names glob roots
of non-addon shared web packages (no `addon.toml`) to ship verbatim. A normal
addon repo configures none.

## The library face

Angee's composer imports the same package in-process during `angee build`:

- `parse_manifest(path)` → the validated `AddonManifest` (`addon.toml`
  vocabulary incl. `dependencies` — PEP 508 — and `requires`, the core
  compatibility floor);
- `discover(roots)` → `(addon_dir, manifest)` pairs, caller root order =
  precedence, symlink-following with a cycle guard;
- `compile_dependencies(manifests)` / `check_requires(manifests, core_version)`;
- `write_block(pyproject, deps)` → the generated `[dependency-groups].addons`
  key, comment-preserving, idempotent, atomically replaced.

The library face imports stdlib + `packaging` + `tomlkit` only — never
hatchling or Django (`tests/test_layering.py` enforces it).

## Escape hatch: explicit hatchling hooks

The same two hooks are also registered by name, so a repo that prefers plain
hatchling can wire them itself instead of using the backend:

```toml
[build-system]
requires = ["hatchling", "hatch-angee>=0.2"]
build-backend = "hatchling.build"

[project]
dynamic = ["entry-points"]

[tool.hatch.metadata.hooks.angee-addons]
[tool.hatch.build.targets.wheel.hooks.angee-addon-sources]
```
