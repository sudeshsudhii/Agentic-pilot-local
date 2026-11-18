"""In-GUI command listener for Agentic Pilot live design mode.

This file is NOT installed into FreeCAD's Mod directory. It is passed to
`freecad.exe` as a startup script only while a live demo runs, so the listener
exists for the lifetime of that window and nothing persistent is added to the
user's FreeCAD installation.

Security posture
----------------
* The socket binds to 127.0.0.1 only -- never 0.0.0.0 -- so nothing off-machine
  can reach it.
* Every request must carry the shared token from ``~/.pilot/live_token``, which
  is created with fresh random bytes by whoever starts first.
* Received code is executed on the Qt main thread via a queue drained by a
  QTimer. Touching FreeCAD's document or view objects from the socket thread
  crashes the GUI, so the socket thread only ever enqueues.

Protocol: newline-delimited JSON, one request and one response per connection.
    -> {"token": "...", "op": "ping"}
    -> {"token": "...", "op": "exec", "code": "...", "label": "Base plate"}
    -> {"token": "...", "op": "fit"}
    <- {"ok": true, "result": "...", "error": null}
"""

from __future__ import annotations

import json
import os
import socket
import threading
import traceback
from pathlib import Path

HOST = "127.0.0.1"
DEFAULT_PORT = 9875
TOKEN_PATH = Path(os.path.expanduser("~")) / ".pilot" / "live_token"
READY_PATH = Path(os.path.expanduser("~")) / ".pilot" / "live_ready"

# Requests waiting to run on the Qt main thread.
_queue: list[dict] = []
_queue_lock = threading.Lock()

# Shared namespace so successive steps can refer to earlier objects.
_exec_globals: dict = {}


def _log(msg: str) -> None:
    """Print to the FreeCAD report view, prefixed for easy filtering."""
    try:
        import FreeCAD as App

        App.Console.PrintMessage(f"[PilotLive] {msg}\n")
    except Exception:
        print(f"[PilotLive] {msg}")


def _read_token() -> str:
    """Return the shared token, creating one if it does not exist yet."""
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    if TOKEN_PATH.exists():
        tok = TOKEN_PATH.read_text(encoding="utf-8").strip()
        if tok:
            return tok
    import secrets

    tok = secrets.token_hex(32)
    TOKEN_PATH.write_text(tok, encoding="utf-8")
    return tok


# -----------------------------------------------------------------------------
# Main-thread execution
# -----------------------------------------------------------------------------
def _apply_view() -> None:
    """Fit and orient the active 3D view so viewers can follow along."""
    try:
        import FreeCADGui as Gui

        Gui.SendMsgToActiveView("ViewFit")
        try:
            Gui.activeDocument().activeView().viewIsometric()
        except Exception:
            pass
    except Exception as exc:
        _log(f"view update skipped: {exc!r}")


def _run_one(item: dict) -> None:
    """Execute one queued request. Must run on the Qt main thread."""
    op = item.get("op")
    try:
        if op == "ping":
            item["result"] = "pong"
        elif op == "fit":
            _apply_view()
            item["result"] = "fitted"
        elif op == "exec":
            import FreeCAD as App

            code = item.get("code") or ""
            if not _exec_globals:
                _exec_globals.update({"App": App, "FreeCAD": App, "__name__": "__pilot_live__"})
                try:
                    import FreeCADGui as Gui

                    _exec_globals["Gui"] = Gui
                except Exception:
                    pass
            # Generated scripts derive their output dir from __file__. Pointing it at
            # a scratch path lets their save/export calls run harmlessly instead of
            # being stripped out, which would break enclosing if/for blocks.
            if item.get("file_path"):
                _exec_globals["__file__"] = item["file_path"]
            exec(code, _exec_globals)  # noqa: S102 - deliberate: this is the feature
            doc = App.ActiveDocument
            if doc is not None:
                doc.recompute()
            _apply_view()
            try:
                import FreeCADGui as Gui

                Gui.updateGui()
            except Exception:
                pass
            item["result"] = f"ok objects={len(doc.Objects) if doc else 0}"
            _log(f"step applied: {item.get('label') or '(unlabelled)'}")
        else:
            raise ValueError(f"unknown op {op!r}")
        item["ok"] = True
    except Exception:
        item["ok"] = False
        item["error"] = traceback.format_exc(limit=6)
        _log(f"step FAILED: {item.get('label')}\n{item['error']}")
    finally:
        item["done"].set()


def _drain() -> None:
    """QTimer callback: run every pending request on the main thread."""
    with _queue_lock:
        pending, _queue[:] = list(_queue), []
    for item in pending:
        _run_one(item)


# -----------------------------------------------------------------------------
# Socket server
# -----------------------------------------------------------------------------
def _handle(conn: socket.socket, token: str) -> None:
    """Validate one request, hand it to the main thread, and reply."""
    try:
        conn.settimeout(30.0)
        buf = b""
        while b"\n" not in buf:
            chunk = conn.recv(65536)
            if not chunk:
                break
            buf += chunk
            if len(buf) > 8 * 1024 * 1024:
                raise ValueError("request too large")

        req = json.loads(buf.decode("utf-8").strip() or "{}")
        if req.get("token") != token:
            _log("rejected a request with a bad token")
            conn.sendall(b'{"ok":false,"error":"bad token"}\n')
            return

        item = {
            "op": req.get("op"),
            "code": req.get("code"),
            "label": req.get("label"),
            "file_path": req.get("file_path"),
            "done": threading.Event(),
            "ok": False,
            "result": None,
            "error": None,
        }
        with _queue_lock:
            _queue.append(item)

        if not item["done"].wait(timeout=120.0):
            conn.sendall(b'{"ok":false,"error":"timed out on main thread"}\n')
            return

        conn.sendall(
            (
                json.dumps(
                    {"ok": item["ok"], "result": item["result"], "error": item["error"]}
                )
                + "\n"
            ).encode("utf-8")
        )
    except Exception as exc:
        try:
            conn.sendall(
                (json.dumps({"ok": False, "error": repr(exc)}) + "\n").encode("utf-8")
            )
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _serve(port: int, token: str) -> None:
    """Accept loop; runs on a daemon thread and only ever enqueues work."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, port))  # localhost only, by construction
    srv.listen(8)
    _log(f"listening on {HOST}:{port}")
    try:
        READY_PATH.parent.mkdir(parents=True, exist_ok=True)
        READY_PATH.write_text(str(port), encoding="utf-8")
    except Exception:
        pass
    while True:
        try:
            conn, addr = srv.accept()
        except Exception as exc:
            _log(f"accept failed: {exc!r}")
            break
        if addr[0] != HOST:  # defence in depth; the bind already prevents this
            try:
                conn.close()
            finally:
                continue
        threading.Thread(target=_handle, args=(conn, token), daemon=True).start()


def start() -> None:
    """Start the listener and the main-thread drain timer."""
    port = int(os.environ.get("PILOT_LIVE_PORT") or DEFAULT_PORT)
    token = _read_token()

    threading.Thread(target=_serve, args=(port, token), daemon=True).start()

    from PySide import QtCore

    timer = QtCore.QTimer()
    timer.timeout.connect(_drain)
    timer.start(100)
    # Keep a reference alive past this function, or Qt collects the timer.
    globals()["_pilot_live_timer"] = timer
    _log("ready - waiting for Agentic Pilot")


start()
