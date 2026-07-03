"""SN60 model-pinning inference relay.

Untrusted miner agents run inside an internet-blocked Docker network, so the only
way they can reach an LLM is through the inference endpoint Kata hands them via
``KATA_SN60_INFERENCE_API``. Point that variable at this relay and it forces every
inference request onto a single pinned model before forwarding to the real Bitsec
proxy. That protects the validator two ways at once:

* **Cost** — a miner cannot spend the validator's inference budget on a costlier
  model; the model is overwritten no matter what the agent's code asked for.
* **Fairness** — king and candidate are guaranteed to duel on the same model.

Enforcement happens on the actual API call, not by scanning source, so runtime or
obfuscated model strings cannot bypass it: the internal network gives the agent no
other route to a provider. Every non-inference request (metrics, health) is passed
through untouched — the relay only ever rewrites the ``model`` field of a
``POST /inference`` body.

The module has no third-party dependencies (kata ships none) and is meant to run as
a small sidecar container on the agent network:

    docker run --rm --name kata_model_relay --network bitsec-net \\
        -e KATA_RELAY_UPSTREAM=http://bitsec_proxy:8000 \\
        -e KATA_RELAY_PINNED_MODEL=qwen/qwen3.6-35b-a3b \\
        kata-sn60-model-relay

Then start the validator with ``KATA_SN60_INFERENCE_API=http://kata_model_relay:8000``.
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_UPSTREAM = "http://bitsec_proxy:8000"
DEFAULT_PINNED_MODEL = "qwen/qwen3.6-35b-a3b"
DEFAULT_TIMEOUT_SECONDS = 900

# Only this path carries a model to overwrite; everything else is forwarded as-is.
INFERENCE_PATH = "/inference"
# Answered by the relay itself so operators can prove the process is up without
# depending on the upstream proxy.
HEALTH_PATH = "/healthz"

# Hop-by-hop headers must never be forwarded (RFC 7230 section 6.1); Host and
# Content-Length are recomputed by the outbound request instead of copied.
_SKIP_REQUEST_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}
_SKIP_RESPONSE_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-length",
}


def resolve_upstream() -> str:
    """Base URL of the real inference proxy the relay forwards to."""
    value = os.environ.get("KATA_RELAY_UPSTREAM")
    if value and value.strip():
        return value.strip().rstrip("/")
    return DEFAULT_UPSTREAM


def resolve_pinned_model() -> str:
    """The single model every inference request is forced onto."""
    value = os.environ.get("KATA_RELAY_PINNED_MODEL")
    if value and value.strip():
        return value.strip()
    return DEFAULT_PINNED_MODEL


def resolve_timeout() -> float:
    """Upstream request timeout; kept high because agent inference can be slow."""
    value = os.environ.get("KATA_RELAY_TIMEOUT")
    if value and value.strip():
        try:
            parsed = float(value.strip())
        except ValueError:
            return float(DEFAULT_TIMEOUT_SECONDS)
        if parsed > 0:
            return parsed
    return float(DEFAULT_TIMEOUT_SECONDS)


def pin_model_in_body(body: bytes, model: str) -> bytes:
    """Force the OpenAI-compatible request body onto ``model``.

    A body we cannot read as a JSON object is returned untouched: the upstream
    proxy is the authority on request validity, so the relay's only job is to
    overwrite the model field when one could exist, never to reject traffic.
    """
    try:
        payload = json.loads(body)
    except (ValueError, TypeError):
        return body
    if not isinstance(payload, dict):
        return body
    payload["model"] = model
    return json.dumps(payload).encode("utf-8")


class ModelPinningRelayHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    # -- request entry points -------------------------------------------------
    def do_GET(self) -> None:
        if self._path_without_query() == HEALTH_PATH:
            self._send_json(200, {"status": "ok", "pinned_model": resolve_pinned_model()})
            return
        self._forward("GET")

    def do_POST(self) -> None:
        self._forward("POST")

    # -- forwarding -----------------------------------------------------------
    def _forward(self, method: str) -> None:
        body = self._read_body()
        if method == "POST" and self._path_without_query() == INFERENCE_PATH:
            body = pin_model_in_body(body, resolve_pinned_model())

        headers = {
            key: value
            for key, value in self.headers.items()
            if key.lower() not in _SKIP_REQUEST_HEADERS
        }
        url = resolve_upstream() + self.path
        request = Request(
            url,
            data=body if body else None,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=resolve_timeout()) as response:
                self._relay_response(response.status, response.headers.items(), response.read())
        except HTTPError as error:
            # Upstream returned a real HTTP error (4xx/5xx); pass it through verbatim.
            self._relay_response(error.code, error.headers.items(), error.read())
        except URLError as error:
            self._send_json(502, {"detail": f"relay could not reach upstream: {error.reason}"})

    def _relay_response(self, status: int, header_items, body: bytes) -> None:
        self.send_response(status)
        for key, value in header_items:
            if key.lower() in _SKIP_RESPONSE_HEADERS:
                continue
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    # -- helpers --------------------------------------------------------------
    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(length) if length > 0 else b""

    def _path_without_query(self) -> str:
        return self.path.split("?", 1)[0]

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args) -> None:
        # Silence per-request logging; inference bodies could be large/noisy.
        return


def build_server(host: str, port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), ModelPinningRelayHandler)
    server.daemon_threads = True
    return server


def main() -> int:
    host = os.environ.get("KATA_RELAY_HOST", "0.0.0.0")
    port = int(os.environ.get("KATA_RELAY_PORT", "8000"))
    server = build_server(host, port)
    print(
        f"SN60 model-pinning relay listening on {host}:{port} -> {resolve_upstream()} "
        f"(model pinned to {resolve_pinned_model()})",
        file=sys.stderr,
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
