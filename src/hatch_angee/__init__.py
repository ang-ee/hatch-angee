"""Hatchling defaults for one in-place Angee addon distribution.

Hatchling owns metadata and archives. This backend supplies package layout,
direct-reference defaults and opt-in dynamic addon entry points. Keywords and
other authored metadata pass through unchanged.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path
from typing import Any, cast

from hatchling.builders.constants import EDITABLES_REQUIREMENT
from hatchling.builders.sdist import SdistBuilder
from hatchling.builders.wheel import WheelBuilder
from hatchling.metadata.core import ProjectMetadata
from hatchling.metadata.plugin.interface import MetadataHookInterface
from hatchling.metadata.utils import normalize_project_name
from hatchling.plugin import hookimpl
from hatchling.plugin.manager import PluginManager


class _AddonMetadataHook(MetadataHookInterface):
    """Supply the explicitly dynamic entry point from a portable package name."""

    PLUGIN_NAME = "angee"

    def update(self, metadata: dict[str, Any]) -> None:
        if "entry-points" not in metadata.get("dynamic", []):
            return
        if "entry-points" in metadata:
            raise ValueError("Declare static entry points or dynamic entry-points, not both")
        namespace, separator, label = normalize_project_name(metadata["name"]).partition("-")
        app = f"{namespace}.{label.replace('-', '_')}"
        if not separator:
            raise ValueError("Dynamic addon entry points require a namespace-addon distribution name")
        metadata["entry-points"] = {"angee.addons": {app: app}}


@hookimpl
def hatch_register_metadata_hook() -> type[_AddonMetadataHook]:
    return _AddonMetadataHook


def _builder(target: str) -> Any:
    root = Path.cwd()
    config = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    project = config["project"]
    hatch = config.setdefault("tool", {}).setdefault("hatch", {})
    metadata_config = hatch.setdefault("metadata", {})
    metadata_config.setdefault("allow-direct-references", True)
    if "entry-points" in project.get("dynamic", []):
        metadata_config.setdefault("hooks", {}).setdefault(_AddonMetadataHook.PLUGIN_NAME, {})
    plugins = PluginManager()
    plugins.manager.register(sys.modules[__name__])
    metadata = ProjectMetadata(str(root), plugins, config)
    entries = metadata.core.entry_points.get("angee.addons", {})
    if len(entries) != 1:
        raise ValueError("An addon distribution must provide exactly one angee.addons entry point")
    app = next(iter(entries))
    parts = app.split(".")
    if not all(part.isidentifier() for part in parts):
        raise ValueError(f"Invalid addon package {app!r}")
    expected = normalize_project_name(app)
    if metadata.name != expected:
        raise ValueError(f"Addon {app!r} must use distribution name {expected!r}")
    # sdists are relocated archives, identified by Hatchling's native metadata.
    if not (root / "PKG-INFO").is_file() and tuple(root.parts[-len(parts):]) != tuple(parts):
        raise ValueError(f"Addon package directory must end in {'/'.join(parts)!r}")
    build = hatch.setdefault("build", {})
    build.setdefault("include", ["*"])
    build.setdefault("exclude", ["PKG-INFO", ".gitignore"])
    wheel = build.setdefault("targets", {}).setdefault("wheel", {})
    if "sources" not in build:
        wheel.setdefault("sources", {"": "/".join(parts)})
    if "dev-mode-dirs" not in build:
        wheel.setdefault("dev-mode-dirs", ["/".join([".."] * len(parts))])
    cls = WheelBuilder if target == "wheel" else SdistBuilder
    return cls(str(root), plugin_manager=plugins, config=config, metadata=metadata)


def _build(target: str, directory: str, version: str) -> str:
    return Path(next(_builder(target).build(directory=directory, versions=[version]))).name


def build_wheel(wheel_directory: str, config_settings: Any = None, metadata_directory: str | None = None) -> str:
    return _build("wheel", wheel_directory, "standard")


def build_editable(wheel_directory: str, config_settings: Any = None, metadata_directory: str | None = None) -> str:
    return _build("wheel", wheel_directory, "editable")


def build_sdist(sdist_directory: str, config_settings: Any = None) -> str:
    return _build("sdist", sdist_directory, "standard")


def get_requires_for_build_wheel(config_settings: Any = None) -> list[str]:
    return cast(list[str], _builder("wheel").config.dependencies)


def get_requires_for_build_editable(config_settings: Any = None) -> list[str]:
    return [*_builder("wheel").config.dependencies, EDITABLES_REQUIREMENT]


def get_requires_for_build_sdist(config_settings: Any = None) -> list[str]:
    return cast(list[str], _builder("sdist").config.dependencies)


def _prepare_metadata(metadata_directory: str, *, editable: bool) -> str:
    builder = _builder("wheel")
    directory = Path(metadata_directory) / f"{builder.artifact_project_id}.dist-info"
    directory.mkdir(exist_ok=True)
    dependencies = []
    if editable and not builder.config.dev_mode_dirs and builder.config.dev_mode_exact:
        dependencies.append(EDITABLES_REQUIREMENT)
    metadata = builder.config.core_metadata_constructor(builder.metadata, extra_dependencies=dependencies)
    (directory / "METADATA").write_text(metadata, encoding="utf-8")
    if entry_points := builder.construct_entry_points_file():
        (directory / "entry_points.txt").write_text(entry_points, encoding="utf-8")
    return directory.name


def prepare_metadata_for_build_wheel(metadata_directory: str, config_settings: Any = None) -> str:
    return _prepare_metadata(metadata_directory, editable=False)


def prepare_metadata_for_build_editable(metadata_directory: str, config_settings: Any = None) -> str:
    return _prepare_metadata(metadata_directory, editable=True)
