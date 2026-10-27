"""Stable dependency ordering across discovery and host projections."""

import pytest

from hatch_angee import order_app_dependencies


def test_dependency_subtrees_precede_each_root_in_declared_order():
    graph = {"alpha": ("zed", "beta"), "beta": ("shared",), "shared": (),
             "zed": (), "independent": (), "disabled": ("disabled",)}
    expected = ("shared", "beta", "zed", "alpha", "independent")
    assert order_app_dependencies(("alpha", "independent"), graph) == expected
    assert order_app_dependencies(("alpha", "independent"), dict(reversed(tuple(graph.items())))) == expected


def test_aliases_and_absent_nodes_use_discovery_owner_identity():
    assert order_app_dependencies(
        ("consumer.Config", "plain"),
        {"consumer": ("alias", "plain"), "dependency": ()},
        aliases={"consumer.Config": "consumer", "alias": "dependency"},
    ) == ("dependency", "consumer")


@pytest.mark.parametrize("graph, roots, message", [
    ({"alpha": ()}, ("alpha", "alpha"), "Duplicate root app 'alpha'"),
    ({"alpha": ("beta", "beta"), "beta": ()}, ("alpha",), "alpha declares duplicate dependency"),
    ({"alpha": ("alpha",)}, ("alpha",), "Cycle in app dependencies: alpha -> alpha"),
    ({"alpha": ("beta",), "beta": ("alpha",)}, ("alpha",),
     "Cycle in app dependencies: alpha -> beta -> alpha"),
])
def test_invalid_selected_graph_fails_with_exact_diagnostic(graph, roots, message):
    with pytest.raises(RuntimeError) as caught:
        order_app_dependencies(roots, graph)
    assert str(caught.value) == message
