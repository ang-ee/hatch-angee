"""Dependency union compilation and core compatibility checks."""

from __future__ import annotations

from hatch_angee.compile import RequiresViolation, check_requires, compile_dependencies
from hatch_angee.manifest import AddonManifest


def test_compile_dependencies_returns_exact_sorted_deduped_union():
    manifests = [
        AddonManifest(name="vendor.crm", dependencies=("redis>=5", "httpx>=0.28")),
        AddonManifest(name="vendor.iam", dependencies=("django-axes>=7", "redis>=5")),
    ]

    assert compile_dependencies(manifests) == (
        "django-axes>=7",
        "httpx>=0.28",
        "redis>=5",
    )


def test_compile_dependencies_does_not_merge_versions():
    manifests = [
        AddonManifest(name="one", dependencies=("redis>=5",)),
        AddonManifest(name="two", dependencies=("redis<6",)),
    ]

    assert compile_dependencies(manifests) == ("redis<6", "redis>=5")


def test_check_requires_returns_sorted_violations():
    manifests = [
        AddonManifest(name="vendor.ok", requires="angee-django>=0.3,<0.4"),
        AddonManifest(name="vendor.future", requires="angee-django>=0.4"),
        AddonManifest(name="vendor.old", requires="angee-django<0.3"),
        AddonManifest(name="vendor.any"),
    ]

    assert check_requires(manifests, "0.3.2") == [
        RequiresViolation("vendor.future", "angee-django>=0.4", "0.3.2"),
        RequiresViolation("vendor.old", "angee-django<0.3", "0.3.2"),
    ]


def test_prerelease_and_dev_cores_satisfy_their_range():
    manifests = [AddonManifest(name="vendor.crm", requires="angee-django>=0.3,<0.5")]

    assert check_requires(manifests, "0.4.0.dev1") == []
    assert check_requires(manifests, "0.4.0rc1") == []
