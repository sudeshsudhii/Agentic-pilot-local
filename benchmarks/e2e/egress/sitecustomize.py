"""Loaded automatically when this directory is on PYTHONPATH: logs every outbound socket
connection the Python process attempts, to PILOT_EGRESS_LOG (one JSON line per attempt)."""

import json
import os
import socket

_log = os.environ.get("PILOT_EGRESS_LOG")
if _log:
    _orig_connect = socket.socket.connect
    _orig_connect_ex = socket.socket.connect_ex

    def _record(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            with open(_log, "a") as f:
                f.write(json.dumps({"pid": os.getpid(), "host": str(address[0]), "port": address[1]}) + "\n")

    def connect(self, address):
        _record(self, address)
        return _orig_connect(self, address)

    def connect_ex(self, address):
        _record(self, address)
        return _orig_connect_ex(self, address)

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex
