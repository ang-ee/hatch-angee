"""Register the Angee hooks with hatchling so any addon repo can use them by name."""

from __future__ import annotations

from hatchling.plugin import hookimpl

from hatch_angee.hooks import AddonEntryPointsHook, AddonSourcesBuildHook


@hookimpl
def hatch_register_metadata_hook() -> type[AddonEntryPointsHook]:
    """Expose the ``angee-addons`` metadata hook (generates entry points)."""

    return AddonEntryPointsHook


@hookimpl
def hatch_register_build_hook() -> type[AddonSourcesBuildHook]:
    """Expose the ``angee-addon-sources`` wheel build hook (ships web/templates/skills)."""

    return AddonSourcesBuildHook
