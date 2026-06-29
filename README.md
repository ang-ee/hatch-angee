# hatch-angee

The one published implementation of Angee's addon build machinery. An addon repo
sets `hatch_angee.build` as its build backend and carries **no `hatch_build.py`**,
**no hook tables**, and **no `dynamic`** of its own — the backend wires everything
in.

```toml
# an addon repo's pyproject.toml — no Python hook code, no hook tables
[build-system]
requires = ["hatch-angee>=0.1"]          # pulls hatchling transitively
build-backend = "hatch_angee.build"

[project]
name = "angee-addon-crm"
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

## Escape hatch: explicit hatchling hooks

The same two hooks are also registered by name, so a repo that prefers plain
hatchling can wire them itself instead of using the backend:

```toml
[build-system]
requires = ["hatchling", "hatch-angee>=0.1"]
build-backend = "hatchling.build"

[project]
dynamic = ["entry-points"]

[tool.hatch.metadata.hooks.angee-addons]
[tool.hatch.build.targets.wheel.hooks.angee-addon-sources]
```
