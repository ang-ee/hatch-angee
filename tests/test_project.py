"""Round-trip-safe generated ``[dependency-groups].addons`` ownership."""

from __future__ import annotations

import pytest
import tomlkit

from hatch_angee.project import GENERATED_COMMENT, ProjectError, write_block


def test_writes_sorted_deduped_block_and_is_idempotent(tmp_path, write_file):
    pyproject = write_file(
        tmp_path / "pyproject.toml",
        """
        [project]
        name = "demo"
        version = "1.0.0"

        [dependency-groups]
        # This group belongs to the operator.
        dev = ["pytest"]
        """,
    )

    write_block(pyproject, ["redis>=5", "httpx>=0.28", "redis>=5"])
    once = pyproject.read_text()
    write_block(pyproject, ["redis>=5", "httpx>=0.28", "redis>=5"])

    assert pyproject.read_text() == once
    assert f"# {GENERATED_COMMENT}\naddons =" in once
    document = tomlkit.parse(once)
    assert document["dependency-groups"]["addons"] == ["httpx>=0.28", "redis>=5"]


def test_replaces_only_existing_addons_key_and_preserves_unrelated_content(tmp_path, write_file):
    pyproject = write_file(
        tmp_path / "pyproject.toml",
        """
        # Project header stays byte-for-byte.
        [project]
        name = "demo" # inline comment stays

        [dependency-groups]
        docs = ["mkdocs"] # independently managed
        addons = ["old-dependency"]

        [tool.demo]
        answer = 42
        """,
    )

    write_block(pyproject, ["new-dependency>=2"])
    content = pyproject.read_text()

    assert "# Project header stays byte-for-byte." in content
    assert 'name = "demo" # inline comment stays' in content
    assert 'docs = ["mkdocs"] # independently managed' in content
    assert "[tool.demo]\nanswer = 42" in content
    assert "old-dependency" not in content
    assert tomlkit.parse(content)["dependency-groups"]["addons"] == ["new-dependency>=2"]


def test_creates_dependency_groups_table_when_absent(tmp_path, write_file):
    pyproject = write_file(
        tmp_path / "pyproject.toml",
        """
        [project]
        name = "demo"
        """,
    )

    write_block(pyproject, [])

    document = tomlkit.parse(pyproject.read_text())
    assert document["project"]["name"] == "demo"
    assert document["dependency-groups"]["addons"] == []
    assert GENERATED_COMMENT in pyproject.read_text()


def test_orphaned_headers_are_reclaimed_to_exactly_one(tmp_path, write_file):
    pyproject = write_file(
        tmp_path / "pyproject.toml",
        f"""
        [dependency-groups]
        # {GENERATED_COMMENT}
        dev = ["pytest"]
        """,
    )

    write_block(pyproject, ["httpx>=0.28"])
    content = pyproject.read_text()

    assert content.count(GENERATED_COMMENT) == 1
    assert f"# {GENERATED_COMMENT}\naddons =" in content
    assert tomlkit.parse(content)["dependency-groups"]["dev"] == ["pytest"]


def test_inline_dependency_groups_name_the_remedy(tmp_path, write_file):
    pyproject = write_file(
        tmp_path / "pyproject.toml",
        'dependency-groups = { dev = ["pytest"] }\n',
    )

    with pytest.raises(ProjectError) as caught:
        write_block(pyproject, [])

    assert "rewrite it as a standard [dependency-groups] table" in str(caught.value)
