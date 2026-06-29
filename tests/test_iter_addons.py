"""``iter_addons`` — the discovery primitive both hooks build on."""

from __future__ import annotations

from hatch_angee.hooks import iter_addons


def test_discovers_and_sorts_by_marker_path(tmp_path, make_addon):
    # Created out of order; iter_addons sorts by marker path for build determinism.
    make_addon(tmp_path / "b_pkg", "vendor.iam")
    make_addon(tmp_path / "a_pkg", "vendor.crm")

    found = list(iter_addons(tmp_path))

    assert [name for name, _ in found] == ["vendor.crm", "vendor.iam"]
    assert found[0][1] == tmp_path / "a_pkg"


def test_prunes_dependency_and_build_dirs(tmp_path, make_addon):
    make_addon(tmp_path / "pkg", "vendor.crm")
    for pruned in ("node_modules", ".venv", "venv", "dist", "build", "__pycache__"):
        make_addon(tmp_path / pruned / "nested", f"vendor.{pruned.strip('._')}")

    assert [name for name, _ in iter_addons(tmp_path)] == ["vendor.crm"]


def test_skips_markers_without_an_addon_name(tmp_path, write_file):
    write_file(tmp_path / "no_name" / "addon.toml", "[addon]\n")  # table, no name
    write_file(tmp_path / "wrong_table" / "addon.toml", '[other]\nname = "x"\n')

    assert list(iter_addons(tmp_path)) == []


def test_empty_tree_yields_nothing(tmp_path):
    assert list(iter_addons(tmp_path)) == []
