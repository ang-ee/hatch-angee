"""The addon manifest schema, including dependency and seam pass-through data."""

from __future__ import annotations

import pytest

from hatch_angee import parse_manifest_content
from hatch_angee.manifest import AddonManifest, ManifestError, parse_manifest


def test_parses_full_vocabulary_and_passes_through_seams(tmp_path, write_file):
    marker = write_file(
        tmp_path / "crm" / "addon.toml",
        """
        [addon]
        name = "vendor.crm"
        description = "Customer records"
        keywords = ["crm", "customers"]
        category = "Data"
        license = "MIT"
        readme = "README.md"
        version = "1.2.3"
        authors = [{ name = "Angee", email = "hi@angee.ai" }]
        urls = { Homepage = "https://example.test/crm" }
        depends_on = ["vendor.iam"]
        dependencies = ["httpx>=0.28", "redis[hiredis]>=5; python_version >= '3.11'"]
        requires = "angee-django>=0.3,<0.4"
        schemas = "schema.schemas"
        permissions = "permissions.zed"

        [web]
        package = "@vendor/crm"
        future = { nested = [1, 2] }

        [mcp]
        tools = "mcp_tools.register"
        future = true

        [resources]
        demo = [{ path = "resources/demo/customer.yaml", adopt = "name" }]

        [[migrations]]
        name = "customer_status"
        app_label = "crm"
        module = "runtime_migrations.customer_status"
        future = { enabled = true }
        """,
    )

    manifest = parse_manifest(marker)

    assert manifest.name == "vendor.crm"
    assert manifest.description == "Customer records"
    assert manifest.keywords == ("crm", "customers")
    assert manifest.category == "Data"
    assert manifest.license == "MIT"
    assert manifest.readme == "README.md"
    assert manifest.version == "1.2.3"
    assert manifest.authors == ({"name": "Angee", "email": "hi@angee.ai"},)
    assert manifest.urls == {"Homepage": "https://example.test/crm"}
    assert manifest.depends_on == ("vendor.iam",)
    assert manifest.dependencies == (
        "httpx>=0.28",
        "redis[hiredis]>=5; python_version >= '3.11'",
    )
    assert manifest.requires == "angee-django>=0.3,<0.4"
    assert manifest.schemas == "schema.schemas"
    assert manifest.permissions == "permissions.zed"
    assert manifest.web["future"] == {"nested": [1, 2]}
    assert manifest.mcp == {"tools": "mcp_tools.register", "future": True}
    assert manifest.resources["demo"][0]["adopt"] == "name"
    assert manifest.migrations[0]["future"] == {"enabled": True}


def test_defaults_optional_vocabulary(tmp_path, write_file):
    marker = write_file(tmp_path / "addon.toml", '[addon]\nname = "vendor.crm"\n')

    manifest = parse_manifest(marker)

    assert manifest.description == ""
    assert manifest.keywords == ()
    assert manifest.depends_on == ()
    assert manifest.dependencies == ()
    assert manifest.requires is None
    assert manifest.web == {}
    assert manifest.mcp == {}
    assert manifest.resources == {}
    assert manifest.migrations == ()


@pytest.mark.parametrize(
    ("body", "key"),
    [
        ("[addon]\ndescription = 'missing name'\n", "addon.name"),
        ("[addon]\nname = 'x'\ndependencies = 'httpx'\n", "addon.dependencies"),
        (
            "[addon]\nname = 'x'\ndependencies = ['not a ??? requirement']\n",
            "addon.dependencies[0]",
        ),
        ("[addon]\nname = 'x'\nrequires = 'not a ??? requirement'\n", "addon.requires"),
        ("[addon]\nname = 'x'\nrequires = 'some-framework>=1'\n", "addon.requires"),
        ("[addon]\nname = 'x'\nkeywords = ['ok', 2]\n", "addon.keywords[1]"),
        ("resources = 2\n[addon]\nname = 'x'\n", "resources"),
    ],
)
def test_validation_failures_name_file_and_key(tmp_path, write_file, body, key):
    marker = write_file(tmp_path / "broken" / "addon.toml", body)

    with pytest.raises(ManifestError) as caught:
        parse_manifest(marker)

    assert str(marker) in str(caught.value)
    assert key in str(caught.value)


