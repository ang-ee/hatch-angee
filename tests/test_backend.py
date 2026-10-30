"""Archive, editable and metadata contracts for in-place addon distributions."""

import ast
import email
import tarfile
import zipfile
from importlib.metadata import PathDistribution
from pathlib import Path

import pytest

import hatch_angee


@pytest.fixture(params=["static", "dynamic"])
def addon(tmp_path, monkeypatch, request):
    package = tmp_path / "addons/acme/notes"
    package.mkdir(parents=True)
    (tmp_path / ".gitignore").write_text("node_modules/\n")
    (package / "__init__.py").write_text('VALUE = 42\n')
    identity = ('entry-points."angee.addons"."acme.notes" = "acme.notes"'
                if request.param == "static" else 'dynamic = ["entry-points"]')
    (package / "pyproject.toml").write_text(f'''build-system = {{ requires = ["hatch-angee>=1,<2"], build-backend = "hatch_angee" }}
[project]
name = "acme-notes"
version = "1.0.0"
dependencies = ["django>=6.1"]
keywords = ["foundation", "notes"]
{identity}
''')
    for folder in ("web/src", "templates/notes", "skills/notes", "web/node_modules/unused"):
        target = package / folder / "file.txt"
        target.parent.mkdir(parents=True)
        target.write_text(folder)
    monkeypatch.chdir(package)
    return package


def wheel_files(path):
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def test_wheel_editable_sdist_and_metadata_share_authored_facts(addon, tmp_path, monkeypatch):
    authored = (addon / "pyproject.toml").read_bytes()
    out = tmp_path / "dist"
    out.mkdir()
    expected = {"acme/notes/__init__.py", "acme/notes/pyproject.toml", "acme/notes/web/src/file.txt",
                "acme/notes/templates/notes/file.txt", "acme/notes/skills/notes/file.txt"}
    direct = wheel_files(out / hatch_angee.build_wheel(str(out)))
    assert {name for name in direct if ".dist-info/" not in name} == expected
    metadata = email.message_from_bytes(next(value for name, value in direct.items() if name.endswith("/METADATA")))
    assert metadata.get_all("Requires-Dist") == ["django>=6.1"]
    assert metadata["Requires-Python"] is None
    assert metadata["License-Expression"] is None
    assert set(metadata["Keywords"].split(",")) == {"foundation", "notes"}
    expected_entries = b"[angee.addons]\nacme.notes = acme.notes\n"
    assert next(value for name, value in direct.items() if name.endswith("/entry_points.txt")) == expected_entries
    for prepare in (hatch_angee.prepare_metadata_for_build_wheel, hatch_angee.prepare_metadata_for_build_editable):
        prepared = out / prepare(str(out))
        assert (prepared / "METADATA").read_bytes() == next(value for name, value in direct.items() if name.endswith("/METADATA"))
        distribution = PathDistribution(prepared)
        assert [(point.group, point.name, point.value) for point in distribution.entry_points] == [
            ("angee.addons", "acme.notes", "acme.notes"),
        ]
    editable = wheel_files(out / hatch_angee.build_editable(str(out)))
    assert next(value for name, value in editable.items() if name.endswith("/entry_points.txt")) == expected_entries
    pth = next(value for name, value in editable.items() if name.endswith(".pth"))
    assert Path(pth.decode().strip()) == addon.parents[1]
    source = out / hatch_angee.build_sdist(str(out))
    assert (addon / "pyproject.toml").read_bytes() == authored
    assert direct["acme/notes/pyproject.toml"] == authored
    extracted = tmp_path / "unpacked"
    with tarfile.open(source) as archive:
        archive.extractall(extracted, filter="data")
    monkeypatch.chdir(next(extracted.iterdir()))
    rebuilt = wheel_files(out / hatch_angee.build_wheel(str(out)))
    assert rebuilt == direct


def test_authored_hatch_configuration_wins(addon, tmp_path):
    with (addon / "pyproject.toml").open("a") as stream:
        stream.write('\n[tool.hatch.build]\nexclude = ["web", "skills", "templates"]\n')
    archive = wheel_files(tmp_path / hatch_angee.build_wheel(str(tmp_path)))
    assert "acme/notes/web/src/file.txt" not in archive


@pytest.mark.parametrize("addon", ["static"], indirect=True)
@pytest.mark.parametrize("replacement", [
    ('name = "acme-notes"', 'name = "wrong"'),
    ('entry-points."angee.addons"."acme.notes" = "acme.notes"', ''),
    ('entry-points."angee.addons"."acme.notes" = "acme.notes"',
     'entry-points."angee.addons"."acme.notes" = "acme.notes"\nentry-points."angee.addons"."acme.more" = "acme.more"'),
])
def test_invalid_identity_fails_before_build(addon, tmp_path, replacement):
    target = addon / "pyproject.toml"
    target.write_text(target.read_text().replace(*replacement))
    with pytest.raises(ValueError):
        hatch_angee.build_wheel(str(tmp_path))


