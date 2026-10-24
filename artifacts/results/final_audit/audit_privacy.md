# Privacy / locality audit of the Agentic Pilot paper

Auditor scope: read-only. Repository files were not modified. Paper sections audited: 00_abstract, 01_introduction, 05_implementation, 07_results (Sec. "Locality (G3)"), 09_safety, tables/threats.tex, 12_conclusion. I also checked tables/status.tex and grepped every other section for locality claims.

## 1. What the code actually enforces

| Claim area | What the code does | Where |
|---|---|---|
| Model endpoint | `OllamaGateway._client_instance()` calls `require_local_endpoint(ollama_base_url, allow_remote_model)` before creating the `ollama.AsyncClient`. A host counts as local only if it is a loopback IP (`ipaddress.is_loopback`) or one of four loopback names. The names are accepted without DNS resolution. LAN, `0.0.0.0` and look-alike hosts are refused. | backend/security/locality.py:19-45, backend/llm/gateway.py (`_client_instance`) |
| Override | `PILOT_ALLOW_REMOTE_MODEL=true` (default False) disables the check entirely. | backend/config.py:16 |
| Coverage of model paths | Every model call I found goes through `OllamaGateway`: planner/nodes, self-verification (verification/manager.py:398), vision fallback (vision/fallback.py), registry probe, health, startup check. No other Ollama/HTTP client exists in `backend/`. The vision path sends base64 screenshots through the same checked client. | grep of backend/ |
| What is NOT enforced | (a) What the loopback server does with the request. Since 2025, Ollama serves "cloud" models (names ending in `-cloud`) through the same local API at 127.0.0.1:11434 and forwards them to ollama.com. `PILOT_OLLAMA_MODEL` and the router candidates are free-form strings, so nothing in the code stops this. The same applies to a local port-forward or proxy (an `ssh -L` tunnel, LiteLLM and similar) listening on loopback. (b) The check is on the URL, not on the connection: the `ollama` client uses httpx, which by default honours `HTTP(S)_PROXY`/`ALL_PROXY` environment variables. (c) `/api/setup/pull-model` spawns `ollama pull` (a network download, initiated by the user). | api/settings.py:52-80 |
| Chroma telemetry | `PersistentClient(..., settings=Settings(anonymized_telemetry=False))` for both memory and RAG stores. Unit test asserts it. | locality.py:48-53, memory/provider.py:61, rag/store.py:37, tests/test_local_egress.py:55 |
| Chroma embedding model | Collections are created without an `embedding_function`, so Chroma's default ONNX all-MiniLM-L6-v2 is used. It runs locally, but it is downloaded from a Chroma-hosted URL on first use if it is not cached. `rag_embedding_model="all-minilm"` in config is unused. The download is implicit (first memory or RAG use) and nothing guards it. | config.py:94 (unused), rag/store.py:38, memory/provider.py:62 |
| Storage | SQLite `~/.pilot/data.db`, Chroma `~/.pilot/chroma`, evidence `log_dir/evidence`, traces `~/.pilot/logs/traces.jsonl` (includes the first 500 chars of every prompt and response), privacy audit `~/.pilot/logs/privacy_audit.jsonl`, tracker `~/.pilot/evidence/<id>/telemetry.json`. `backend/telemetry/*` writes only local files. I found no upload path. Memory and knowledge content is, however, placed into prompts and therefore sent to whatever model endpoint is configured. | telemetry/tracer.py, telemetry/tracker.py:49, evidence/manager.py:45 |
| Privacy audit log | `privacy_auditor.record_llm_call` runs only after a successful `chat`. Failed attempts, `list()`/health calls and the `/api/setup/pull-model` download are not logged, and the log can be disabled (`privacy_audit_enabled`). `record_external_request` is never called by production code, only by a unit test, so browser traffic is never audited. | gateway.py, security/audit.py:84, grep |
| Service | FastAPI binds 127.0.0.1:8765 without authentication. The Observatory binds 127.0.0.1:8766. Tauri CSP limits `connect-src` to loopback. | main.py:149, observatory/backend/main.py:67, src-tauri/tauri.conf.json:23 |
| Other off-machine paths | (a) `observatory/frontend/index.html` loads Google Fonts (fonts.googleapis.com / fonts.gstatic.com), so opening the Observatory contacts Google. (b) `runner.switch_fallback` (API `.../fallback`) navigates to DuckDuckGo or Bing with the user's query, which is a search provider the user did not name. It is user-invoked. (c) The planner may navigate anywhere (stated in the paper). Plugins (gmail/forms/twitter) are dry-run with no network. RAG ingestion reads local files only. `backend/desktop` has no network code. | |
| Browser | Chromium launched by Playwright with `--disable-blink-features=AutomationControlled --no-sandbox`. Non-persistent contexts. Playwright's default flags suppress much background networking (component update, sync and so on), but this was not verified. | browser/pool.py:90-93 |

