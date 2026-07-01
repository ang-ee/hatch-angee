"""``AddonSourcesBuildHook`` — force-includes seam trees into the wheel.

The two non-obvious rules under test: (1) force-include only when the source path
differs from the import path (a remap), and (2) editable builds no-op.
"""

from __future__ import annotations

from pathlib import Path

from hatch_angee.hooks import AddonSourcesBuildHook


def _hook(root: Path, config: dict | None = None) -> AddonSourcesBuildHook:
    return AddonSourcesBuildHook(
        root=str(root),
        config=config or {},
        build_config=None,
        metadata=None,
        directory=str(root),
        target_name="wheel",
    )


def test_editable_build_is_a_noop(tmp_path, make_addon):
    make_addon(tmp_path / "addons" / "angee" / "iam", "angee.iam")

    build_data: dict = {}
    _hook(tmp_path).initialize("editable", build_data)

    assert build_data.get("force_include", {}) == {}


def test_remap_layout_ships_each_seam_at_the_import_path(tmp_path, make_addon):
    # Source dir (addons/angee/iam) differs from import path (angee/iam) -> remap.
    addon = make_addon(
        tmp_path / "addons" / "angee" / "iam", "angee.iam", with_bin=True, with_config=True
    )

    build_data: dict = {}
    _hook(tmp_path).initialize("standard", build_data)
    fi = build_data["force_include"]

    assert fi[str(addon / "web" / "src")] == "angee/iam/web/src"
    assert fi[str(addon / "web" / "bin")] == "angee/iam/web/bin"
    assert fi[str(addon / "web" / "config")] == "angee/iam/web/config"
    assert fi[str(addon / "web" / "package.json")] == "angee/iam/web/package.json"
    assert fi[str(addon / "templates" / "src")] == "angee/iam/templates/src"
    assert fi[str(addon / "skills" / "src")] == "angee/iam/skills/src"


def test_flat_layout_defers_to_the_default_walk(tmp_path, make_addon):
    # Addon name == top-level dir -> source path == import path -> no force-include.
    make_addon(tmp_path / "crm", "crm")

    build_data: dict = {}
    _hook(tmp_path).initialize("standard", build_data)

    assert build_data.get("force_include", {}) == {}


def test_absent_seams_are_skipped(tmp_path, make_addon):
    addon = make_addon(tmp_path / "addons" / "angee" / "iam", "angee.iam", seams=("web",))

    build_data: dict = {}
    _hook(tmp_path).initialize("standard", build_data)
    fi = build_data["force_include"]

    assert fi[str(addon / "web" / "src")] == "angee/iam/web/src"
    assert all("templates" not in target for target in fi.values())
    assert all("skills" not in target for target in fi.values())


def test_extra_web_ships_non_addon_packages_verbatim(tmp_path, write_file):
    # extra-web is how the framework ships its non-addon web libraries (e.g.
    # `angee/web/*`); @angee/app carries a `config/` build-config seam consumed
    # downstream by package name, so it must ship alongside src/package.json.
    write_file(tmp_path / "libs" / "shared" / "src" / "util.js", "// util")
    write_file(tmp_path / "libs" / "shared" / "config" / "vite.ts", "// config")
    write_file(tmp_path / "libs" / "shared" / "package.json", '{"name": "shared"}')

    build_data: dict = {}
    _hook(tmp_path, {"extra-web": ["libs/*"]}).initialize("standard", build_data)
    fi = build_data["force_include"]

    assert fi[str(tmp_path / "libs" / "shared" / "src")] == "libs/shared/src"
    assert fi[str(tmp_path / "libs" / "shared" / "config")] == "libs/shared/config"
    assert fi[str(tmp_path / "libs" / "shared" / "package.json")] == "libs/shared/package.json"
