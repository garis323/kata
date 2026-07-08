from __future__ import annotations

from pathlib import Path

from kata.screening import validate_sn60_static_screening
from kata.screening_system.models import ScreeningDecision, ScreeningFinding


def screen_submission(
    *,
    submission_root: Path,
    changed_paths: list[str] | None = None,
    repo_root: Path | None = None,
    public_root: Path | None = None,
    pr_author: str | None = None,
    mode: str = "miner",
    enable_review: bool = False,
) -> ScreeningDecision:
    """Run the screening subsystem for a candidate submission.

    Phase 1 intentionally preserves current behavior: it wraps the existing SN60
    static screening checks in a structured decision object. The extra arguments
    are part of the stable subsystem API and will be used by later layers.
    """
    del changed_paths, repo_root, public_root, pr_author, enable_review
    if mode != "miner":
        return ScreeningDecision(status="pass")

    findings = [
        ScreeningFinding(
            rule_id="sn60.static",
            severity="reject",
            path="agent.py",
            line=None,
            reason=reason,
            evidence=reason,
        )
        for reason in validate_sn60_static_screening(submission_root)
    ]
    if findings:
        return ScreeningDecision(status="reject", reject_reasons=findings)
    return ScreeningDecision(status="pass")
