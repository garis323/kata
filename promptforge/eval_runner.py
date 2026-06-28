from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from promptforge.baseline import generate_baseline_prompt_from_repository
from promptforge.config import resolve_registry_url
from promptforge.eval_pack import discover_eval_pack_tasks
from promptforge.generator import generate_prompt_from_repository
from promptforge.repository import resolve_repository

IGNORED_COPY_DIRS = (
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
)


@dataclass(frozen=True)
class VariantResult:
    name: str
    prompt_path: str
    workspace: str
    agent_stdout: str
    agent_stderr: str
    checks_stdout: str
    checks_stderr: str
    agent_exit_code: int
    checks_exit_code: int
    success: bool


@dataclass(frozen=True)
class TaskRunSummary:
    task_id: str
    task_path: str
    task_repo_ref: str
    variants: list[VariantResult]


@dataclass(frozen=True)
class EvalRunSummary:
    run_id: str
    requested_repo_ref: str
    eval_pack: str
    mode: str
    registry_url: str | None
    agent_command: str
    created_at: str
    tasks: list[TaskRunSummary]


def run_eval(
    *,
    repo_ref: str,
    eval_pack_path: str,
    mode: str,
    agent_command: str,
    registry_url: str | None = None,
    output_root: str | None = None,
) -> EvalRunSummary:
    validations = discover_eval_pack_tasks(eval_pack_path)
    invalid = [result for result in validations if not result.is_valid]
    if invalid:
        invalid_names = ", ".join(result.root.name for result in invalid)
        raise ValueError(
            "Eval pack is invalid. Run `promptforge eval-pack validate` first. "
            f"Invalid task directories: {invalid_names}"
        )

    resolved_registry_url = resolve_registry_url(registry_url)
    task_names = [result.root.name for result in validations]
    run_id = build_run_id(validations[0].root.parent.name if len(task_names) > 1 else task_names[0])
    runs_root = Path(output_root) if output_root else Path("runs")
    run_root = runs_root / run_id
    run_root.mkdir(parents=True, exist_ok=False)

    task_summaries: list[TaskRunSummary] = []
    for validation in validations:
        task_root = validation.root
        task_run_root = run_root / "tasks" / task_root.name
        task_run_root.mkdir(parents=True, exist_ok=False)

        task_snapshot = task_run_root / "eval_pack"
        shutil.copytree(task_root, task_snapshot)

        task_repo_ref = read_task_repo_ref(task_snapshot / "repo_ref.txt", fallback=repo_ref)
        with resolve_repository(task_repo_ref) as repo:
            repo_snapshot = task_run_root / "repo_snapshot"
            copy_repository(repo.root, repo_snapshot)
            variants = [
                run_variant(
                    variant_name="baseline",
                    prompt_text=generate_baseline_prompt_from_repository(repo, mode),
                    variant_root=task_run_root / "baseline",
                    repo_snapshot=repo_snapshot,
                    eval_pack_root=task_snapshot,
                    repo_ref=task_repo_ref,
                    mode=mode,
                    agent_command=agent_command,
                ),
                run_variant(
                    variant_name="generated",
                    prompt_text=generate_prompt_from_repository(
                        repo,
                        mode,
                        resolved_registry_url,
                    ),
                    variant_root=task_run_root / "generated",
                    repo_snapshot=repo_snapshot,
                    eval_pack_root=task_snapshot,
                    repo_ref=task_repo_ref,
                    mode=mode,
                    agent_command=agent_command,
                ),
            ]

        task_summaries.append(
            TaskRunSummary(
                task_id=task_root.name,
                task_path=str(task_root),
                task_repo_ref=task_repo_ref,
                variants=variants,
            )
        )

    summary = EvalRunSummary(
        run_id=run_id,
        requested_repo_ref=repo_ref,
        eval_pack=str(Path(eval_pack_path).expanduser().resolve()),
        mode=mode,
        registry_url=resolved_registry_url,
        agent_command=agent_command,
        created_at=datetime.now(UTC).isoformat(),
        tasks=task_summaries,
    )
    write_summary(run_root / "run_summary.json", summary)
    return summary


