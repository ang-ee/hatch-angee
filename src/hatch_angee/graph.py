"""Deterministic dependency traversal shared by manifest and Django app discovery."""

from __future__ import annotations

from collections.abc import Iterable, Mapping


def order_app_dependencies(
    roots: Iterable[str],
    dependencies: Mapping[str, tuple[str, ...]],
    *,
    aliases: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    """Order a discovered app graph, rejecting duplicate edges and cycles.

    Visit roots in declaration order and each app's dependencies lexically,
    completing a dependency's closure before the next sibling or root. This
    precedence determines composed addon contributions. Only nodes supplied by
    the discovery owner participate; dependencies absent from the mapping do not
    participate in the result.
    """

    app_aliases = aliases or {}
    root_names = tuple(roots)
    if len(set(root_names)) != len(root_names):
        duplicate = next(name for name in root_names if root_names.count(name) > 1)
        raise RuntimeError(f"Duplicate root app {duplicate!r}")
    ordered: list[str] = []
    visiting: list[str] = []
    visited: set[str] = set()

    def visit(declaration: str) -> None:
        name = app_aliases.get(declaration, declaration)
        if name not in dependencies or name in visited:
            return
        if name in visiting:
            cycle = " -> ".join((*visiting[visiting.index(name) :], name))
            raise RuntimeError(f"Cycle in app dependencies: {cycle}")
        declared_dependencies = dependencies[name]
        if len(set(declared_dependencies)) != len(declared_dependencies):
            raise RuntimeError(f"{name} declares duplicate dependency")
        visiting.append(name)
        for dependency in sorted(declared_dependencies):
            visit(dependency)
        visiting.pop()
        visited.add(name)
        ordered.append(name)

    for root in root_names:
        visit(root)
    return tuple(ordered)

