"""Phase 4 test: per-subnet static screening dispatches through the plugin.

Generic anti-cheat checks stay in the core screener; a lane's plugin can add
subnet-specific static findings via ``static_screen``. SN60 adds none (default None),
so its screening is unchanged (covered by the existing screening tests).
"""

from __future__ import annotations

import types
from pathlib import Path

import pytest

from kata.packages import (
    EnvSpec,
    ScoreCard,
    ScoringProfile,
    SubnetPlugin,
    clear_registry,
    register_plugin,
)
from kata.packages.dispatch import load_builtin_plugins
from kata.screening_system.engine import _plugin_static_screen_findings


class _ScreeningPlugin(SubnetPlugin):
    evaluator_id = "t_eval"
    pack = "t__pack"
    mode = "miner"
    scoring_profile = ScoringProfile.DETERMINISTIC
    validator_identity = "t-v"

    def environment_spec(self) -> EnvSpec:
        return EnvSpec()

    def sample_problems(self, *, seed, config):
        return []

    def benchmark_identity(self, problems) -> str:
        return "b"

    def run_candidate(self, *, agent_path, problems, context):
        return None

    def score(self, raw, problems) -> ScoreCard:
        return ScoreCard(comparable=0.0, passed=True)

    def compare(self, a, b) -> int:
        return 0

    def beats_king(self, candidate, king) -> bool:
        return False

    def static_screen(self, submission_path):
        return ["custom subnet finding"]


@pytest.fixture(autouse=True)
def _restore_registry():
    yield
    clear_registry()
    load_builtin_plugins()


def test_static_screen_dispatches_to_lane_plugin(tmp_path: Path, monkeypatch) -> None:
    register_plugin(_ScreeningPlugin())
    monkeypatch.setattr(
        "kata.promotion_system.find_evaluator_pack_entry",
        lambda repo_pack, mode, public_root=None: (
            types.SimpleNamespace(evaluator_id="t_eval")
            if repo_pack == "t__pack"
            else None
        ),
    )
    findings = _plugin_static_screen_findings(
        submission_root=tmp_path, repo_pack="t__pack", mode="miner", public_root=None
    )
    assert findings == ["custom subnet finding"]


def test_static_screen_noop_for_unknown_or_missing_lane(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "kata.promotion_system.find_evaluator_pack_entry",
        lambda repo_pack, mode, public_root=None: None,
    )
    assert (
        _plugin_static_screen_findings(
            submission_root=tmp_path, repo_pack="nope", mode="miner", public_root=None
        )
        == []
    )
    # No repo_pack -> no dispatch at all.
    assert (
        _plugin_static_screen_findings(
            submission_root=tmp_path, repo_pack=None, mode="miner", public_root=None
        )
        == []
    )


def test_sn60_adds_no_extra_static_findings(tmp_path: Path, monkeypatch) -> None:
    load_builtin_plugins()
    monkeypatch.setattr(
        "kata.promotion_system.find_evaluator_pack_entry",
        lambda repo_pack, mode, public_root=None: types.SimpleNamespace(
            evaluator_id="sn60_bitsec"
        ),
    )
    # SN60's generic checks live in the core screener; its plugin adds nothing extra.
    assert (
        _plugin_static_screen_findings(
            submission_root=tmp_path,
            repo_pack="sn60__bitsec",
            mode="miner",
            public_root=None,
        )
        == []
    )
