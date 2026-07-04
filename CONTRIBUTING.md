# Contributing to Kata

Kata is an objective miner-agent competition repo. Contributions should make
the evaluator, subnet pack workflow, or agent competition machinery more
trustworthy and more useful.

## Principles

- Keep evaluation deterministic and reproducible wherever possible.
- Treat evaluator correctness as higher priority than artifact style.
- Preserve provenance (sandbox commit, benchmark snapshot hashes) so results
  stay comparable over time.
- Never weaken submission validation, screening, or promotion checks without
  a test proving the new behavior.

## Local checks

```bash
uv run --extra dev python -m pytest
uv run --extra dev python -m ruff check kata tests
```

If you change the evaluator adapter, screening, or promotion logic, add or
update tests.

For the full miner PR lifecycle, evaluation stages, promotion flow, and engine
contribution workflow, see `docs/workflow.md`.

## What belongs where

- Engine changes: `kata/`
- Lane and registry state schemas: `kata/lane_state.py`
- Evaluator adapters: `kata/evaluators/`
- Submission contract and validation: `kata/submissions.py`, `kata/screening.py`

Miner submissions belong under `submissions/` via PR, not in engine code.

## Out of scope

- weakening anti-cheat validation
- unpinning the sandbox or benchmark snapshot without a provenance story
- broad artifact rewrites without evaluation evidence
