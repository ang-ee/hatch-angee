"""The library face stays import-clean of the backend's and runtime's worlds.

The decoupling contract: manifest/discovery/compile/project (the library the
Angee composer imports in-process) may touch stdlib + ``packaging`` +
``tomlkit`` only; hatchling belongs to the backend face (``hooks``/``build``),
Django to the caller. A subprocess keeps ``sys.modules`` honest.
"""

from __future__ import annotations

import subprocess
import sys

_PROBE = """
import sys
import hatch_angee
import hatch_angee.compile
import hatch_angee.discovery
import hatch_angee.manifest
import hatch_angee.project

banned = sorted(
    name for name in sys.modules if name.split(".")[0] in {"hatchling", "django"}
)
assert not banned, f"library face imported backend/runtime modules: {banned}"
"""


def test_library_modules_import_without_hatchling_or_django():
    subprocess.run([sys.executable, "-c", _PROBE], check=True)
