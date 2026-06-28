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
target = workspace / "content/pages/subnet_77/index.mdx"


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
    fail("Expected content/pages/subnet_77/index.mdx to exist.")

paths = changed_paths()
if paths != ["content/pages/subnet_77/index.mdx"]:
    fail(f"Unexpected changed paths: {paths}")

text = target.read_text(encoding="utf-8")
required_sections = [
    "## Identity Mapping Boundary",
    "## Pool Selection Boundary",
]
for section in required_sections:
    if section not in text:
        fail(f"Missing required section: {section}")

required_links = [
    "[[Yuma Consensus]]",
    "[[Liquidity Positions]]",
    "https://raw.githubusercontent.com/creativebuilds/sn77/master/README.md",
    "https://github.com/creativebuilds/sn77",
]
for link in required_links:
    if link not in text:
        fail(f"Missing required link: {link}")

required_phrases = [
    "evm address",
    "bittensor hotkey",
    "registration step",
    "external liquidity pools",
]
lowered = text.lower()
for phrase in required_phrases:
    if phrase not in lowered:
        fail(f"Missing required concept phrase: {phrase}")
PY