## 2. What the egress evidence shows and does not show

Sources: artifacts/results/e2e_smoke_stub/{README.md, egress_summary.json, episodes.jsonl, run_meta.json}, benchmarks/e2e/egress/sitecustomize.py, benchmarks/e2e/run_e2e.py, benchmarks/e2e/fake_ollama.py, tests/test_local_egress.py. I also inspected the raw socket log of that run, which survives only in the session scratchpad (`.../scratchpad/egress.jsonl`, 555 lines) and is not in the repository.

**What it shows**
- 70 episodes (10 dev tasks × 7 configs). The harness's Python processes (8 PIDs: the orchestrator plus 7 workers) made 555 Python-level `connect`/`connect_ex` calls on AF_INET/AF_INET6 sockets. The raw log shows all 555 went to **127.0.0.1:11435, the stand-in's port**. Not one went to the local sites or to anything else.
- In every episode, the set of hostnames in URLs reported by Playwright `BrowserContext.on("request")` contained only `127.0.0.1` (`non_local_page_hosts == []`).
- Memory was exercised in 54 episodes (Chroma query with the cached ONNX embedding). That query made no Python-level network connection.

**What it does not show**
1. **No real inference.** The model server was `fake_ollama.py`, which returns canned JSON: "navigate to the first URL in the request" and then "complete". The test therefore says nothing about where real inference runs or about a real Ollama server's own traffic (update checks, registry, cloud-model forwarding).
2. **Little of the agent was exercised.** In all 70 episodes, `browser_actions = 0` (the agent only navigated to the URL given in the request), `vision_called = false` (no screenshot was ever sent to a model), and `knowledge_retrieved = 0` (RAG retrieval never happened). Planner, intent, verification and memory paths ran. Vision, RAG, recovery-driven navigation and link-following did not.
3. **Process and protocol coverage.** The logger patches `socket.socket.connect/connect_ex` in Python processes that have the directory on PYTHONPATH. It does not see the Playwright Node driver, the Chromium processes, the model-server process, DNS lookups made by the C resolver (`getaddrinfo`), unconnected UDP `sendto`, or sockets opened inside native extensions.
4. **Page requests.** These are URL hostnames from Playwright `request` events, not interface-level observation. WebSockets (a separate Playwright event), DNS prefetch/preconnect and browser-internal traffic (Safe Browsing, component updater and so on) are not covered. Because the 5 sites are self-hosted fictional pages and the stub never left them, a clean result is expected by construction. It shows that the test pages load no third-party resources, not how the agent behaves on the web.
5. **Loopback-proxy blind spot.** The released summary aggregates by host only (`{"127.0.0.1": 555}`), and the committed test asserts only that hosts are loopback. In an environment where the outbound proxy listens on loopback, any proxied external HTTPS connection would be logged as 127.0.0.1 and pass. The current session's environment is such a case: `HTTPS_PROXY=http://127.0.0.1:44259`, and the run's platform string is the same sandbox type. The raw log shows that the reported run did not hit the proxy port. That clears the run, but the released artifact cannot show it and the test cannot detect it. Recommendation: record `host:port`, assert that the port set equals {stub port}, and release the raw log.
6. **Committed test is narrower than the run.** `test_agent_episode_opens_no_non_loopback_connection` runs 3 tasks (D01, D03, D05) in one configuration with `PILOT_ENABLE_MEMORY=false` and `PILOT_ENABLE_RAG=false`, so Chroma is never queried.
7. **Chroma download.** The embedding model was pre-cached (README caveat), so the first-use download was not observed.
8. **Provenance.** run_meta.json records `git_commit 1435fe9`, `git_dirty: true`. The paper says the working tree "was then committed as 55ac1ea". 1435fe9 is an ancestor of 55ac1ea, two commits back with b9d5088 between them, but the claim that the dirty tree equals 55ac1ea cannot be verified from the artifacts.

