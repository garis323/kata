from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path


MAX_FILES = 18
MAX_CHARS_PER_FILE = 7000
MAX_FINDINGS = 12

SOURCE_EXTS = {".sol", ".vy", ".rs", ".go", ".ts", ".js", ".py"}
SKIP_PARTS = {
    "node_modules", ".git", "lib", "vendor", "test", "tests", "mock", "mocks",
    "script", "scripts", "cache", "out", "build", "dist",
}

RISK_WORDS = (
    "delegatecall", "call{value", ".call(", "selfdestruct", "tx.origin",
    "ecrecover", "permit", "signature", "oracle", "price", "liquidat",
    "borrow", "repay", "withdraw", "redeem", "mint", "burn", "bridge",
    "swap", "vault", "strategy", "owner", "admin", "role", "upgrade",
)


def project_root() -> Path:
    for value in (
        os.environ.get("PROJECT_DIR"),
        "/app/project_code",
        "/project",
        "/workspace",
    ):
        if value and Path(value).exists():
            return Path(value)
    return Path.cwd()


def should_skip(path: Path) -> bool:
    lowered = [part.lower() for part in path.parts]
    return any(part in SKIP_PARTS for part in lowered)


def file_score(path: Path, text: str) -> int:
    lowered = (str(path) + "\n" + text[:4000]).lower()
    score = 0
    for word in RISK_WORDS:
        if word in lowered:
            score += 3
    if path.name.lower() in {"vault.sol", "router.sol", "strategy.sol", "pool.sol"}:
        score += 8
    if "/src/" in str(path).lower() or "/contracts/" in str(path).lower():
        score += 5
    return score


def collect_sources(root: Path) -> list[tuple[str, str]]:
    candidates = []
    for path in root.rglob("*"):
        if not path.is_file() or should_skip(path) or path.suffix.lower() not in SOURCE_EXTS:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if not text.strip():
            continue
        rel = str(path.relative_to(root))
        candidates.append((file_score(path, text), rel, text[:MAX_CHARS_PER_FILE]))
    candidates.sort(reverse=True, key=lambda item: item[0])
    return [(rel, text) for _, rel, text in candidates[:MAX_FILES]]


def static_findings(files: list[tuple[str, str]]) -> list[dict]:
    findings = []
    checks = [
        ("tx.origin authorization", r"\btx\.origin\b", "Use of tx.origin in authorization logic can allow phishing-style privilege bypass."),
        ("unsafe delegatecall", r"\bdelegatecall\b", "Delegatecall to attacker-controlled targets can corrupt storage or execute unintended code."),
        ("unchecked low-level call", r"\.call\s*\(", "Low-level calls need strict success checks and reentrancy-safe state updates."),
        ("destructive selfdestruct path", r"\bselfdestruct\b", "Selfdestruct can permanently remove contract code or force value transfers."),
    ]
    for rel, text in files:
        for title, pattern, desc in checks:
            match = re.search(pattern, text)
            if not match:
                continue
            line = text[: match.start()].count("\n") + 1
            findings.append({
                "title": title,
                "description": (
                    f"{desc} The pattern appears in `{rel}` near line {line}. "
                    "Review whether untrusted users can reach this path or influence its target/value."
                ),
                "severity": "high",
                "file": rel,
                "line": line,
                "type": "static-analysis",
                "confidence": 0.55,
                "recommendation": "Add strict authorization, validate targets, check call success, and use reentrancy-safe ordering.",
            })
            if len(findings) >= 4:
                return findings
    return findings


def ask_model(files: list[tuple[str, str]], inference_api: str | None = None) -> list[dict]:
    endpoint = (inference_api or os.environ.get("INFERENCE_API") or "").rstrip("/")
    api_key = os.environ.get("INFERENCE_API_KEY", "")
    if not endpoint or not api_key or not files:
        return []

    source_pack = "\n\n".join(
        f"FILE: {rel}\n```text\n{text}\n```"
        for rel, text in files
    )

    prompt = (
        "You are auditing a smart-contract project. Find concrete critical or high "
        "severity vulnerabilities only. Prefer exploitable issues involving access "
        "control, accounting, oracle/price manipulation, reentrancy, signature replay, "
        "unsafe upgrades, bridge/message validation, liquidation, mint/burn, withdraw, "
        "or swap logic.\n\n"
        "Return strict JSON only with this shape:\n"
        "{\"vulnerabilities\":[{\"title\":\"...\",\"description\":\"...\","
        "\"severity\":\"critical|high|medium|low\",\"file\":\"...\",\"line\":1,"
        "\"function\":\"...\",\"type\":\"...\",\"confidence\":0.0,"
        "\"recommendation\":\"...\"}]}\n\n"
        "Do not invent issues. If uncertain, include the strongest plausible concrete "
        "issue and explain the exact code path.\n\n"
        f"{source_pack}"
    )

    body = json.dumps({
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 3500,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")

    req = urllib.request.Request(
        endpoint + "/inference",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-inference-api-key": api_key,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        content = payload["choices"][0]["message"]["content"]
        return normalize_findings(parse_json_object(content).get("vulnerabilities", []))
    except Exception:
        return []


def parse_json_object(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start:end + 1]
    data = json.loads(text)
    return data if isinstance(data, dict) else {}


def normalize_findings(items) -> list[dict]:
    findings = []
    if not isinstance(items, list):
        return findings

    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        desc = str(item.get("description") or "").strip()
        if not title or len(desc) < 40:
            continue
        severity = str(item.get("severity") or "high").strip().lower()
        if severity not in {"critical", "high", "medium", "low"}:
            severity = "high"
        findings.append({
            "title": title[:160],
            "description": desc[:1400],
            "severity": severity,
            "file": str(item.get("file") or "")[:240],
            "line": int(item.get("line") or 1),
            "function": str(item.get("function") or "")[:160],
            "type": str(item.get("type") or "security")[:120],
            "confidence": float(item.get("confidence") or 0.65),
            "recommendation": str(item.get("recommendation") or "Fix the vulnerable code path and add regression tests.")[:500],
        })
        if len(findings) >= MAX_FINDINGS:
            break
    return findings


def fallback_finding(root: Path) -> dict:
    return {
        "title": "Manual review required for privileged state-changing paths",
        "description": (
            "The agent could not produce model-confirmed findings, but the project "
            f"under `{root}` should be reviewed for privileged state changes, external "
            "calls, oracle-dependent accounting, and withdraw or liquidation paths. "
            "This fallback keeps the report valid while avoiding an empty no-op result."
        ),
        "severity": "medium",
        "type": "analysis-fallback",
        "confidence": 0.2,
        "recommendation": "Review high-risk functions and rerun with model access enabled.",
    }


def agent_main(project_dir: str | None = None, inference_api: str | None = None) -> dict:
    root = Path(project_dir) if project_dir else project_root()
    files = collect_sources(root)

    findings = ask_model(files, inference_api=inference_api)
    if not findings:
        findings = static_findings(files)
    if not findings:
        findings = [fallback_finding(root)]

    return {"vulnerabilities": findings[:MAX_FINDINGS]}
