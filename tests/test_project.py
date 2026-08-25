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


def test_mid_file_table_is_byte_idempotent_without_blank_line_growth(tmp_path, write_file):
    original = f'''[project]
name = "demo"

[dependency-groups]
dev = ["pytest"]
# {GENERATED_COMMENT}
addons = [
    "httpx>=0.28",
]

[tool.uv]
default-groups = ["dev", "addons"]
'''
    pyproject = write_file(tmp_path / "pyproject.toml", original)

    outputs = []
    for _ in range(3):
        write_block(pyproject, ["httpx>=0.28"])
        outputs.append(pyproject.read_bytes())

    assert outputs == [original.encode()] * 3


def test_last_table_is_a_byte_identical_no_op(tmp_path, write_file):
    original = f'''[project]
name = "demo"

[dependency-groups]
dev = ["pytest"]
# {GENERATED_COMMENT}
addons = [
    "httpx>=0.28",
]
'''
    pyproject = write_file(tmp_path / "pyproject.toml", original)

    write_block(pyproject, ["httpx>=0.28"])

    assert pyproject.read_bytes() == original.encode()


def test_fresh_table_has_stable_position_and_one_header(tmp_path, write_file):
    pyproject = write_file(
        tmp_path / "pyproject.toml",
        '''[project]
name = "demo"

[tool.uv]
default-groups = ["dev", "addons"]
''',
    )
    expected = f'''[project]
name = "demo"

[tool.uv]
default-groups = ["dev", "addons"]

[dependency-groups]
# {GENERATED_COMMENT}
addons = [
    "httpx>=0.28",
]
'''

    write_block(pyproject, ["httpx>=0.28"])
    write_block(pyproject, ["httpx>=0.28"])

    assert pyproject.read_text() == expected
    assert pyproject.read_text().count(GENERATED_COMMENT) == 1


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


def test_duplicate_and_orphaned_headers_are_reclaimed(tmp_path, write_file):
    pyproject = write_file(
        tmp_path / "pyproject.toml",
        f'''[dependency-groups]
# {GENERATED_COMMENT}
# Operator comment stays.
dev = ["pytest"]
# {GENERATED_COMMENT}
addons = ["old-dependency"]
# {GENERATED_COMMENT}

[tool.uv]
default-groups = ["dev", "addons"]
''',
    )

    write_block(pyproject, ["httpx>=0.28"])
    content = pyproject.read_text()

    assert content.count(GENERATED_COMMENT) == 1
    assert "# Operator comment stays.\ndev = [\"pytest\"]" in content
    assert f'# {GENERATED_COMMENT}\naddons = [\n    "httpx>=0.28",\n]' in content
    assert "old-dependency" not in content
    assert "\n\n[tool.uv]\n" in content


def test_inline_dependency_groups_name_the_remedy(tmp_path, write_file):
    pyproject = write_file(
        tmp_path / "pyproject.toml",
        'dependency-groups = { dev = ["pytest"] }\n',
    )

    with pytest.raises(ProjectError) as caught:
        write_block(pyproject, [])

    assert "rewrite it as a standard [dependency-groups] table" in str(caught.value)
