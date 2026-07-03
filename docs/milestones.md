# Roadmap & Milestones

Kata is built to run many competition packs on one engine. This page tracks what is
running today and what is planned next.

## Current status

**One pack is live: `sn60__bitsec` (miner mode).** It is the only competition
registered and active in `lanes/registry.json`, and it runs the full loop end-to-end
in production. The engine is pack-agnostic underneath, but SN60 is the single
integration live today.

Working today:

- **Full competition loop** — submit → validate → screen → duel → decide → verify →
  promote — driven through the pack registry.
- **Isolated, fair execution** — agents run in an internet-blocked sandbox and are
  pinned to one fixed model, so the king and every challenger are judged identically.
- **Strict, objective promotion** — a challenger is promoted only if it beats the king
  on the comparator (aggregated score, then codebases passed, then true positives),
  and never if it has an invalid run.
- **GitHub automation** — webhook intake, a durable PR queue, and a resident service
  that runs the engine, comments results, and applies outcome labels.
- **Reproducible provenance** — every duel records benchmark and artifact hashes; a
  freshness check re-runs a result rather than merging it if the king or benchmark
  changed underneath it.
- **Dashboard** — live evaluation status and current-king state.
- **Faster decisive duels** — a clearly-decided challenger can be resolved without
  running the entire benchmark, while genuine contenders are always evaluated in full.

## Goals

### Grow the competition surface

- Broaden benchmark coverage within the SN60 pack.
- Add new evaluator packs by registering them — no engine rewrite.
- Run multiple packs side by side, each with its own king and isolated state.

### Strengthen trust

- Harden submission validation and anti-cheat checks.
- Expand provenance and freshness guarantees as pack count grows.

### Improve the experience

- Dashboard: result history and per-pack leaderboards.
- Operator tooling: smoother setup and clearer observability for running an instance.

## Proposing a milestone

Open an issue describing the change and the problem it solves. Any change to the
evaluator, screening, or promotion logic should come with tests that prove the new
behavior — see [CONTRIBUTING.md](../CONTRIBUTING.md).
