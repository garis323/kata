"""SN60 / Bitsec miner agent: a minimal LLM smart-contract auditor.

Contract (docs/submissions.md): a synchronous ``agent_main`` that is callable
with no arguments and returns a report with a top-level ``vulnerabilities`` list.

Standard library only (the sandbox network has no egress except the injected
inference endpoint), and it never raises: any failure returns an empty report,
which is a valid run. An exception would count as an invalid run and block
promotion, so we always fail closed.
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

SOURCE_SUFFIXES = (".sol", ".vy", ".rs", ".cairo", ".move")
SKIP_DIRS = {"node_modules", "lib", "out", "artifacts", "cache", "test", "tests"}
SEARCH_ROOTS = ("/repo", "/project", "/code", "/src", "/app", ".")

MAX_SOURCE_CHARS = 80_000
MAX_FINDINGS = 40
TIMEOUT_SECONDS = 600

PROMPT = (
    "You are a smart-contract security auditor. Review the source below and "
    "report only genuine high or critical severity vulnerabilities. Return ONLY "
    "a JSON array; each item has: title, description, severity ('high' or "
    "'critical'), location (file), line (int or null), function, category, "
    "reasoning. Return [] if there are none.\n\nSOURCE:\n"
)


def agent_main(project_dir=None, inference_api=None) -> dict:
    try:
        findings = _audit(project_dir, inference_api)
    except Exception:
        findings = []
    return {"vulnerabilities": findings}


def _audit(project_dir, inference_api) -> list:
    endpoint = (inference_api or os.environ.get("INFERENCE_API") or "").strip().rstrip("/")
    source = _read_sources(project_dir)
    if not endpoint or not source:
        return []
    content = _ask_model(endpoint, PROMPT + source)
    return _normalize(_parse(content))


def _read_sources(project_dir) -> str:
    root = _find_root(project_dir)
    if root is None:
        return ""
    chunks, total = [], 0
    for path in _iter_sources(root):
        text = _read(path)
        if not text.strip():
            continue
        if total + len(text) > MAX_SOURCE_CHARS:
            break
        chunks.append(f"\n===== {path.name} =====\n{text}")
        total += len(text)
    return "".join(chunks)


def _find_root(project_dir):
    explicit = (project_dir or os.environ.get("PROJECT_DIR") or "").strip()
    if explicit and Path(explicit).is_dir():
        return Path(explicit)
    for raw in SEARCH_ROOTS:
        candidate = Path(raw)
        if candidate.is_dir() and any(True for _ in _iter_sources(candidate, limit=1)):
            return candidate
    return None


def _iter_sources(root, limit=None):
    count = 0
    try:
        walker = os.walk(root)
    except OSError:
        return
    for current, dirs, files in walker:
        dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS and not d.startswith(".")]
        for name in sorted(files):
            if name.endswith(SOURCE_SUFFIXES):
                yield Path(current) / name
                count += 1
                if limit and count >= limit:
                    return


def _read(path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _ask_model(endpoint, prompt):
    body = json.dumps(
        {
            "model": "default",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4000,
            "stream": False,
        }
    ).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    key = (os.environ.get("INFERENCE_API_KEY") or "").strip()
    if key:
        # The Bitsec inference proxy authenticates on this header, not on an
        # Authorization: Bearer header. Using the wrong one gets every request
        # rejected, so the agent reports nothing and loses every duel.
        headers["x-inference-api-key"] = key
    for path in ("/inference", "/v1/chat/completions"):
        request = urllib.request.Request(endpoint + path, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                data = json.loads(response.read().decode("utf-8", errors="replace"))
        except Exception:
            continue
        content = _content(data)
        if content:
            return content
    return ""


def _content(data):
    if not isinstance(data, dict):
        return ""
    choices = data.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        message = choices[0].get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return message["content"]
    for key in ("content", "response", "output"):
        if isinstance(data.get(key), str):
            return data[key]
    return ""


def _parse(content) -> list:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end > start:
        text = text[start : end + 1]
    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        return []
    return parsed if isinstance(parsed, list) else []


def _normalize(items) -> list:
    out = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = _str(item, "title", "name", "summary")
        description = _str(item, "description", "detail", "reasoning")
        if not title and not description:
            continue
        record = {
            "title": title or description[:80],
            "description": description or title,
            "severity": _severity(_str(item, "severity", "impact")),
        }
        location = _str(item, "location", "file", "path")
        if location:
            record["location"] = location
            record["file"] = location
        for field in ("function", "category", "reasoning"):
            value = _str(item, field)
            if value:
                record[field] = value
        line = item.get("line")
        if isinstance(line, int) and not isinstance(line, bool):
            record["line"] = line
        out.append(record)
        if len(out) >= MAX_FINDINGS:
            break
    return out


def _str(item, *keys) -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _severity(value) -> str:
    lowered = value.lower()
    if "crit" in lowered:
        return "critical"
    return "high"


if __name__ == "__main__":
    print(json.dumps(agent_main()))
