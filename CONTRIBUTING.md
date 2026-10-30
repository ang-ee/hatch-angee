# Contributing

## Local setup

Use Python 3.11+ and uv. From this repository root:

```bash
make install-dev
```

## Canonical commands

```bash
make lint
make typecheck
make test
make check
uv build
```

`make check` runs lint, strict source type checking and the complete test suite.
The contracts in `tests/test_backend.py` build throwaway addon distributions and
exercise wheel, editable, sdist, relocated-sdist and prepared metadata entrypoints.
Cover authored and opted-in dynamic entry points when changing backend behavior.
Hatchling owns project metadata and archives; see [the authoring contract](README.md).

## Releasing

Set the release version in `pyproject.toml`, refresh `uv.lock` with `uv lock`, and
run `make check` and `uv build`. The project table is the sole version owner.
After review, tag the release commit `vX.Y.Z` and push the tag.
[The publishing workflow](.github/workflows/publish-pypi.yml) verifies that the tag
matches the project version, builds with `uv build`, and publishes to PyPI using
the `PYPI_TOKEN` repository secret.

## CI matrix

[CI](.github/workflows/ci.yml) runs lint, strict source type checking and tests on
Python 3.11, 3.12, 3.13 and 3.14 against the newest Hatchling release. The declared
minimum Hatchling version must also pass the backend suite before a release.
