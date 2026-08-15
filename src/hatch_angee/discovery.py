"""Filesystem discovery for addon directories marked by ``addon.toml``."""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from hatch_angee.manifest import AddonManifest, ManifestError, parse_manifest

# Addon source never lives in dependency/build/cache/venv trees or dot-directories.
# Pruning applies below each root, so a dot-directory above a root is harmless.
_PRUNE = {"node_modules", "venv", "dist", "build", "site-packages"}


def _coerce_roots(roots: Iterable[Path | str] | Path | str) -> tuple[Path, ...]:
    if isinstance(roots, (Path, str)):
        return (Path(roots),)
    return tuple(Path(root) for root in roots)


def _iter_markers(root: Path) -> list[Path]:
    """Return the root's ``addon.toml`` markers sorted by relative path parts.

    Directory symlinks are followed — stack layouts symlink checkouts into
    source trees — with a visited set of resolved directories guarding cycles.
    """

    markers: list[Path] = []
    visited: set[Path] = set()
    for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
        current = Path(dirpath)
        resolved = current.resolve()
        if resolved in visited:
            dirnames[:] = []
            continue
        visited.add(resolved)
        dirnames[:] = [name for name in dirnames if name not in _PRUNE and not name.startswith(".")]
        if "addon.toml" in filenames:
            markers.append(current / "addon.toml")
    markers.sort(key=lambda marker: marker.relative_to(root).parts)
    return markers


def discover(
    roots: Iterable[Path | str] | Path | str,
) -> list[tuple[Path, AddonManifest]]:
    """Return ``(addon_dir, manifest)`` pairs in caller precedence order.

    Roots are traversed in caller order — the precedence contract — and each
    root's markers sort by relative path parts, the original hooks' order. A
    physical addon reachable from two roots (or through a symlink alias) is
    yielded once, for the first root that finds it. A marker without an
    ``[addon]`` table or ``name`` remains an ignored non-addon for parity with
    the original build hooks; every other schema error fails fast.
    """

    seen: set[Path] = set()
    discovered: list[tuple[Path, AddonManifest]] = []
    for root in _coerce_roots(roots):
        for marker in _iter_markers(root):
            resolved = marker.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            try:
                manifest = parse_manifest(marker)
            except ManifestError as error:
                if error.code == "not-an-addon":
                    continue
                raise
            discovered.append((marker.parent, manifest))
    return discovered
