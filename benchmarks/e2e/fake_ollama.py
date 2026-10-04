"""A stand-in for the Ollama HTTP API that returns fixed answers. NOT a model.

It exists only to smoke-test the harness and the no-egress test without model weights.
Episodes run against it say nothing about the agent and must never be reported as results.

Policy: the intent names the first URL in the request; plans have one step; the planner always
claims `complete`; the self-check always says done.
"""

from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = "scripted-stub:latest"


def _reply(system: str, user: str) -> dict:
    if '"done"' in system:
        return {"done": True, "reason": "scripted"}
    if '"task_summary"' in system:
        return {"task_summary": user[:80], "total_steps": 1, "current_step_index": 1,
                "steps": [{"step_index": 1, "description": "do the task", "action_type": "interact"}]}
    if '"risk_level"' in system:
        m = re.search(r"https?://[^\s'\"]+", user)
        return {"action": "navigate", "site": m.group(0) if m else "unknown", "risk_level": "low",
                "confidence": 1.0, "reasoning": "scripted"}
    if '"action_type"' in system:
        return {"action_type": "complete", "reasoning": "scripted stub claims completion"}
    return {}


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _json(self, obj: dict):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/tags"):
            return self._json({"models": [{"model": MODEL, "name": MODEL, "size": 0, "digest": "stub"}]})
        if self.path.startswith("/api/version"):
            return self._json({"version": "stub"})
        self._json({})

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        if self.path.startswith("/api/chat"):
            msgs = req.get("messages", [])
            system = next((m["content"] for m in msgs if m.get("role") == "system"), "")
            user = next((m["content"] for m in msgs if m.get("role") == "user"), "")
            return self._json({"model": req.get("model", MODEL), "done": True,
                               "message": {"role": "assistant", "content": json.dumps(_reply(system, user))},
                               "prompt_eval_count": len((system + user).split()), "eval_count": 10})
        if self.path.startswith("/api/show"):
            return self._json({"details": {}, "model_info": {}})
        self._json({})


class FakeOllama:
    def __init__(self, port: int = 0):
        self.httpd = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        self._t = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self):
        self._t.start()
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()


if __name__ == "__main__":
    import sys

    with FakeOllama(int(sys.argv[1]) if len(sys.argv) > 1 else 11435) as f:
        print(f"scripted stub at {f.url}")
        threading.Event().wait()