def run_variant(
    *,
    variant_name: str,
    prompt_text: str,
    variant_root: Path,
    repo_snapshot: Path,
    eval_pack_root: Path,
    repo_ref: str,
    mode: str,
    agent_command: str,
) -> VariantResult:
    workspace = variant_root / "workspace"
    shutil.copytree(repo_snapshot, workspace)

    prompt_path = variant_root / "prompt.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(prompt_text + "\n", encoding="utf-8")

    agent_stdout = variant_root / "agent.stdout.txt"
    agent_stderr = variant_root / "agent.stderr.txt"
    checks_stdout = variant_root / "checks.stdout.txt"
    checks_stderr = variant_root / "checks.stderr.txt"

    agent_exit_code = run_agent_command(
        command=agent_command,
        workspace=workspace,
        prompt_path=prompt_path,
        eval_pack_root=eval_pack_root,
        repo_snapshot=repo_snapshot,
        mode=mode,
        repo_ref=repo_ref,
        stdout_path=agent_stdout,
        stderr_path=agent_stderr,
    )
    checks_exit_code = run_checks(
        checks_path=eval_pack_root / "checks.sh",
        workspace=workspace,
        prompt_path=prompt_path,
        eval_pack_root=eval_pack_root,
        repo_snapshot=repo_snapshot,
        mode=mode,
        repo_ref=repo_ref,
        stdout_path=checks_stdout,
        stderr_path=checks_stderr,
    )
    return VariantResult(
        name=variant_name,
        prompt_path=str(prompt_path),
        workspace=str(workspace),
        agent_stdout=str(agent_stdout),
        agent_stderr=str(agent_stderr),
        checks_stdout=str(checks_stdout),
        checks_stderr=str(checks_stderr),
        agent_exit_code=agent_exit_code,
        checks_exit_code=checks_exit_code,
        success=agent_exit_code == 0 and checks_exit_code == 0,
    )


def run_agent_command(
    *,
    command: str,
    workspace: Path,
    prompt_path: Path,
    eval_pack_root: Path,
    repo_snapshot: Path,
    mode: str,
    repo_ref: str,
    stdout_path: Path,
    stderr_path: Path,
) -> int:
    env = build_env(
        workspace=workspace,
        prompt_path=prompt_path,
        eval_pack_root=eval_pack_root,
        repo_snapshot=repo_snapshot,
        mode=mode,
        repo_ref=repo_ref,
    )
    return run_shell_command(command, workspace, env, stdout_path, stderr_path)


def run_checks(
    *,
    checks_path: Path,
    workspace: Path,
    prompt_path: Path,
    eval_pack_root: Path,
    repo_snapshot: Path,
    mode: str,
    repo_ref: str,
    stdout_path: Path,
    stderr_path: Path,
) -> int:
    env = build_env(
        workspace=workspace,
        prompt_path=prompt_path,
        eval_pack_root=eval_pack_root,
        repo_snapshot=repo_snapshot,
        mode=mode,
        repo_ref=repo_ref,
    )
    return run_process(
        ["bash", str(checks_path.resolve())],
        workspace,
        env,
        stdout_path,
        stderr_path,
    )


def run_shell_command(
    command: str,
    cwd: Path,
    env: dict[str, str],
    stdout_path: Path,
    stderr_path: Path,
) -> int:
    return run_process(["bash", "-lc", command], cwd, env, stdout_path, stderr_path)


def run_process(
    command: list[str],
    cwd: Path,
    env: dict[str, str],
    stdout_path: Path,
    stderr_path: Path,
) -> int:
    with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open(
        "w", encoding="utf-8"
    ) as stderr_file:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            env=env,
            stdout=stdout_file,
            stderr=stderr_file,
            text=True,
            check=False,
        )
    return completed.returncode


def build_env(
    *,
    workspace: Path,
    prompt_path: Path,
    eval_pack_root: Path,
    repo_snapshot: Path,
    mode: str,
    repo_ref: str,
) -> dict[str, str]:
    env = dict(os.environ)
    env["PROMPTFORGE_WORKSPACE"] = str(workspace.resolve())
    env["PROMPTFORGE_PROMPT_FILE"] = str(prompt_path.resolve())
    env["PROMPTFORGE_MODE"] = mode
    env["PROMPTFORGE_REPO_REF"] = repo_ref
    env["PROMPTFORGE_REPO_SNAPSHOT"] = str(repo_snapshot.resolve())
    env["PROMPTFORGE_EVAL_TASK_DIR"] = str(eval_pack_root.resolve())
    env["PROMPTFORGE_TASK_FILE"] = str((eval_pack_root / "task.md").resolve())
    env["PROMPTFORGE_RUBRIC_FILE"] = str((eval_pack_root / "rubric.md").resolve())
    env["PROMPTFORGE_ALLOWED_PATHS_FILE"] = str((eval_pack_root / "allowed_paths.txt").resolve())
    env["PROMPTFORGE_FORBIDDEN_PATHS_FILE"] = str(
        (eval_pack_root / "forbidden_paths.txt").resolve()
    )
    return env


def read_task_repo_ref(path: Path, *, fallback: str) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        return stripped
    return fallback


def build_run_id(task_id: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{task_id}-{timestamp}"


def copy_repository(source: Path, target: Path) -> None:
    shutil.copytree(source, target, ignore=shutil.ignore_patterns(*IGNORED_COPY_DIRS))


def write_summary(path: Path, summary: EvalRunSummary) -> None:
    path.write_text(json.dumps(asdict(summary), indent=2) + "\n", encoding="utf-8")
