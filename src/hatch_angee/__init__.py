"""hatch-angee — the one published implementation of Angee's addon build machinery.

Addon repos depend on this at build time and reference the hooks by name; they
ship no ``hatch_build.py`` of their own. See ``hooks.py``.
"""

__version__ = "0.1.3"
