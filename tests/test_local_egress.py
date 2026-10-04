"""Evidence for the privacy property: model traffic and the agent's own traffic stay on this machine.

1. A non-loopback model endpoint is refused before any connection is made.
2. Chroma stores are created with telemetry disabled.
3. A full agent episode (real LangGraph loop, real Chromium, local sites, a scripted stand-in for
   Ollama on loopback) opens no non-loopback socket from the agent process, and the browser
   requests no non-loopback URL.

The stand-in model is not a language model; this test checks where traffic goes, not task success.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from backend.security.locality import NonLocalEndpointError, is_loopback_url, require_local_endpoint

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("url", ["http://127.0.0.1:11434", "http://localhost:11434", "http://[::1]:11434",
                                 "http://127.0.0.2:8080", "localhost:11434", "http://LOCALHOST."])
def test_loopback_urls_are_local(url):
    assert is_loopback_url(url)


@pytest.mark.parametrize("url", ["http://192.168.1.20:11434", "http://10.0.0.5:11434", "https://api.example.com",
                                 "http://example.com/?h=127.0.0.1", "http://127.0.0.1.example.com", "http://localhost.evil.example:11434", "http://0.0.0.0:11434", ""])
def test_other_urls_are_not_local(url):
    assert not is_loopback_url(url)


def test_remote_endpoint_refused_unless_allowed():
    with pytest.raises(NonLocalEndpointError):
        require_local_endpoint("http://192.168.1.20:11434", allow_remote=False)
    require_local_endpoint("http://192.168.1.20:11434", allow_remote=True)
    require_local_endpoint("http://127.0.0.1:11434", allow_remote=False)


def test_gateway_refuses_remote_endpoint_before_connecting():
    from backend.config import PilotConfig
    from backend.llm.gateway import OllamaGateway

    gw = OllamaGateway(PilotConfig(ollama_base_url="http://203.0.113.7:11434"))
    with pytest.raises(NonLocalEndpointError):
        gw._client_instance()


def test_chroma_telemetry_disabled(tmp_path):
    chromadb = pytest.importorskip("chromadb")
    from backend.security.locality import local_chroma_settings

    client = chromadb.PersistentClient(path=str(tmp_path), settings=local_chroma_settings())
    assert client.get_settings().anonymized_telemetry is False


@pytest.mark.timeout(600)
def test_agent_episode_opens_no_non_loopback_connection(tmp_path):
    pytest.importorskip("langgraph")
    pytest.importorskip("playwright")
    from benchmarks.e2e.fake_ollama import FakeOllama

    egress_log = tmp_path / "egress.jsonl"
    with FakeOllama() as fake:
        env = {**os.environ,
               "PYTHONPATH": os.pathsep.join([str(ROOT / "benchmarks" / "e2e" / "egress"), str(ROOT)]),
               "PILOT_EGRESS_LOG": str(egress_log),
               "PILOT_OLLAMA_BASE_URL": fake.url, "PILOT_OLLAMA_MODEL": "scripted-stub:latest",
               "PILOT_ENABLE_MEMORY": "false", "PILOT_ENABLE_RAG": "false"}
        subprocess.run([sys.executable, "-m", "benchmarks.e2e.run_e2e", "--split", "dev", "--tasks", "D01,D03,D05",
                        "--trials", "1", "--configs", "full", "--out", str(tmp_path / "run"), "--episode-timeout", "120"],
                       cwd=ROOT, env=env, check=True, timeout=540)

    episodes = [json.loads(l) for l in (tmp_path / "run" / "episodes.jsonl").read_text().splitlines()]
    assert len(episodes) == 3
    assert all(e["non_local_page_hosts"] == [] for e in episodes)
    hosts = {json.loads(l)["host"] for l in egress_log.read_text().splitlines()} if egress_log.exists() else set()
    assert hosts, "the socket logger recorded nothing; the check would be vacuous"
    assert all(is_loopback_url(f"http://[{h}]" if ":" in h else f"http://{h}") for h in hosts), hosts
