from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from kata.sn60_model_relay import (
    DEFAULT_PINNED_MODEL,
    DEFAULT_UPSTREAM,
    build_server,
    pin_model_in_body,
    resolve_pinned_model,
    resolve_timeout,
    resolve_upstream,
)

# --- pin_model_in_body ------------------------------------------------------


def test_pin_model_overwrites_requested_model() -> None:
    body = json.dumps({"model": "anthropic/claude-opus", "messages": []}).encode()
    out = json.loads(pin_model_in_body(body, "qwen/pinned"))
    assert out["model"] == "qwen/pinned"
    assert out["messages"] == []


def test_pin_model_adds_model_when_absent() -> None:
    body = json.dumps({"messages": [{"role": "user", "content": "hi"}]}).encode()
    out = json.loads(pin_model_in_body(body, "qwen/pinned"))
    assert out["model"] == "qwen/pinned"


def test_pin_model_preserves_other_request_fields() -> None:
    body = json.dumps(
        {"model": "x", "messages": [], "tools": [{"t": 1}], "temperature": 0.9}
    ).encode()
    out = json.loads(pin_model_in_body(body, "qwen/pinned"))
    assert out["model"] == "qwen/pinned"
    assert out["tools"] == [{"t": 1}]
    assert out["temperature"] == 0.9


def test_pin_model_leaves_non_json_untouched() -> None:
    body = b"not json at all"
    assert pin_model_in_body(body, "qwen/pinned") == body


def test_pin_model_leaves_json_non_object_untouched() -> None:
    body = json.dumps([1, 2, 3]).encode()
    assert pin_model_in_body(body, "qwen/pinned") == body


# --- env resolution ---------------------------------------------------------


def test_resolve_upstream_default(monkeypatch) -> None:
    monkeypatch.delenv("KATA_RELAY_UPSTREAM", raising=False)
    assert resolve_upstream() == DEFAULT_UPSTREAM


def test_resolve_upstream_strips_trailing_slash(monkeypatch) -> None:
    monkeypatch.setenv("KATA_RELAY_UPSTREAM", "http://proxy:8000/")
    assert resolve_upstream() == "http://proxy:8000"


def test_resolve_pinned_model_default(monkeypatch) -> None:
    monkeypatch.delenv("KATA_RELAY_PINNED_MODEL", raising=False)
    assert resolve_pinned_model() == DEFAULT_PINNED_MODEL


def test_resolve_pinned_model_override(monkeypatch) -> None:
    monkeypatch.setenv("KATA_RELAY_PINNED_MODEL", "vendor/model")
    assert resolve_pinned_model() == "vendor/model"


def test_resolve_timeout_invalid_falls_back(monkeypatch) -> None:
    monkeypatch.setenv("KATA_RELAY_TIMEOUT", "not-a-number")
    assert resolve_timeout() == 900.0


def test_resolve_timeout_reads_positive_override(monkeypatch) -> None:
    monkeypatch.setenv("KATA_RELAY_TIMEOUT", "12.5")
    assert resolve_timeout() == 12.5


# --- end-to-end over real sockets -------------------------------------------


class _RecordingUpstream(BaseHTTPRequestHandler):
    """Fake Bitsec proxy: records each request and returns a canned response."""

    def _handle(self, method: str) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        self.server.records.append(  # type: ignore[attr-defined]
            {
                "method": method,
                "path": self.path,
                "headers": {k.lower(): v for k, v in self.headers.items()},
                "body": body,
            }
        )
        if self.path.split("?", 1)[0] == "/boom":
            self._reply(502, {"detail": "upstream boom"})
            return
        self._reply(200, {"ok": True, "echo_path": self.path}, extra_header=("X-Upstream", "yes"))

    def _reply(self, status: int, payload: dict, extra_header=None) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        if extra_header is not None:
            self.send_header(*extra_header)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:
        self._handle("POST")

    def do_GET(self) -> None:
        self._handle("GET")

    def log_message(self, *_args) -> None:
        return


