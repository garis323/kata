"""Resolve the subnet plugin for a submission/lane (Phase 4 of the refactor).

The core dispatches by ``evaluator_id`` -- the same id the lane registry records --
without importing any subnet package directly. Built-in plugins are loaded lazily so
importing this module stays cheap and cycle-free.
"""

from __future__ import annotations

from kata.packages.plugin import SubnetPlugin
from kata.packages.registry import get_plugin_or_none, register_plugin


def load_builtin_plugins() -> None:
    """Ensure the built-in subnet plugins are registered.

    Importing a plugin package registers it as a side effect; this also re-registers
    defensively so a cleared registry (e.g. in tests) is repaired. Cheap to call
    repeatedly -- the module import is cached after the first call.
    """
    from kata.packages import sn60

    if get_plugin_or_none(sn60.SN60_BITSEC_PLUGIN.evaluator_id) is None:
        register_plugin(sn60.SN60_BITSEC_PLUGIN)


def plugin_for_evaluator(evaluator_id: str | None) -> SubnetPlugin | None:
    """Return the registered plugin for ``evaluator_id``, or ``None`` if there is none."""
    if not evaluator_id:
        return None
    load_builtin_plugins()
    return get_plugin_or_none(evaluator_id)
