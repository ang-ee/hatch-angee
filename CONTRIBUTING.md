# Contributing

## Local setup

- Python 3.11+
- `uv` installed

```bash
uv pip install -e .[dev]
```

## Canonical commands

```bash
make lint
make test
make check
```

## Test and lint policy

- Run lint + tests before opening a PR.
- The hooks only fire against a tree containing `addon.toml` markers; the suite
  builds throwaway addon trees under `tmp_path` plus one end-to-end wheel
  (`tests/test_build_backend.py`).
- Add/update tests for behavior changes.

## Releasing

- Bump the version in **both** `pyproject.toml` and `src/hatch_angee/__init__.py`
  — they must match.
- Tag `vX.Y.Z` and push the tag. `.github/workflows/publish-pypi.yml` verifies the
  tag, `pyproject.toml`, and `__version__` all agree, builds with `uv build`, and
  publishes to PyPI using the `PYPI_TOKEN` repository secret.

## CI matrix

CI (`.github/workflows/ci.yml`) validates Python 3.11, 3.12, 3.13, and 3.14.
