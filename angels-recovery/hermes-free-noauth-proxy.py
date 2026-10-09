#!/usr/bin/env python3
"""Synthetic one-shot local adapter for a credentialless public :free endpoint.

Public GitHub Actions runner only. No ANGELS secrets, no company work, no production.
Hermes' custom provider supplies a placeholder Authorization token; DO NOT forward it.
This script does not claim that usage is perpetually free or that Hermes is deployed.
"""
from __future__ import annotations
import hashlib
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ALLOWED_MODELS = frozenset({
    "cohere/north-mini-code:free",
    "nvidia/nemotron-3.5-lightning:free",
})
UPSTREAM = "https://api.kilo.ai/api/gateway/chat/completions"
MAX_BYTES = 160_000


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("HTTP", fmt % args, flush=True)

    def send_json(self, status: int, body: object):
        data = json.dumps(body, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.rstrip("/") in ("/v1/models", "/models"):
            self.send_json(200, {"object":"list","data":[{"id":m,"object":"model","owned_by":"ANGELS public free relay test"} for m in sorted(ALLOWED_MODELS)]})
        elif self.path == "/health":
            self.send_json(200, {"ok": True, "no_paid_fallback": True})
        else:
            self.send_json(404, {"error":{"message":"unknown_path"}})

    def do_POST(self):
        if self.path not in ("/v1/chat/completions", "/chat/completions"):
            return self.send_json(404, {"error":{"message":"unsupported_endpoint"}})
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length < 2 or length > MAX_BYTES:
            return self.send_json(413, {"error":{"message":"oversize_or_empty_request"}})
        try:
            req = json.loads(self.rfile.read(length))
            if not isinstance(req, dict):
                raise ValueError("request_not_object")
        except (ValueError, UnicodeDecodeError):
            return self.send_json(400, {"error":{"message":"invalid_json"}})
        model = req.get("model")
        if model not in ALLOWED_MODELS:
            return self.send_json(403, {"error":{"message":"unapproved_or_paid_model"}})
        if not isinstance(req.get("messages"), list) or not req["messages"]:
            return self.send_json(400, {"error":{"message":"messages_required"}})
        if req.get("stream") not in (False, None):
            return self.send_json(400, {"error":{"message":"streaming_denied"}})
        req["stream"] = False
        req["max_tokens"] = min(max(int(req.get("max_tokens") or 128), 1), 768)
        wire = json.dumps(req, separators=(",", ":")).encode("utf-8")
        try:
            # Deliberately NO Authorization header. Credentials from Hermes are NEVER relayed.
            upstream_req = Request(
                UPSTREAM, data=wire, method="POST",
                headers={"Content-Type":"application/json", "Accept":"application/json"},
            )
            with urlopen(upstream_req, timeout=45) as response:
                status = response.status
                raw = response.read(500_000)
            response_data = json.loads(raw)
            cost = response_data.get("usage", {}).get("cost", None)
            if cost is None or float(cost) != 0:
                print(json.dumps({"event":"UNVERIFIED_OR_NONZERO_COST","model":model,"cost":str(cost)}), flush=True)
                return self.send_json(502, {"error":{"message":"nonzero_or_unverified_cost"}})
            print(json.dumps({"event":"FREE_INFERENCE_RECEIPT","model":model,"http":status,"cost":0,"request_sha256":hashlib.sha256(wire).hexdigest()}), flush=True)
            self.send_json(status, response_data)
        except HTTPError as e:
            print(json.dumps({"event":"UPSTREAM_HTTP_FAILURE","model":model,"http":e.code}), flush=True)
            self.send_json(502, {"error":{"message":"upstream_unavailable","upstream_http":e.code}})
        except (URLError, TimeoutError, OSError, ValueError, KeyError, TypeError) as e:
            print(json.dumps({"event":"UPSTREAM_FAILURE","model":model,"reason":type(e).__name__}), flush=True)
            self.send_json(502, {"error":{"message":"upstream_or_cost_verification_failed"}})


if __name__ == "__main__":
    if os.environ.get("GITHUB_REPOSITORY") != "visionastro48-dev/shaddow-synthetic-host-gate-20261001":
        raise SystemExit("BLOCKED: disposable public ANGELS test runner only")
    port = int(os.environ.get("ANGELS_HERMES_PROXY_PORT", "8765"))
    assert 1024 <= port <= 65535
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(json.dumps({"event":"BOUNDED_LOCAL_FREE_PROXY_READY","bind":"127.0.0.1","port":port}), flush=True)
    server.serve_forever()