@pytest.fixture
def relay_and_upstream(monkeypatch):
    upstream = ThreadingHTTPServer(("127.0.0.1", 0), _RecordingUpstream)
    upstream.records = []  # type: ignore[attr-defined]
    upstream.daemon_threads = True
    threading.Thread(target=upstream.serve_forever, daemon=True).start()
    upstream_port = upstream.server_address[1]

    monkeypatch.setenv("KATA_RELAY_UPSTREAM", f"http://127.0.0.1:{upstream_port}")
    monkeypatch.setenv("KATA_RELAY_PINNED_MODEL", "qwen/pinned-test")

    relay = build_server("127.0.0.1", 0)
    threading.Thread(target=relay.serve_forever, daemon=True).start()
    relay_base = f"http://127.0.0.1:{relay.server_address[1]}"

    try:
        yield relay_base, upstream
    finally:
        relay.shutdown()
        upstream.shutdown()


def _post(url: str, body: bytes, headers: dict[str, str] | None = None):
    request = Request(url, data=body, method="POST", headers=headers or {})
    with urlopen(request, timeout=10) as response:
        return (
            response.status,
            response.read(),
            {k.lower(): v for k, v in response.headers.items()},
        )


def test_inference_model_is_pinned_before_reaching_upstream(relay_and_upstream) -> None:
    base, upstream = relay_and_upstream
    body = json.dumps({"model": "anthropic/claude-opus", "messages": []}).encode()

    status, _, resp_headers = _post(
        base + "/inference",
        body,
        {"Content-Type": "application/json", "x-inference-api-key": "sk-or-abc"},
    )

    assert status == 200
    assert resp_headers.get("x-upstream") == "yes"  # upstream response passed through
    assert len(upstream.records) == 1
    record = upstream.records[0]
    assert record["path"] == "/inference"
    assert json.loads(record["body"])["model"] == "qwen/pinned-test"
    # The agent's inference key rides through untouched to the real proxy.
    assert record["headers"].get("x-inference-api-key") == "sk-or-abc"


def test_inference_query_string_is_still_pinned(relay_and_upstream) -> None:
    base, upstream = relay_and_upstream
    body = json.dumps({"model": "expensive/model", "messages": []}).encode()

    _post(base + "/inference?trace=1", body, {"Content-Type": "application/json"})

    record = upstream.records[0]
    assert record["path"] == "/inference?trace=1"
    assert json.loads(record["body"])["model"] == "qwen/pinned-test"


def test_non_inference_body_passes_through_untouched(relay_and_upstream) -> None:
    base, upstream = relay_and_upstream
    body = json.dumps({"model": "anthropic/claude-opus"}).encode()

    _post(base + "/metrics/job-runs/x/summary/reset", body, {"Content-Type": "application/json"})

    record = upstream.records[0]
    assert record["path"].startswith("/metrics/")
    # Only /inference is rewritten; other endpoints keep their body verbatim.
    assert json.loads(record["body"])["model"] == "anthropic/claude-opus"


def test_health_is_answered_locally_without_touching_upstream(relay_and_upstream) -> None:
    base, upstream = relay_and_upstream
    with urlopen(base + "/healthz", timeout=10) as response:
        payload = json.loads(response.read())

    assert payload["status"] == "ok"
    assert payload["pinned_model"] == "qwen/pinned-test"
    assert upstream.records == []


def test_upstream_http_error_is_passed_through(relay_and_upstream) -> None:
    base, _ = relay_and_upstream
    body = json.dumps({"messages": []}).encode()

    with pytest.raises(HTTPError) as excinfo:
        _post(base + "/boom", body, {"Content-Type": "application/json"})

    assert excinfo.value.code == 502


def test_unreachable_upstream_returns_502(monkeypatch) -> None:
    monkeypatch.setenv("KATA_RELAY_UPSTREAM", "http://127.0.0.1:9")  # nothing listening
    monkeypatch.setenv("KATA_RELAY_PINNED_MODEL", "qwen/pinned-test")
    relay = build_server("127.0.0.1", 0)
    threading.Thread(target=relay.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{relay.server_address[1]}"
    try:
        body = json.dumps({"model": "x", "messages": []}).encode()
        with pytest.raises(HTTPError) as excinfo:
            _post(base + "/inference", body, {"Content-Type": "application/json"})
        assert excinfo.value.code == 502
    finally:
        relay.shutdown()
