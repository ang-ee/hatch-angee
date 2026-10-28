"""Schema and parser for Angee's co-located ``addon.toml`` manifests."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name


class ManifestError(ValueError):
    """A manifest error that identifies both the source file and failing key.

    ``code`` carries the machine-readable case so callers never match on the
    human message; ``"not-an-addon"`` marks a marker file that is not an addon
    manifest at all (no ``[addon]`` table or no ``name``), which discovery
    skips for parity with the original build hooks.
    """

    def __init__(self, path: Path, key: str, message: str, *, code: str | None = None) -> None:
        self.path = path
        self.key = key
        self.message = message
        self.code = code
        super().__init__(f"{path}: {key}: {message}")


@dataclass(frozen=True, slots=True)
class AddonManifest:
    """The stable addon contract plus pass-through contribution seam data.

    Mapping-valued fields are excluded from the hash so the frozen dataclass
    stays hashable (identity for sets/keys is the scalar contract, led by
    ``name``); equality still compares every field.
    """

    name: str
    description: str = ""
    keywords: tuple[str, ...] = ()
    category: str | None = None
    license: str | None = None
    readme: str | None = None
    version: str | None = None
    authors: tuple[Mapping[str, Any], ...] = field(default=(), hash=False)
    urls: Mapping[str, str] = field(default_factory=dict, hash=False)
    depends_on: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    requires: str | None = None
    schemas: str | None = None
    permissions: str | None = None
    web: Mapping[str, Any] = field(default_factory=dict, hash=False)
    mcp: Mapping[str, Any] = field(default_factory=dict, hash=False)
    resources: Mapping[str, Any] = field(default_factory=dict, hash=False)
    migrations: tuple[Mapping[str, Any], ...] = field(default=(), hash=False)


def _error(path: Path, key: str, message: str, *, code: str | None = None) -> ManifestError:
    return ManifestError(path, key, message, code=code)


def _required_string(addon: Mapping[str, Any], key: str, path: Path, *, code: str | None = None) -> str:
    if key not in addon:
        raise _error(path, f"addon.{key}", "is required", code=code)
    value = addon.get(key)
    if not isinstance(value, str) or not value:
        raise _error(path, f"addon.{key}", "must be a non-empty string")
    return value


def _optional_string(addon: Mapping[str, Any], key: str, path: Path) -> str | None:
    value = addon.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise _error(path, f"addon.{key}", "must be a non-empty string")
    return value


def _string_list(
    value: Any,
    *,
    path: Path,
    key: str,
    allow_single: bool = False,
) -> tuple[str, ...]:
    if value is None:
        return ()
    if allow_single and isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        raise _error(path, key, "must be an array of strings")
    result: list[str] = []
    for index, entry in enumerate(value):
        if not isinstance(entry, str) or not entry:
            raise _error(path, f"{key}[{index}]", "must be a non-empty string")
        result.append(entry)
    return tuple(result)


def _table(data: Mapping[str, Any], key: str, path: Path) -> dict[str, Any]:
    value = data.get(key, {})
    if not isinstance(value, Mapping):
        raise _error(path, key, "must be a table")
    return dict(value)


def _authors(addon: Mapping[str, Any], path: Path) -> tuple[Mapping[str, Any], ...]:
    value = addon.get("authors", [])
    if not isinstance(value, list):
        raise _error(path, "addon.authors", "must be an array of tables")
    result: list[Mapping[str, Any]] = []
    for index, author in enumerate(value):
        if not isinstance(author, Mapping):
            raise _error(path, f"addon.authors[{index}]", "must be a table")
        result.append(dict(author))
    return tuple(result)


def _urls(addon: Mapping[str, Any], path: Path) -> Mapping[str, str]:
    value = addon.get("urls", {})
    if not isinstance(value, Mapping):
        raise _error(path, "addon.urls", "must be a table")
    result: dict[str, str] = {}
    for name, url in value.items():
        if not isinstance(name, str) or not isinstance(url, str):
            raise _error(path, f"addon.urls.{name}", "must be a string")
        result[name] = url
    return result


def _dependencies(addon: Mapping[str, Any], path: Path) -> tuple[str, ...]:
    dependencies = _string_list(
        addon.get("dependencies"), path=path, key="addon.dependencies"
    )
    for index, dependency in enumerate(dependencies):
        try:
            Requirement(dependency)
        except InvalidRequirement as error:
            raise _error(
                path,
                f"addon.dependencies[{index}]",
                f"invalid PEP 508 requirement {dependency!r}: {error}",
            ) from error
    return dependencies


def _requires(addon: Mapping[str, Any], path: Path) -> str | None:
    requires = _optional_string(addon, "requires", path)
    if requires is None:
        return None
    try:
        requirement = Requirement(requires)
    except InvalidRequirement as error:
        raise _error(
            path,
            "addon.requires",
            f"invalid PEP 508 requirement {requires!r}: {error}",
        ) from error
    if canonicalize_name(requirement.name) != "angee-django":
        raise _error(path, "addon.requires", "must name the angee-django core distribution")
    # `requires` declares a version-compatibility floor and nothing else; a URL
    # yields an empty specifier (the check could never fire), and markers/extras
    # have no defined meaning in a compatibility declaration.
    if requirement.url is not None:
        raise _error(path, "addon.requires", "must be a version specifier, not a direct URL")
    if requirement.extras:
        raise _error(path, "addon.requires", "must not declare extras")
    if requirement.marker is not None:
        raise _error(path, "addon.requires", "must not carry an environment marker")
    return requires


def _migrations(data: Mapping[str, Any], path: Path) -> tuple[Mapping[str, Any], ...]:
    value = data.get("migrations", [])
    if not isinstance(value, list):
        raise _error(path, "migrations", "must be an array of tables")
    result: list[Mapping[str, Any]] = []
    for index, migration in enumerate(value):
        if not isinstance(migration, Mapping):
            raise _error(path, f"migrations[{index}]", "must be a table")
        result.append(dict(migration))
    return tuple(result)


def parse_manifest(path: Path | str) -> AddonManifest:
    """Read and validate one filesystem addon.toml through the content owner."""

    marker = Path(path)
    try:
        content = marker.read_bytes()
    except OSError as error:
        raise _error(marker, "file", str(error)) from error
    return parse_manifest_content(content, path=marker)


def parse_manifest_content(content: bytes | str, *, path: Path | str = "addon.toml") -> AddonManifest:
    """Parse one UTF-8 blob or decoded TOML text with the same manifest rules.

    path is diagnostic identity only and is never opened. Stable addon vocabulary
    is validated eagerly; contribution seam tables retain their mappings so their
    independently evolving inner schemas do not force a parser release.
    """

    marker = Path(path)
    try:
        text = content.decode("utf-8") if isinstance(content, bytes) else content
        data = tomllib.loads(text)
    except UnicodeDecodeError as error:
        raise _error(marker, "file", str(error)) from error
    except tomllib.TOMLDecodeError as error:
        raise _error(marker, "toml", str(error)) from error

    if "addon" not in data:
        raise _error(marker, "addon", "is required", code="not-an-addon")
    addon = data.get("addon")
    if not isinstance(addon, Mapping):
        raise _error(marker, "addon", "must be a table")

    description = addon.get("description", "")
    if not isinstance(description, str):
        raise _error(marker, "addon.description", "must be a string")

    return AddonManifest(
        name=_required_string(addon, "name", marker, code="not-an-addon"),
        description=description,
        keywords=_string_list(addon.get("keywords"), path=marker, key="addon.keywords"),
        category=_optional_string(addon, "category", marker),
        license=_optional_string(addon, "license", marker),
        readme=_optional_string(addon, "readme", marker),
        version=_optional_string(addon, "version", marker),
        authors=_authors(addon, marker),
        urls=_urls(addon, marker),
        depends_on=_string_list(
            addon.get("depends_on"),
            path=marker,
            key="addon.depends_on",
            allow_single=True,
        ),
        dependencies=_dependencies(addon, marker),
        requires=_requires(addon, marker),
        schemas=_optional_string(addon, "schemas", marker),
        permissions=_optional_string(addon, "permissions", marker),
        web=_table(data, "web", marker),
        mcp=_table(data, "mcp", marker),
        resources=_table(data, "resources", marker),
        migrations=_migrations(data, marker),
    )
