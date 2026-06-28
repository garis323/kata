# PromptForge

PromptForge is an objective prompt optimization repo for SN74/Gittensor.

It generates repo-specific prompts, evaluates them against pinned repo tasks, compares them with
baseline prompts, and reports whether they improve verified task success.

PromptForge is not a prompt library. The core claim is:

> a generated prompt is only better if it solves more validated repo tasks under the same eval
> conditions.

## Measurement Model

Prompt quality is measured with controlled repo evals:

- same repo snapshot
- same task
- same agent command
- same model and budget
- baseline prompt vs PromptForge-generated prompt

Each task defines objective checks in `checks.sh`. A prompt only improves if it increases verified
task success, not because the wording looks better.

## Registration MVP Interfaces

```bash
promptforge generate --repo <repo-path> --mode contributor
promptforge baseline --repo <repo-path>
promptforge eval --repo <repo-path> --eval-pack evals/<repo-name> --agent-command '<command>'
promptforge report --run <run-id>
```

## Current Benchmark Pack

The first real eval pack is for:

- `e35ventura/taopedia-articles`

It currently includes three pinned contributor tasks:

- `add-delayed-proxies-article`
- `clarify-subnet-77-identity-mapping`
- `clarify-validator-take-vs-stake-weight`

Each task:

- pins the repo commit in `repo_ref.txt`
- limits allowed edit paths
- defines task-specific pass/fail checks
- can be executed through the standard `promptforge eval` flow

## Local Workflow

Generate a repo-specific prompt:

```bash
uv run python -m promptforge generate \
  --repo https://github.com/e35ventura/taopedia-articles.git \
  --mode contributor
```

Validate the task pack:

```bash
uv run python -m promptforge eval-pack validate \
  --path evals/e35ventura__taopedia-articles
```

Run an eval:

```bash
uv run python -m promptforge eval \
  --repo https://github.com/e35ventura/taopedia-articles.git \
  --eval-pack evals/e35ventura__taopedia-articles \
  --mode contributor \
  --agent-command '<your-agent-command>'
```

Render a report:

```bash
uv run python -m promptforge report --run <run-id>
```

## Current Status

The core CLI path is working:

- prompt generation
- baseline generation
- eval-pack scaffolding and validation
- eval execution
- markdown reporting

What still remains before a strong registration submission:

- run the benchmark pack with a real agent command
- produce a real baseline-vs-generated result report
- show that PromptForge improves measured task success, not only that the benchmark exists
