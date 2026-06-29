# hatch-angee

The one published implementation of Angee's addon build machinery. Add it to an
addon repo's build requires and reference the hooks by name — the repo carries
**no `hatch_build.py`** of its own.

```toml
# an addon repo's pyproject.toml — no Python hook code
[build-system]
requires = ["hatchling", "hatch-angee"]
build-backend = "hatchling.build"

[project]
name = "angee-addon-crm"
version = "0.1.0"
dynamic = ["entry-points"]                       # generated from addon.toml

[tool.hatch.metadata.hooks.angee-addons]         # → angee.addons entry points
[tool.hatch.build.targets.wheel.hooks.angee-addon-sources]   # → ship web/templates/skills
```

The hooks discover every `addon.toml` in the repo and:

- **generate** the `angee.addons` entry points (`name -> import anchor`) — the
  runtime enumerates these over `uv.lock` to list *available* addons;
- **ship** each addon's `web/`, `templates/`, `skills/` into the wheel at the
  addon's import path (`vendor.crm` → `vendor/crm/...`), layout-agnostic.