@pytest.mark.parametrize(
    ("requires", "fragment"),
    [
        ("angee-django @ file:///tmp/core", "direct URL"),
        ("angee-django[postgres]>=0.3", "extras"),
        ("angee-django>=0.3; python_version >= '3.10'", "environment marker"),
    ],
)
def test_requires_is_a_pure_version_specifier(tmp_path, write_file, requires, fragment):
    marker = write_file(
        tmp_path / "addon.toml", f'[addon]\nname = "x"\nrequires = "{requires}"\n'
    )

    with pytest.raises(ManifestError) as caught:
        parse_manifest(marker)

    assert "addon.requires" in str(caught.value)
    assert fragment in str(caught.value)


def test_non_addon_markers_carry_the_structural_code(tmp_path, write_file):
    no_table = write_file(tmp_path / "a" / "addon.toml", 'title = "not an addon"\n')
    no_name = write_file(tmp_path / "b" / "addon.toml", "[addon]\ndescription = 'x'\n")

    for marker in (no_table, no_name):
        with pytest.raises(ManifestError) as caught:
            parse_manifest(marker)
        assert caught.value.code == "not-an-addon"


def test_non_utf8_marker_raises_manifest_error(tmp_path):
    marker = tmp_path / "addon.toml"
    marker.write_bytes(b"\xff\xfe[addon]")

    with pytest.raises(ManifestError) as caught:
        parse_manifest(marker)

    assert str(marker) in str(caught.value)


def test_manifest_is_hashable_despite_mapping_fields():
    manifest = AddonManifest(name="vendor.crm", urls={"Homepage": "https://example.test"})

    assert isinstance(hash(manifest), int)


@pytest.mark.parametrize("as_bytes", [False, True])
def test_content_entrypoint_matches_file_contract_without_reading_its_diagnostic_path(tmp_path, as_bytes):
    content = """
[addon]
name = "vendor.remote"
description = "Remote metadata"
keywords = ["remote", "catalog"]
category = "Tools"
depends_on = "vendor.foundation"
dependencies = ["httpx>=0.28"]
[web]
package = "@vendor/remote"
[[migrations]]
name = "preserve_rows"
module = "runtime_migrations.preserve_rows"
"""
    marker = tmp_path / "addon.toml"
    marker.write_text(content, encoding="utf-8")
    expected = parse_manifest(marker)
    marker.unlink()
    actual = parse_manifest_content(content.encode("utf-8") if as_bytes else content, path=marker)
    assert actual == expected
    assert actual.depends_on == ("vendor.foundation",)
    assert actual.migrations[0]["name"] == "preserve_rows"
    assert not marker.exists()


@pytest.mark.parametrize(
    "content",
    [
        b"\xff",
        b"[addon",
        b"",
        b"[addon]\n",
        b'[addon]\nname=""\n',
        b'[addon]\nname="x.y"\nkeywords=[1]\n',
        b'[addon]\nname="x.y"\ndescription=3\n',
        b'[addon]\nname="x.y"\ndependencies=["not a requirement @"]\n',
    ],
)
def test_content_and_file_errors_keep_one_source_key_and_code(tmp_path, content):
    marker = tmp_path / "remote" / "addon.toml"
    marker.parent.mkdir()
    marker.write_bytes(content)
    with pytest.raises(ManifestError) as file_error:
        parse_manifest(marker)
    marker.unlink()
    with pytest.raises(ManifestError) as content_error:
        parse_manifest_content(content, path=marker)
    assert content_error.value.path == file_error.value.path == marker
    assert content_error.value.key == file_error.value.key
    assert content_error.value.code == file_error.value.code
    assert str(content_error.value) == str(file_error.value)
