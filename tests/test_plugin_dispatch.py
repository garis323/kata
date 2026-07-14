"""Tests: resolving the subnet plugin for a submission/lane.

Uses the in-repo ``sn22`` stub as the concrete registered subnet (real subnets like SN60 live in
their own repos and are discovered via entry points when installed).
"""

from __future__ import annotations

import pytest

from kata.packages.dispatch import load_builtin_plugins, plugin_for_evaluator
from kata.packages.registry import clear_registry, get_plugin_or_none


@pytest.fixture(autouse=True)
def _keep_builtins_registered():
    yield
    load_builtin_plugins()  # leave the registry in its normal (discovered) state


def test_plugin_for_evaluator_resolves_registered() -> None:
    plugin = plugin_for_evaluator("sn22_desearch")
    assert plugin is not None
    assert plugin.evaluator_id == "sn22_desearch"


def test_plugin_for_evaluator_unknown_or_blank() -> None:
    assert plugin_for_evaluator("does-not-exist") is None
    assert plugin_for_evaluator(None) is None
    assert plugin_for_evaluator("") is None


def test_load_builtin_plugins_repairs_cleared_registry() -> None:
    load_builtin_plugins()
    assert get_plugin_or_none("sn22_desearch") is not None
    clear_registry()
    assert get_plugin_or_none("sn22_desearch") is None
    load_builtin_plugins()  # defensively re-registers even after the module import cache
    assert get_plugin_or_none("sn22_desearch") is not None
