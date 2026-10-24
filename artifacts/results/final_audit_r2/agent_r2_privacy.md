# R2 privacy and security audit (Agent 5)

Scope: read-only. No repository file was edited. The title stays as the author decided. Checked: paper sections 00, 01, 04, 05, 07 (Sec. "Locality (G3)"), 09, 10, 12; tables/threats.tex and tables/status.tex; artifacts/results/e2e_smoke_stub/*; benchmarks/e2e/{egress/sitecustomize.py, run_e2e.py, fake_ollama.py, sites.py}; tests/test_local_egress.py; backend/security/{locality,audit}.py; backend/llm/gateway.py; backend/config.py; backend/main.py; backend/api/{tasks,observability,settings}.py; observatory/; src-tauri/tauri.conf.json; and the previous audit, artifacts/results/final_audit/audit_privacy.md.

## Status of the previous audit (audit_privacy.md, 15 items)

The current text resolves 14 of the 15 items. Intro 13 and 28, 07:30 sentences 1, 2 and 4, 09:6 (property, evidence, exclusions, scope of the egress test), 09:12 (audit log), threats rows "Model inference" and "Browser traffic", status row 13, and the conclusion all use the recommended wording or wording close to it. Provenance (item 8) is now disclosed as "uncommitted working tree based on commit 1435fe9".

Partly open:
- Item 1 (abstract): the stand-in and the Python processes are now named. The abstract still omits "unless overridden", and it does not say that the run cannot show where a real server sends requests. See F1.
- Facts from Section 1 of the previous audit that the paper still omits: the Observatory loads Google Fonts, and proxy environment variables are honoured by the HTTP client. See F4.
- Code recommendations that were not carried out. The paper describes bf0a8a5, so these are acceptable as long as the text discloses them: the test asserts hosts but not ports; memory and RAG are off in the committed test; no filter on `-cloud` model names; `trust_env` is not disabled. The raw log is now released (`egress_raw.jsonl`, with host, port and pid), which resolves the earlier point that the loopback-proxy case could not be checked for the reported run.

---

## (A) What the scripted stand-in test establishes

**Instrumentation.** Done with `benchmarks/e2e/egress/sitecustomize.py`, which Python imports automatically when its directory is on `PYTHONPATH`. When `PILOT_EGRESS_LOG` is set, it monkeypatches `socket.socket.connect` and `socket.socket.connect_ex` at class level. It logs `{pid, host, port}` for AF_INET and AF_INET6 sockets only (AF_UNIX is not logged).
- *Covered:* every Python-level `connect`/`connect_ex` call on IPv4/IPv6 sockets. That includes `socket.create_connection` and asyncio `sock_connect`/`create_connection`, which both call `sock.connect`, so it also covers httpx/anyio (and therefore the `ollama` client) and `ssl.SSLSocket.connect` (which calls `super().connect`). Destinations are the addresses after resolution, so a hostname that resolves off the machine would still show up as a non-loopback IP.
- *Not covered:* unconnected UDP (`sendto`/`sendmsg`, e.g. QUIC or mDNS); DNS resolution itself (`getaddrinfo` is in C and its queries to the resolver are not logged); sockets opened in native code; and any process that does not import this sitecustomize. That means non-Python processes (the Playwright Node driver, every Chromium process, the model server, an `ollama pull` subprocess) and Python started with `-I`/`-S`.
- *Processes instrumented:* 8 PIDs in `egress_raw.jsonl`. PID 1329 is the orchestrator, with 2 connects (the environment probe of `/api/version` and `/api/tags`). The other 7 are one worker per configuration (39–99 connects each). They inherited `PYTHONPATH` and `PILOT_EGRESS_LOG` through `subprocess.call(..., env=env)` (run_e2e.py:235).

**Page requests.** `BrowserContext.on("request")` was attached to every context returned by `browser_pool.acquire` (run_e2e.py:103-111). For each episode, `non_local_page_hosts` = URL hostnames − {127.0.0.1, ""} (run_e2e.py:162). These are request URLs that Playwright reports, not observations at the interface. The check does not see WebSockets (a separate event), DNS prefetch or preconnect, or traffic internal to Chromium. The test sites are self-hosted by a `ThreadingHTTPServer` on 127.0.0.1 inside the worker (sites.py:284), and Chromium connects to it. Those connections are server-side `accept`s, which is why they do not appear in the connect log.

**Stand-in server.** `benchmarks/e2e/fake_ollama.py` on 127.0.0.1:11435 returns canned JSON: the intent is the first URL in the request, the plan has one step, the planner always says `complete`, and the self-check always says done. It does no inference at all. `run_meta.json` records the model as `scripted-stub:latest`, size 0, digest "stub".

**Result (verified against the raw file).** 555 connect attempts, all to `127.0.0.1:11435`. The gateway made 465 model calls. Connects and requests differ because of keep-alive reuse and list/version probes. `non_local_page_hosts == []` in all 70 episodes. Totals across episodes: `browser_actions` = 0, `vision_called` = 0, `knowledge_retrieved` = 0. Memory retrieval returned ≥1 record in 54 of the 60 memory-enabled episodes, and Chroma made no Python-level connection: no posthog telemetry and no model download (the embedding model was already cached, as the README says).

**Code version.** `run_meta.json`: `git_commit 1435fe9`, `git_dirty: true`, started 2026-10-04T07:20:38Z. The locality enforcement (`backend/security/locality.py`, gateway check, Chroma settings) first appears in 55ac1ea at 07:28:30, eight minutes after the run started. The paper evaluates `bf0a8a5`. `git diff 1435fe9 bf0a8a5 -- backend` touches 9 files (+199/−14), and `backend/` is unchanged from bf0a8a5 to HEAD. The diff of the dirty tree was not saved, so the run cannot be tied byte-for-byte to the evaluated code. The enforcement code was not exercised in the run anyway, because the endpoint was already loopback. Refusal is shown only by the unit tests (T).

**Committed test** (`tests/test_local_egress.py`):
- `is_loopback_url` cases, accept and reject.
- Refusal of a remote endpoint, with the override allowed.
- The gateway refuses 203.0.113.7 before connecting.
- `anonymized_telemetry is False`.
- A reduced episode test: D01, D03, D05, config `full`, with `PILOT_ENABLE_MEMORY=false` and `PILOT_ENABLE_RAG=false`. It asserts that the set of logged **hosts** is loopback. It checks neither the port nor the per-PID coverage, so a proxy listening on loopback would pass. It guards against an empty log ("vacuous").
- No committed script reproduces the 70-episode run with egress logging, or the aggregation into `egress_summary.json`.

**Loopback enforcement code (verified, also by running `is_loopback_url` on Python 3.11.15).**
- `backend/llm/gateway.py:39-49`: `require_local_endpoint(ollama_base_url, allow_remote_model)` runs before `ollama.AsyncClient` is created. Every model path goes through this one client (chat, vision with base64 screenshots, list, registry probe).
- `backend/security/locality.py:13-45`: the host comes from `urlsplit`, lowercased, with the trailing dot stripped.
  - Accepted: the names `localhost`, `localhost.localdomain`, `ip6-localhost`, `ip6-loopback` (no DNS resolution; /etc/hosts is trusted), all of 127.0.0.0/8, `::1` in any spelling, and `::ffff:127.0.0.1` (True on 3.11.15).
  - Refused: LAN (192.168/16, 10/8), link-local (169.254/16, fe80::), `0.0.0.0`, `*.local`, integer/hex/short IPv4 forms (`2130706433`, `0x7f000001`, `127.1`; refusing these is the safe direction), look-alikes (`127.0.0.1.example.com`, `localhost.evil.example`), userinfo tricks, and the empty string.
  - Caveat: `http://evil.com\@127.0.0.1` is accepted by `urlsplit`. Whether httpx parses it the same way was not checked here (httpx is not installed). The base URL is set by the trusted user, so this is outside the threat model.
- Override: `PILOT_ALLOW_REMOTE_MODEL=true` (config.py:16, default False) turns the check off completely and logs nothing. The privacy log then records `is_local: false`. The base URL is read only at startup. No API changes it.
- Not enforced:
  - Model names (`*-cloud` models go through local Ollama to ollama.com; there is no `cloud` filter anywhere in backend/).
  - Proxy environment variables (httpx defaults to `trust_env=True`).
  - The launcher (`main.py:131-139, 317`) sends GET `/api/tags` to `--ollama-url` without the check. No user data is sent.
  - `/api/setup/pull-model` (settings.py:51-80) spawns `ollama pull`, which uses its own `OLLAMA_HOST` and downloads from the registry.
- Chroma: both `PersistentClient`s use `local_chroma_settings()` (memory/provider.py:61, rag/store.py:37). The default ONNX embedding model is downloaded on first use. `chromadb>=0.5.0` is not pinned.
- Privacy audit log (`security/audit.py`): written only after a successful `chat`. `record_external_request` has no production caller, so browser traffic is never audited. The paper now states this correctly at 09:12.

---

## (B) Untested paths

E = egress run; T = unit test; C = code inspection. "Disclosed" says where the paper states the gap.

| # | Path | Exercised? | Control in code | Disclosed in paper |
|---|---|---|---|---|
| 1 | Real Ollama server: where inference runs, and its own traffic (update checks, registry, telemetry) | No (stand-in) | none | Yes, 09:6, 12:4, threats:11 |
| 2 | Ollama cloud models (`*-cloud`) served through local 127.0.0.1:11434 and forwarded to ollama.com | No | none (no name filter) | Yes, 09:6, threats:11 |
| 3 | Remote `PILOT_OLLAMA_BASE_URL`/LAN host | Refusal: T only | loopback check; override `PILOT_ALLOW_REMOTE_MODEL` | Yes, 05:12, 09:6 |
| 4 | Loopback tunnel or proxy (ssh -L, LiteLLM) on 127.0.0.1 | No; the committed test checks hosts, not ports | none | Yes, 09:6 (tunnel); host-only assertion not disclosed (F7) |
| 5 | `HTTP(S)_PROXY`/`ALL_PROXY` honoured by httpx: a proxy receives model requests even for a loopback URL | No | none (check is on the URL, not the connection) | **No** (F4) |
| 6 | DNS lookups (C resolver; Chromium's resolver, prefetch) | No | none | Yes, 09:6 |
| 7 | UDP/QUIC (`sendto`), sockets in native code | No | none | No (F6, minor) |
| 8 | Page WebSockets | No (not in `request` events) | none | Yes, 07:30, 09:6, threats:14 |
| 9 | Chromium background traffic (Safe Browsing, component updater, variations, optimization guide, GCM) | No | Playwright default flags (unmeasured) | Yes, 09:6, threats:14 |
| 10 | Websites the agent visits by design, their third-party resources, link-following | No (self-hosted pages; clean by construction; 0 browser actions) | none | Yes, 09:6, threats:13 |
| 11 | DuckDuckGo/Bing fallback (user-invoked, runner.py:141-158) | No | user-invoked only | Yes, 09:6 |
| 12 | Browser extensions | n/a: none are loaded (non-persistent Playwright contexts) | C | Not needed |
| 13 | Dependency telemetry: Chroma posthog (off; no connection seen in 60 memory episodes), Chroma ONNX download (cached), LangSmith tracing if `LANGCHAIN_TRACING_V2` is set in the user's environment, `ollama pull` | Chroma query: E (Python level); download and others: no | Chroma telemetry off (T); nothing else | Chroma telemetry and download: yes, 09:6; others no (env-dependent, low) |
| 14 | Vision path (screenshots to model), RAG retrieval, recovery navigation | No (`vision_called`=0, `knowledge_retrieved`=0) | same gateway check | Yes, 07:30 |
| 15 | Tauri/React client and its WebView (WebView2/WebKitGTK background traffic) | No | CSP `connect-src` loopback only (tauri.conf.json:23) | No (F8) |
| 16 | Observatory UI loads fonts.googleapis.com/gstatic (observatory/frontend/index.html:7-9) | No | none | **No** (F3, F4) |
| 17 | Local API 127.0.0.1:8765: no auth, no Host check (no TrustedHostMiddleware), WebSocket `/ws/observability` accepts any Origin (observability.py:66-69); Observatory `/ws` likewise (observatory/backend/api.py:132). Reachable by web pages on the same machine, including pages the agent visits (DNS rebinding, cross-site WebSocket) | No | CORS allow-list (does not apply to WebSockets or to rebinding) | Partly: "API has no authentication" (09:14); exposure to web pages **not** stated (F2, F3) |
| 18 | Storage at rest: SQLite `~/.pilot/data.db`, Chroma `~/.pilot/chroma`, `traces.jsonl` (first 500 chars of every prompt and response), evidence PNGs, typed text in clear; default umask; no encryption | n/a | none | Mostly: 09:14, threats:12, :15. File permissions and prompt traces not stated (F9) |
| 19 | Log retention: evidence, traces, privacy log, SQLite, Chroma | n/a | no deletion (DELETE /api/tasks cancels only) | Partly: threats:16 names only evidence (F9) |
| 20 | Code version of the run vs evaluated bf0a8a5 | n/a | — | Partly: 07:30 (dirty 1435fe9); gap to bf0a8a5 not stated (F5) |

Side observation from code reading (not executed; not a paper-text issue): `GET /api/tasks/{task_id}/evidence/{filename}` (tasks.py:121-135) builds `evidence/<task_id>`, and its traversal guard is a string-prefix check against that same directory. With `task_id = ".."` (percent-encoded so that clients do not collapse it), the directory becomes `log_dir`, and `traces.jsonl` or `privacy_audit.jsonl` would pass the guard. `_get_task_dir` also creates directories. Combined with row 17, this widens what a web page could read. Worth a fix in the code.

---

## (C) Findings

Severity: H = central claim exceeds evidence; M = undisclosed path or inaccurate evidence description; L = imprecise or incomplete. No hardware tests or new experiments are requested; every fix is a text edit.

**F1 [M] sections/00_abstract.tex:2.** The title claims "Privacy-Preserving". The abstract never says in what sense, omits the override, and does not say that the stand-in cannot show where a real server sends data. The conclusion (12:4) and intro (01:13) carry these qualifiers; the abstract does not.
Quoted: "The model client refuses non-loopback endpoints, and in 70 episodes with a scripted stand-in for the model server the agent's Python processes connected only to loopback addresses."
Replace with: "We call the agent privacy-preserving in a narrow sense: by default its model client refuses non-loopback endpoints (an explicit override lifts this), and in 70 episodes with a scripted stand-in for the model server the agent's Python processes connected only to that stand-in on 127.0.0.1, which does not show where a real model server sends requests."

**F2 [M] sections/09_safety.tex:12 and :14.** "The service listens on loopback" reads as a protection. The code has no Host-header check and accepts WebSocket connections from any Origin (backend/api/observability.py:66-69; backend/main.py:78-90 has only CORS, which does not govern WebSockets or DNS rebinding). Web pages open on the same machine, including those the agent itself visits, can therefore potentially read task events and, through rebinding, records and evidence screenshots. This is threat (iv) of the paper's own model (disclosure to parties other than the site the user asked for), and it is not disclosed.
- 09:12, quoted: "The service listens on loopback, and each successful model completion is logged"
  Replace with: "The service listens only on the loopback interface, and each successful model completion is logged"
- 09:14, quoted: "The API has no authentication, typed text is stored in clear, and screenshots are not redacted."
  Replace with: "The API on 127.0.0.1 has no authentication and checks neither the Host header nor the Origin of WebSocket connections, so a web page open on the same machine, including one the agent visits, may be able to reach it (DNS rebinding, cross-site WebSocket access) and read task events, records and evidence screenshots, subject to the browser's local-network protections; typed text is stored in clear, and screenshots are not redacted."

**F3 [M] tables/threats.tex (after line 16).** The local API and the monitoring UI are disclosure surfaces with no row in the table.
Insert:
```
Local API & bound to 127.0.0.1; no authentication, Host or WebSocket Origin check & C & web pages on the same machine may read task events and evidence \\
Monitoring UI & loads web fonts from Google & C & opening it contacts fonts.googleapis.com \\
```

**F4 [L] sections/09_safety.tex:6 (exclusion list).** Two off-machine paths are not listed: proxy environment variables (httpx `trust_env=True` by default; the check is on the URL, not the connection), and the Observatory's Google Fonts.
Quoted: "model weights and Chroma's default embedding model, which are downloaded once; and unencrypted local storage."
Replace with: "model weights and Chroma's default embedding model, which are downloaded once; proxy environment variables, which the HTTP client honours, so a configured proxy can receive model requests even for a loopback address; the monitoring UI, which loads web fonts from Google; and unencrypted local storage."

**F5 [L] sections/07_results.tex:30 (provenance).** The run predates the commit that added the enforcement code (55ac1ea, 07:28 versus run start 07:20), and the paper's evaluated code is bf0a8a5 (05:4). The dirty diff was not saved.
Quoted: "on an uncommitted working tree based on commit \texttt{1435fe9} (recorded in the run's metadata)."
Replace with: "on an uncommitted working tree based on commit \texttt{1435fe9} (recorded in the run's metadata; the uncommitted changes were not saved, so the run cannot be tied exactly to the evaluated commit \texttt{bf0a8a5}, whose agent code differs from \texttt{1435fe9} in nine files)."

**F6 [L] sections/07_results.tex:30 (instrumentation).** Accurate but unspecific about the mechanism and the APIs not covered.
Quoted: "We logged every outbound \texttt{connect} call made from the harness's Python processes; the Playwright driver, Chromium, the model server and DNS lookups were not instrumented."
Replace with: "A \texttt{sitecustomize} module on the Python path logged every call to \texttt{socket.connect} and \texttt{connect\_ex} on IPv4 and IPv6 sockets in the harness's eight Python processes (an orchestrator and one worker per configuration; asyncio and HTTP-client connections pass through these calls); unconnected UDP, sockets opened in native code, DNS lookups, the Playwright driver, Chromium and the model server were not instrumented."

**F7 [L] sections/07_results.tex:30 (committed test).** The test asserts only that hosts are loopback. A proxy or tunnel listening on loopback would pass.
Quoted: "The repository's test suite runs a reduced version of this check (three development tasks, one configuration, memory and retrieval disabled),"
Replace with: "The repository's test suite runs a reduced version of this check (three development tasks, one configuration, memory and retrieval disabled; it asserts loopback hosts, not the port, so a proxy listening on loopback would pass, whereas the released raw log of the 70-episode run shows only the stand-in's port),"

**F8 [L] sections/10_limitations.tex:6.** The Limitations section has no locality caveat, although G3 is one of the three stated gaps.
Quoted: "No result involves a language model or a live website, so the agent is not shown to complete tasks."
Replace with: "No result involves a language model or a live website, so the agent is not shown to complete tasks. Likewise, the locality test used a stand-in model server and self-hosted pages and instrumented only the Python processes, so it does not show what a real model server, Chromium or the desktop client send off the machine."

**F9 [L] tables/threats.tex:12 and :16.** The residual risks for storage and retention are incomplete. Traces keep prompt and response text; files use default permissions; only evidence is named as growing.
- Line 12, quoted: "not encrypted; readable by any local process"
  Replace with: "not encrypted; default file permissions; traces keep the first 500 characters of each prompt and response"
- Line 16, quoted: "no deletion policy & C & evidence grows without bound"
  Replace with: "no deletion policy & C & evidence, traces, database and memory grow without bound"

**F10 [L] sections/05_implementation.tex:12.** "now" is revision language. The text does not say what counts as loopback, what the override is called, or what the check does not cover.
Quoted: "The model client now refuses any endpoint whose host is not a loopback name or address, before connecting, unless the user sets an explicit override; LAN addresses count as remote."
Replace with: "The model client refuses any endpoint whose host is not a loopback address (127.0.0.0/8, \texttt{::1}) or a \texttt{localhost} name (accepted without DNS resolution), before connecting, unless the user sets \texttt{PILOT\_ALLOW\_REMOTE\_MODEL=true}; LAN, link-local and unspecified addresses count as remote. The check applies to the configured address, not to the model name or proxy settings."

**F11 [L] sections/00_abstract.tex:6 (keywords).** "privacy-preserving computing" names the field of differential privacy, secure computation and homomorphic encryption, none of which the paper uses. The title is unchanged under this edit.
Quoted: "privacy-preserving computing"
Replace with: "data locality"

**F12 [L] tables/status.tex:13.** The row's E and T support different things. The run shows destinations with a loopback endpoint and never exercises refusal.
Quoted: "E (70 stand-in episodes), T"
Replace with: "E (destinations, 70 stand-in episodes), T (refusal, telemetry flag)"

**F13 [Info, not paper text; the author may wish to align these with the paper]**
- tests/test_local_egress.py:1, quoted: "Evidence for the privacy property: model traffic and the agent's own traffic stay on this machine." Suggested: "Evidence that the agent's Python processes connect only to loopback addresses when the model endpoint is a loopback stand-in."
- artifacts/results/e2e_smoke_stub/README.md, quoted: "recorded every outbound connection the agent process attempted". Suggested: "recorded every Python-level socket connect in the harness's Python processes".
- No committed script reproduces the 70-episode egress run or the aggregation into egress_summary.json.
- Code (side observation in B): evidence endpoint traversal with `task_id=".."`.

Sentences checked and found accurate: 01:10 (G3), 01:13 (narrow privacy-preserving definition), 01:28 ("partially addressing G3"), 04:6 (FastAPI on loopback), 05:4 (default branch uses a hosted model; not evaluated), 07:30 (555 to stand-in port; Playwright-reported hosts; WebSockets and browser-internal traffic not observed; no vision or retrieval; memory 54/60; says nothing about task success), 09:4 (threat model), 09:6 (property and most exclusions), 09:12 (audit-log scope), 12:4 (conclusion), threats rows 11, 13, 14, 15, 17, 18.

**Totals: 12 paper-text findings (H 0, M 3, L 9), plus informational items.** No remaining sentence asserts "no data leaves" or uses unqualified "privacy-preserving" in running text. The remaining exposure is the title and keywords, which F1 and F11 address without changing the title.