@pytest.mark.parametrize("addon", ["dynamic"], indirect=True)
@pytest.mark.parametrize("name", ["acme-integrate-notes", "Acme.Integrate_Notes"])
def test_dynamic_identity_survives_sdist_relocation(addon, tmp_path, monkeypatch, name):
    project = addon / "pyproject.toml"
    project.write_text(project.read_text().replace('name = "acme-notes"', f'name = "{name}"'))
    package = addon.with_name("integrate_notes")
    addon.rename(package)
    monkeypatch.chdir(package)
    direct = wheel_files(tmp_path / hatch_angee.build_wheel(str(tmp_path)))
    source = tmp_path / hatch_angee.build_sdist(str(tmp_path))
    extracted = tmp_path / "unpacked"
    with tarfile.open(source) as archive:
        archive.extractall(extracted, filter="data")
    monkeypatch.chdir(next(extracted.iterdir()))
    assert wheel_files(tmp_path / hatch_angee.build_wheel(str(tmp_path))) == direct
    assert "acme/integrate_notes/__init__.py" in direct
    assert next(value for name, value in direct.items() if name.endswith("/entry_points.txt")) == (
        b"[angee.addons]\nacme.integrate_notes = acme.integrate_notes\n"
    )


@pytest.mark.parametrize("addon", ["dynamic"], indirect=True)
@pytest.mark.parametrize("name", ["notes", "9acme-notes", "acme-9notes"])
def test_dynamic_identity_rejects_invalid_import_names(addon, tmp_path, name):
    project = addon / "pyproject.toml"
    project.write_text(project.read_text().replace('name = "acme-notes"', f'name = "{name}"'))
    with pytest.raises(ValueError, match="addon"):
        hatch_angee.build_wheel(str(tmp_path))


@pytest.mark.parametrize("addon", ["dynamic"], indirect=True)
def test_dynamic_entry_points_do_not_overwrite_authored_groups(addon, tmp_path):
    with (addon / "pyproject.toml").open("a") as stream:
        stream.write('\n[project.entry-points.other]\nnotes = "acme.notes:VALUE"\n')
    with pytest.raises(ValueError, match="static entry points or dynamic"):
        hatch_angee.build_wheel(str(tmp_path))


@pytest.mark.parametrize("addon", ["static"], indirect=True)
def test_static_entry_point_preserves_app_config_and_other_groups(addon, tmp_path):
    project = addon / "pyproject.toml"
    project.write_text(project.read_text().replace(
        'entry-points."angee.addons"."acme.notes" = "acme.notes"',
        'entry-points."angee.addons"."acme.notes" = "acme.notes.apps.NotesConfig"\n'
        'entry-points.other.notes = "acme.notes:VALUE"',
    ))
    files = wheel_files(tmp_path / hatch_angee.build_wheel(str(tmp_path)))
    entries = next(value for name, value in files.items() if name.endswith("/entry_points.txt"))
    assert b"acme.notes = acme.notes.apps.NotesConfig" in entries
    assert b"[other]\nnotes = acme.notes:VALUE" in entries


def test_direct_references_default_to_allowed_but_explicit_false_wins(addon, tmp_path):
    project = addon / "pyproject.toml"
    requirement = "demo @ https://example.invalid/demo.whl"
    project.write_text(project.read_text().replace('"django>=6.1"', f'"{requirement}"'))
    files = wheel_files(tmp_path / hatch_angee.build_wheel(str(tmp_path)))
    metadata = email.message_from_bytes(next(value for name, value in files.items() if name.endswith("/METADATA")))
    assert metadata.get_all("Requires-Dist") == [requirement]
    with project.open("a") as stream:
        stream.write('\n[tool.hatch.metadata]\nallow-direct-references = false\n')
    with pytest.raises(ValueError, match="direct reference"):
        hatch_angee.build_wheel(str(tmp_path))


def test_layout_mismatch_fails(addon, tmp_path, monkeypatch):
    wrong = addon.with_name("wrong")
    addon.rename(wrong)
    monkeypatch.chdir(wrong)
    with pytest.raises(ValueError, match="package directory"):
        hatch_angee.build_wheel(str(tmp_path))


def test_backend_reads_no_capability_or_dependency_contracts():
    source = Path(hatch_angee.__file__).read_text()
    tree = ast.parse(source)
    imports = {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert imports <= {"__future__", "pathlib", "typing", "hatchling"}
    assert 'config["tool"]' not in source
    assert 'project["dependencies"]' not in source
    assert not any(path.name in {"manifest.py", "discovery.py", "compile.py", "hooks.py", "graph.py"}
                   for path in Path(hatch_angee.__file__).parent.glob("*.py"))


def test_exact_editable_metadata_preserves_native_runtime_requirement(addon, tmp_path):
    with (addon / "pyproject.toml").open("a") as stream:
        stream.write('\n[tool.hatch.build]\ndev-mode-dirs = []\ndev-mode-exact = true\n')
    prepared = tmp_path / hatch_angee.prepare_metadata_for_build_editable(str(tmp_path)) / "METADATA"
    expected = email.message_from_bytes(prepared.read_bytes()).get_all("Requires-Dist")
    editable = wheel_files(tmp_path / hatch_angee.build_editable(str(tmp_path)))
    actual = email.message_from_bytes(next(value for name, value in editable.items() if name.endswith("/METADATA")))
    assert actual.get_all("Requires-Dist") == expected
    assert "editables~=0.3" in expected