**Are the two privacy-property clauses supported by code?**
- "model inference is restricted to the user's machine": **Not supported as stated.** The code restricts the *configured endpoint host* to loopback (unless overridden). It does not restrict where the server behind that endpoint performs inference (Ollama cloud models, local tunnels or proxies), and it does not control environment proxies. The egress test used a stub and cannot speak to inference location. Supported wording: "by default the model client sends prompts and screenshots only to a server on the loopback interface".
- "task records, memory and evidence are stored only on its disk": **Supported by code inspection (C) as a statement about where the code writes them.** No upload path exists, and telemetry modules write local files. Caveats: the contents are also transmitted as prompt context to the configured model endpoint, are unencrypted, and are readable through the unauthenticated loopback API. The egress test does not establish "only" (memory was exercised but not ingestion or vision), so the evidence class is C, not E.

## 3. Sentences that exceed the evidence, with corrected wording

Severity: H = central claim, M = method/evidence description inaccurate, L = imprecise or incomplete.

1. **[H] 00_abstract.tex:2** — "Model traffic is restricted to the machine; in 70 agent episodes the agent process opened no non-loopback connection."
   → "The model client refuses non-loopback endpoints unless the user overrides this; in 70 harness episodes with a scripted stand-in for the model server, the agent's Python processes attempted connections only to the stand-in on 127.0.0.1, and the browser requested only loopback URLs."

2. **[H] 01_introduction.tex:13** — "It is \emph{privacy-preserving} in that model inference is restricted to the user's machine and its records are stored there (Section~\ref{sec:safety})."
   → "It is \emph{privacy-preserving} in a narrow sense: by default its model client sends prompts and screenshots only to a model server on the loopback interface, and it writes task records, memory and evidence only to local files (Section~\ref{sec:safety}); whether that server runs inference locally depends on its configuration."

3. **[M] 01_introduction.tex:28** — "Enforcement and an \textsc{actual} test of local-only model traffic, addressing G3"
   → "Enforcement of a loopback-only model endpoint and an \textsc{actual} test, with a stand-in model server, that the agent's Python processes connect only to loopback addresses, addressing G3"

4. **[M] 07_results.tex:30 (sentence 1)** — "To test locality we ran 70 full agent episodes, ... with a scripted stand-in for the Ollama API on the loopback interface, and logged every socket connection the agent process attempted."
   → "... and logged every outbound \texttt{connect} call made from the harness's Python processes (orchestrator and workers); the Playwright driver, Chromium, the model server and DNS lookups were not instrumented. Because the stand-in claims completion at once, the episodes made no browser action beyond the initial navigation, never called the vision model and never retrieved knowledge; memory retrieval ran in 54 of them."

5. **[M] 07_results.tex:30 (sentence 2)** — "All 555 attempts went to 127.0.0.1, and no page request left the loopback interface."
   → "All 555 attempts went to 127.0.0.1, all of them to the stand-in's port, and every page request that Playwright reported named host 127.0.0.1; WebSockets and browser-internal traffic were not observed."

6. **[L] 07_results.tex:30 (sentence 4)** — "The repository's test suite runs this check, together with tests that a remote model address is refused and that Chroma telemetry is off"
   → "The repository's test suite runs a reduced version of this check (three development tasks, one configuration, memory and retrieval disabled), together with tests that a remote model address is refused and that Chroma telemetry is off"

