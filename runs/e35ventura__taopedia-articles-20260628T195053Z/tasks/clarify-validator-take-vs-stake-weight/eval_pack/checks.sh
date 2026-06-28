#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

workspace = Path(os.environ["PROMPTFORGE_WORKSPACE"])
snapshot = Path(os.environ["PROMPTFORGE_REPO_SNAPSHOT"])
target = workspace / "content/pages/validator_take/index.mdx"


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def changed_paths() -> list[str]:
    completed = subprocess.run(
        ["git", "diff", "--no-index", "--name-only", str(snapshot), str(workspace)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode not in {0, 1}:
        fail(completed.stderr.strip() or "Unable to diff workspace against snapshot.")
    prefix = f"{workspace.name}/"
    paths: list[str] = []
    for line in completed.stdout.splitlines():
        value = line.strip().replace("\\", "/")
        if not value:
            continue
        if value.startswith(prefix):
            value = value.removeprefix(prefix)
        paths.append(value)
    return sorted(set(paths))


if not target.exists():
    fail("Expected content/pages/validator_take/index.mdx to exist.")

paths = changed_paths()
if paths != ["content/pages/validator_take/index.mdx"]:
    fail(f"Unexpected changed paths: {paths}")

text = target.read_text(encoding="utf-8")
required_sections = [
    "## Validator Take Is Not Stake Weight",
    "## Reader Shortcut",
]
for section in required_sections:
    if section not in text:
        fail(f"Missing required section: {section}")

required_links = [
    "[[Delegation Rewards]]",
    "[[Effective Stake]]",
    "[[Yuma Consensus]]",
    "https://docs.learnbittensor.org/resources/glossary#validator-take-",
    "https://docs.learnbittensor.org/resources/glossary#stake-weight",
]
for link in required_links:
    if link not in text:
        fail(f"Missing required link: {link}")

required_phrases = [
    "distribution split",
    "validator-side emissions",
    "validator influence",
]
lowered = text.lower()
for phrase in required_phrases:
    if phrase not in lowered:
        fail(f"Missing required concept phrase: {phrase}")
PY
