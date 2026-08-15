"""The public discovery API shared by build hooks and future composers."""

from __future__ import annotations

from hatch_angee.discovery import discover


def test_returns_addon_directory_and_parsed_manifest_sorted_by_marker(tmp_path, make_addon):
    second = make_addon(
        tmp_path / "z-source" / "addons" / "vendor" / "iam",
        "vendor.iam",
        manifest="""
        [addon]
        name = "vendor.iam"
        dependencies = ["django-axes>=7"]
        """,
    )
    first = make_addon(tmp_path / "a-source" / "vendor" / "crm", "vendor.crm")

    found = discover([tmp_path])

    assert [(addon_dir, manifest.name) for addon_dir, manifest in found] == [
        (first, "vendor.crm"),
        (second, "vendor.iam"),
    ]
    assert found[1][1].dependencies == ("django-axes>=7",)


def test_prunes_build_dependency_and_dot_directories(tmp_path, make_addon):
    make_addon(tmp_path / "valid", "vendor.crm")
    pruned = (
        "node_modules",
        "venv",
        "dist",
        "build",
        "site-packages",
        ".venv",
        ".git",
        ".angee",
    )
    for index, parent in enumerate(pruned):
        make_addon(tmp_path / parent / "nested", f"pruned.{index}")

    assert [manifest.name for _, manifest in discover([tmp_path])] == ["vendor.crm"]


def test_roots_precede_in_caller_order(tmp_path, make_addon):
    crm = make_addon(tmp_path / "source-b" / "addons" / "vendor" / "crm", "vendor.crm")
    iam = make_addon(tmp_path / "source-a" / "src" / "vendor" / "iam", "vendor.iam")

    found = discover([tmp_path / "source-b", tmp_path / "source-a"])

    assert [(directory, manifest.name) for directory, manifest in found] == [
        (crm, "vendor.crm"),
        (iam, "vendor.iam"),
    ]


def test_follows_directory_symlinks_into_checkouts(tmp_path, make_addon):
    checkout = tmp_path / "real-checkout"
    make_addon(checkout / "addons" / "vendor" / "crm", "vendor.crm")
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "linked").symlink_to(checkout, target_is_directory=True)

    assert [manifest.name for _, manifest in discover([sources])] == ["vendor.crm"]


def test_symlink_alias_roots_dedupe_to_the_first_root(tmp_path, make_addon):
    real = tmp_path / "real"
    addon_dir = make_addon(real / "vendor" / "crm", "vendor.crm")
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)

    found = discover([real, alias])

    assert [(directory, manifest.name) for directory, manifest in found] == [
        (addon_dir, "vendor.crm"),
    ]


def test_symlink_cycles_terminate(tmp_path, make_addon):
    make_addon(tmp_path / "vendor" / "crm", "vendor.crm")
    (tmp_path / "loop").symlink_to(tmp_path, target_is_directory=True)

    assert [manifest.name for _, manifest in discover([tmp_path])] == ["vendor.crm"]
