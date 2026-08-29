"""hatch-angee — the one published implementation of Angee's addon build machinery.

Addon repos depend on this at build time and reference the hooks by name; Angee's
composer also calls its manifest and dependency helpers in-process.
"""

from hatch_angee.compile import RequiresViolation, check_requires, compile_dependencies
from hatch_angee.discovery import discover
from hatch_angee.manifest import AddonManifest, ManifestError, parse_manifest
from hatch_angee.project import ProjectError, write_block

__all__ = [
    "AddonManifest",
    "ManifestError",
    "ProjectError",
    "RequiresViolation",
    "check_requires",
    "compile_dependencies",
    "discover",
    "parse_manifest",
    "write_block",
]

__version__ = "0.2.3"
