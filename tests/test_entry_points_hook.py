"""``AddonEntryPointsHook`` — generates the ``angee.addons`` entry points."""

from __future__ import annotations

from hatch_angee.hooks import ENTRY_POINT_GROUP, AddonEntryPointsHook


def test_generates_sorted_name_to_name_mapping(tmp_path, make_addon):
    make_addon(tmp_path / "iam", "vendor.iam")
    make_addon(tmp_path / "crm", "vendor.crm")

    metadata: dict = {}
    AddonEntryPointsHook(root=str(tmp_path), config={}).update(metadata)

    group = metadata["entry-points"][ENTRY_POINT_GROUP]
    assert group == {"vendor.crm": "vendor.crm", "vendor.iam": "vendor.iam"}
    assert list(group) == ["vendor.crm", "vendor.iam"]  # sorted insertion order


def test_preserves_pre_existing_entry_point_groups(tmp_path, make_addon):
    make_addon(tmp_path / "crm", "vendor.crm")

    metadata: dict = {"entry-points": {"console_scripts": {"foo": "pkg:main"}}}
    AddonEntryPointsHook(root=str(tmp_path), config={}).update(metadata)

    assert metadata["entry-points"]["console_scripts"] == {"foo": "pkg:main"}
    assert ENTRY_POINT_GROUP in metadata["entry-points"]


def test_empty_group_when_no_addons(tmp_path):
    metadata: dict = {}
    AddonEntryPointsHook(root=str(tmp_path), config={}).update(metadata)

    assert metadata["entry-points"][ENTRY_POINT_GROUP] == {}


def test_discovery_config_limits_entry_points(tmp_path, make_addon):
    make_addon(tmp_path / "addons" / "crm", "vendor.crm")
    make_addon(tmp_path / "examples" / "notes", "example.notes")

    metadata: dict = {}
    AddonEntryPointsHook(
        root=str(tmp_path), config={"addon-discovery": ["addons"]}
    ).update(metadata)

    assert metadata["entry-points"][ENTRY_POINT_GROUP] == {"vendor.crm": "vendor.crm"}
