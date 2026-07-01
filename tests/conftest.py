"""Shared fixtures: builders for throwaway addon trees under ``tmp_path``."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest


def _write(path: Path, content: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content))
    return path


@pytest.fixture
def write_file():
    """Write ``content`` to ``path`` (creating parents); dedents for readability."""

    return _write


@pytest.fixture
def make_addon(write_file):
    """Create an ``addon.toml`` plus its seam trees, returning the addon dir.

    ``seams`` controls which of web/templates/skills are populated; each gets a
    ``src/`` dir, optionally a ``bin/`` dir and a ``package.json`` — the exact
    shapes ``AddonSourcesBuildHook._ship`` looks for.
    """

    def _make(
        addon_dir: Path,
        name: str,
        *,
        seams=("web", "templates", "skills"),
        with_src=True,
        with_bin=False,
        with_config=False,
        with_manifest=True,
    ) -> Path:
        write_file(addon_dir / "addon.toml", f'[addon]\nname = "{name}"\n')
        for seam in seams:
            if with_src:
                write_file(addon_dir / seam / "src" / "index.js", "// entry")
            if with_bin:
                write_file(addon_dir / seam / "bin" / "tool.js", "// bin")
            if with_config:
                write_file(addon_dir / seam / "config" / "vite.ts", "// config")
            if with_manifest:
                write_file(addon_dir / seam / "package.json", '{"name": "seam"}')
        return addon_dir

    return _make