7. **[H] 09_safety.tex:6** — "We call the system privacy-preserving in this sense: \emph{model inference is restricted to the user's machine, and task records, memory and evidence are stored only on its disk.}"
   → "We call the system privacy-preserving in this sense: \emph{by default the model client sends prompts and screenshots only to a model server on the loopback interface, and the code writes task records, memory and evidence only to local files.}"

8. **[M] 09_safety.tex:6** — "The model client refuses a non-loopback endpoint unless the user sets an explicit override, Chroma telemetry is off, and in 70 agent episodes the agent process opened no non-loopback connection (Section~\ref{sec:res-privacy})."
   → "... and in 70 harness episodes with a stand-in model server the agent's Python processes attempted no connection to a non-loopback address (Section~\ref{sec:res-privacy})."

9. **[L] 09_safety.tex:6** — "The property does not cover: data the user asks the agent to enter on a website, ...; model weights and Chroma's default embedding model, which are downloaded once; unencrypted local storage; or traffic of a different configuration." The list of exclusions is incomplete, which makes the property read as stronger than it is.
   → Add: "what the loopback model server does with a request (for example, Ollama cloud models or a local tunnel forward it off the machine); the model server's own traffic; prompt context drawn from memory and retrieved documents, which goes to whatever endpoint is configured; and the user-invoked DuckDuckGo/Bing fallback, which sends the query to that provider."

10. **[L] 09_safety.tex:6** — "The egress test observed the agent's Python process and the browser's page requests, not background traffic of the Chromium binary."
   → "The egress test observed outbound connect calls in the harness's Python processes and the URLs of page requests reported by Playwright; it did not observe a real model server (a stand-in was used), the Playwright driver or Chromium processes (background traffic, WebSockets), or DNS lookups."

11. **[L] 09_safety.tex:12** — "The service listens on loopback, and every model call is logged with destination and payload sizes."
   → "The service listens on loopback, and each successful model completion is logged with destination and payload sizes (failed attempts and model-list calls are not, and the log can be disabled)."

12. **[M] tables/threats.tex:11 (Model inference row)** — residual risk reads only "user override sends prompts and screenshots off the machine", with Evidence "E, T".
   → Residual: "user override, or a loopback server that forwards requests (e.g., Ollama cloud models, a tunnel), sends prompts and screenshots off the machine; E used a stand-in server".

13. **[L] tables/threats.tex:14 (Browser traffic row)** — Control column "page requests logged in the harness". A harness logger is not a control in the agent.
   → Control: "none in the agent; the test harness logs page-request URLs". Residual: "Chromium background traffic, WebSockets and DNS not observed".

14. **[M] tables/status.tex:13** — "Local-only model endpoint, no telemetry & IE & E (70 episodes)"
   → "Loopback-only model endpoint; Chroma telemetry off & IE & E (70 stand-in episodes), T". The Observatory UI loads Google Fonts, and telemetry-off is evidenced by a unit test, not by the episodes.

15. **[H] 12_conclusion.tex:4** — "Model traffic is restricted to the user's machine."
   → "By default the model client connects only to a loopback endpoint, and in 70 episodes with a stand-in model server the agent's Python processes connected only to loopback addresses."

Sentences checked and found accurate: 05_implementation.tex:12 (locality enforcement, LAN counted as remote, Chroma telemetry, audit log parses host); 07_results.tex:30 "The stand-in always claims completion, so these episodes say nothing about task success"; 09_safety.tex:4 (threat model); 04_architecture.tex:6 "FastAPI service bound to the loopback interface"; the Memory/task-data, Screenshots and Retention rows of the threats table.

## 4. Recommendations (non-binding)
- Log `host:port:pid` and assert that ports are a subset of {stub port}. Release the raw egress log next to egress_summary.json.
- Enable memory and RAG in the committed egress test, and add one episode that forces the vision path, so that a screenshot request is exercised.
- Reject model names ending in `-cloud` (or require the override for them), and/or construct the ollama client with `trust_env=False`.
- Self-host the Observatory fonts. Note the DuckDuckGo/Bing fallback in the paper.
- Optionally run the egress test under a network namespace with no route (`unshare -n`), which would cover Chromium, the driver and DNS as well.

**Total overstated or incomplete sentences: 15** (H: 4, M: 6, L: 5).
