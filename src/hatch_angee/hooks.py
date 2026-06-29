"""Hatchling hooks shared by every Angee addon repo — published once in
``hatch-angee`` so no repo carries its own ``hatch_build.py``.

Two hooks, both driven by the co-located ``addon.toml`` markers:

- :class:`AddonEntryPointsHook` (metadata) generates the ``angee.addons`` entry
  points from the markers (the AutoService pattern) → baked into
  ``entry_points.txt``, enumerated at runtime over ``uv.lock``.
- :class:`AddonSourcesBuildHook` (wheel build) ships each addon's non-Python
  contribution trees (``web/``, ``templates/``, ``skills/``) into the wheel at the
  addon's import path, so a downstream project resolves them straight from its
  install — one distribution channel, no separate npm publish.

Both discover addons the same way: every ``addon.toml`` under the project, minus
``node_modules`` and the usual build/venv dirs. The wheel target for an addon is
derived from its declared ``name`` (``vendor.crm`` → ``vendor/crm``), so the hooks
are layout-agnostic: a single-addon repo, a ``src/`` layout, or a multi-addon
bundle all work without configuration.
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.metadata.plugin.interface import MetadataHookInterface

ENTRY_POINT_GROUP = "angee.addons"
# Never descend into dependency/build/cache/venv trees: addon source never lives in a
# dot-directory (`.angee` — which holds the in-repo uv cache + dev worktrees — `.venv`,
# `.git`, `.tox`, …) or a build-output dir. Checked on the path *relative to root* so a
# dot in a parent of the project doesn't prune everything.
_PRUNE = {"node_modules", "venv", "dist", "build", "site-packages"}
_SEAMS = ("web", "templates", "skills")


def _pruned(parts: tuple[str, ...]) -> bool:
    """Return whether any path component is a build/cache dir or a dot-directory."""

    return any(part in _PRUNE or part.startswith(".") for part in parts)


def iter_addons(root: Path) -> Iterator[tuple[str, Path]]:
    """Yield ``(name, addon_dir)`` for every ``addon.toml`` under ``root``.

    Sorted for build determinism; pruned of dependency/build/cache/venv trees.
    """

    markers = (
        m
        for m in root.rglob("addon.toml")
        if not _pruned(m.relative_to(root).parts)
    )
    for marker in sorted(markers):
        name = tomllib.loads(marker.read_text()).get("addon", {}).get("name")
        if name:
            yield name, marker.parent


class AddonEntryPointsHook(MetadataHookInterface):
    """Generate the ``angee.addons`` entry points from the ``addon.toml`` markers."""

    PLUGIN_NAME = "angee-addons"

    def update(self, metadata: dict[str, Any]) -> None:
        """Set the ``angee.addons`` group: ``name -> import anchor`` per addon."""

        addons = {name: name for name, _dir in iter_addons(Path(self.root))}
        metadata.setdefault("entry-points", {})[ENTRY_POINT_GROUP] = dict(sorted(addons.items()))


class AddonSourcesBuildHook(BuildHookInterface[Any]):
    """Force-include each addon's web/templates/skills trees into the wheel.

    Hatchling's default file walk drops some source trees inconsistently, so each
    seam is force-included explicitly under the addon's import path. ``node_modules``
    never lives under a seam dir, so the install tree is naturally excluded.
    """

    PLUGIN_NAME = "angee-addon-sources"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        """Map every addon seam (and any configured extra web root) into the wheel.

        When an addon's source path already equals its import path (the normal
        flat/``src`` layout), hatchling's default walk ships the seam at the right
        place — force-including it too would collide. So we only force-include when a
        **remap** is needed, i.e. the source dir differs from the import path (e.g.
        a multi-root bundle whose ``addons/angee/iam`` ships as ``angee/iam``); such
        a repo excludes the source seam from the default walk.

        ``extra-web`` (hook config) names glob roots of *non-addon* web packages —
        framework-internal shared libraries with no ``addon.toml`` — shipped verbatim
        at their own path. A normal addon repo configures none.
        """

        if version == "editable":
            # An editable install resolves the seams from the source roots on the
            # path; copying them into site-packages would duplicate the namespace.
            return
        root = Path(self.root)
        force_include: dict[str, str] = build_data.setdefault("force_include", {})
        for name, addon_dir in iter_addons(root):
            target = name.replace(".", "/")
            if addon_dir.relative_to(root).as_posix() == target:
                continue  # source path == import path → default walk handles the seams
            for seam in _SEAMS:
                self._ship(force_include, addon_dir / seam, f"{target}/{seam}")
        for pattern in self.config.get("extra-web", []):
            for package in sorted(root.glob(pattern)):
                self._ship(force_include, package, package.relative_to(root).as_posix())

    @staticmethod
    def _ship(force_include: dict[str, str], source: Path, target: str) -> None:
        """Force-include ``source``'s ``src``/``bin``/``package.json`` under ``target``."""

        if not source.is_dir():
            return
        for child in ("src", "bin"):
            sub = source / child
            if sub.is_dir():
                force_include[str(sub)] = f"{target}/{child}"
        manifest = source / "package.json"
        if manifest.is_file():
            force_include[str(manifest)] = f"{target}/package.json"
