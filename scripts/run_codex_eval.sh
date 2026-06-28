#!/usr/bin/env bash
set -euo pipefail

workspace=${PROMPTFORGE_WORKSPACE:?PROMPTFORGE_WORKSPACE is required}
prompt_file=${PROMPTFORGE_PROMPT_FILE:?PROMPTFORGE_PROMPT_FILE is required}
task_file=${PROMPTFORGE_TASK_FILE:?PROMPTFORGE_TASK_FILE is required}
mode=${PROMPTFORGE_MODE:-contributor}
model=${PROMPTFORGE_CODEX_MODEL:-}

if ! command -v codex >/dev/null 2>&1; then
  echo "codex CLI is not installed or not on PATH" >&2
  exit 127
fi

combined_prompt=$(mktemp)
trap 'rm -f "$combined_prompt"' EXIT

cat > "$combined_prompt" <<EOF
You are running inside a PromptForge eval workspace.

Your job is to modify the repository in the current workspace so it satisfies the eval task.

Rules:
- Follow the repo-specific prompt exactly.
- Follow the eval task exactly.
- Keep the diff minimal and task-scoped.
- Do not edit files outside the task scope unless the task explicitly requires it.
- Do not print a long explanation. Apply the changes directly in the workspace.
- Stop once the workspace contains your final solution.

Mode: ${mode}
Workspace: ${workspace}

## Repo-Specific Prompt

EOF

cat "$prompt_file" >> "$combined_prompt"

cat >> "$combined_prompt" <<EOF

## Eval Task

EOF

cat "$task_file" >> "$combined_prompt"

codex_args=(
  exec
  --cd "$workspace"
  --skip-git-repo-check
  --sandbox workspace-write
  --ask-for-approval never
)

if [[ -n "$model" ]]; then
  codex_args+=(--model "$model")
fi

codex "${codex_args[@]}" - < "$combined_prompt"
