"""End-to-end: the ``hatch_angee.build`` backend builds a real addon wheel.

Drives a throwaway bundle repo (source path != import path, so the build hook
actively force-includes) through ``build_wheel`` and inspects the wheel: seams
land at the import path and the ``angee.addons`` entry points are baked in.
"""

from __future__ import annotations

import zipfile

from hatch_angee.build import build_wheel


def _bundle(root, write_file) -> None:
    write_file(
        root / "pyproject.toml",
        """
        [build-system]
        requires = ["hatchling", "hatch-angee"]
        build-backend = "hatch_angee.build"

        [project]
        name = "angee-bundle"
        version = "0.1.0"

        [tool.hatch.build.targets.wheel]
        sources = ["src"]
        only-include = ["src/angee"]
        """,
    )
    write_file(root / "src" / "angee" / "__init__.py")
    write_file(root / "src" / "angee" / "iam" / "__init__.py")
    addon = root / "addons" / "angee" / "iam"
    write_file(addon / "addon.toml", '[addon]\nname = "angee.iam"\n')
    write_file(addon / "web" / "src" / "index.js", "// iam web")
    write_file(addon / "web" / "package.json", '{"name": "@angee/iam"}')


def test_build_wheel_ships_seams_and_generates_entry_points(tmp_path, monkeypatch, write_file):
    root = tmp_path / "bundle"
    _bundle(root, write_file)
    out = tmp_path / "out"
    out.mkdir()

    monkeypatch.chdir(root)
    wheel = out / build_wheel(str(out))

    with zipfile.ZipFile(wheel) as zf:
        names = set(zf.namelist())
        ep_name = next(n for n in names if n.endswith("entry_points.txt"))
        entry_points = zf.read(ep_name).decode()

    # The Python package ships via the default walk...
    assert "angee/__init__.py" in names
    # ...and the seam ships, remapped from addons/angee/iam to the import path.
    assert "angee/iam/web/src/index.js" in names
    assert "angee/iam/web/package.json" in names
    # The metadata hook baked the generated entry points into the wheel.
    assert "[angee.addons]" in entry_points
    assert "angee.iam = angee.iam" in entry_points


def test_readme_flat_layout_example_builds(tmp_path, monkeypatch, write_file):
    # Mirrors the README's primary example: the backend, a co-located addon.toml,
    # and only `packages = [...]` — no hook tables, no `dynamic`. Here source path
    # == import path, so the build hook defers to hatchling's default walk.
    root = tmp_path / "crm"
    write_file(
        root / "pyproject.toml",
        """
        [build-system]
        requires = ["hatch-angee>=0.1"]
        build-backend = "hatch_angee.build"

        [project]
        name = "angee-addon-crm"
        version = "0.1.0"

        [tool.hatch.build.targets.wheel]
        packages = ["vendor"]
        """,
    )
    write_file(root / "vendor" / "__init__.py")
    addon = root / "vendor" / "crm"
    write_file(addon / "__init__.py")
    write_file(addon / "addon.toml", '[addon]\nname = "vendor.crm"\n')
    write_file(addon / "web" / "src" / "index.js", "// crm web")
    write_file(addon / "web" / "package.json", '{"name": "@vendor/crm"}')
    out = tmp_path / "out"
    out.mkdir()

    monkeypatch.chdir(root)
    wheel = out / build_wheel(str(out))

    with zipfile.ZipFile(wheel) as zf:
        names = set(zf.namelist())
        ep_name = next(n for n in names if n.endswith("entry_points.txt"))
        entry_points = zf.read(ep_name).decode()

    assert "vendor/crm/web/src/index.js" in names
    assert "vendor/crm/web/package.json" in names
    assert "[angee.addons]" in entry_points
    assert "vendor.crm = vendor.crm" in entry_points
