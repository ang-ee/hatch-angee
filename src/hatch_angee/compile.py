"""Compile addon manifests into dependency and compatibility projections."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from packaging.requirements import Requirement
from packaging.version import Version

from hatch_angee.manifest import AddonManifest


@dataclass(frozen=True, slots=True)
class RequiresViolation:
    """One addon whose declared core compatibility excludes the active core."""

    addon: str
    requires: str
    core_version: str


def compile_dependencies(manifests: Iterable[AddonManifest]) -> tuple[str, ...]:
    """Return the exact, sorted union of every manifest's PEP 508 dependencies."""

    dependencies = {
        dependency for manifest in manifests for dependency in manifest.dependencies
    }
    return tuple(sorted(dependencies))


def check_requires(
    manifests: Iterable[AddonManifest], core_version: str | Version
) -> list[RequiresViolation]:
    """Return deterministic violations of addon core-version requirements."""

    version = core_version if isinstance(core_version, Version) else Version(core_version)
    violations = [
        RequiresViolation(manifest.name, manifest.requires, str(version))
        for manifest in manifests
        if manifest.requires is not None
        # prereleases=True pins the policy explicitly: a dev/pre core (the
        # normal state of the framework between releases) satisfies its range.
        # The bare `in` operator's default flipped between packaging releases.
        and not Requirement(manifest.requires).specifier.contains(version, prereleases=True)
    ]
    return sorted(violations, key=lambda violation: violation.addon)
