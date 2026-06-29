"""PEP 517 build backend = hatchling + Angee's hooks, auto-enabled.

Set ``build-backend = "hatch_angee.build"`` and an addon repo declares **nothing
but the backend** — no per-repo ``[tool.hatch.*.hooks.*]`` tables, no
``dynamic``. The backend wraps hatchling and, for the wheel/editable builds,
injects:

- the ``angee-addons`` metadata hook → generates the ``angee.addons`` entry
  points (so ``entry-points`` is declared dynamic too);
- the ``angee-addon-sources`` build hook → ships each addon's web/templates/skills.

Backend config lives in ``[tool.hatch-angee]`` (e.g. ``extra-web`` for a
framework's non-addon shared web libraries). The named hooks resolve through the
same plugin registration (``hatch_angee.plugin``), so this backend is the *default*
front door and ``hatchling`` + explicit hook tables stays the escape hatch.

Everything except the wheel/editable build is hatchling's own (re-exported).
"""

from __future__ import annotations

import os
from typing import Any

from hatchling.build import *  # noqa: F403 — re-export hatchling's PEP 517 surface
from hatchling.build import __all__  # noqa: F401

_BUILD_HOOK = "angee-addon-sources"
_METADATA_HOOK = "angee-addons"


def _enable(builder: Any) -> None:
    """Inject the Angee hooks into the builder's raw config before it builds.

    All three targets are plain dicts read lazily (``hook_config`` is a
    ``cached_property``, the metadata hooks materialise at build), so mutating them
    on a freshly constructed builder is equivalent to the repo having declared the
    tables itself.
    """

    options = builder.metadata.config.get("tool", {}).get("hatch-angee", {})
    builder.config.target_config.setdefault("hooks", {}).setdefault(_BUILD_HOOK, dict(options))

    dynamic = builder.metadata.core_raw_metadata.setdefault("dynamic", [])
    if "entry-points" not in dynamic:
        dynamic.append("entry-points")
    builder.metadata.hatch.metadata.config.setdefault("hooks", {}).setdefault(_METADATA_HOOK, {})


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    """Build a wheel with the Angee hooks enabled."""

    from hatchling.builders.wheel import WheelBuilder

    builder = WheelBuilder(os.getcwd())
    _enable(builder)
    return os.path.basename(next(builder.build(directory=wheel_directory, versions=["standard"])))


def build_editable(
    wheel_directory: str,
    config_settings: dict[str, Any] | None = None,
    metadata_directory: str | None = None,
) -> str:
    """Build an editable wheel (the source hook no-ops for editable installs)."""

    from hatchling.builders.wheel import WheelBuilder

    builder = WheelBuilder(os.getcwd())
    _enable(builder)
    return os.path.basename(next(builder.build(directory=wheel_directory, versions=["editable"])))
