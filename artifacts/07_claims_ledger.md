# 07 — Claims Ledger (C2)

Every factual statement in the paper about the system, a number, or other work, with its source. Code references are at commit `2361d50` (unchanged in this branch).

- **Type:** code / experiment / citation / repo-record.
- **Status:** `verified` means checked first-hand in this session, or by a Phase A agent and spot-checked by the Lead Editor. `todo` means it appears in the PDF as a visible `\todo{}`.

## Numbers

| ID | Section | Claim | Type | Source | Status |
|---|---|---|---|---|---|
| N1 | Abstract, §VII, Tab. IV | 38 constructed end states: 23 unsatisfied, 15 satisfied | experiment | `artifacts/results/verification_gate_summary.csv`, row `all` | verified |
| N2 | Abstract, §VII | Component gate withholds 15/23 (8 FC); dispatch-only accepts all 23 | experiment | same CSV, rule `component` vs `dispatch_only` | verified |
| N3 | Abstract, §VII | Live `verify_node`: withholds 14/23 (empty reasoning) and 13/23 (verbose reasoning); P1 lost in both, X2 lost with verbose | experiment | same CSV, rules `live_empty` / `live_verbose`; `verification_gate_cases.csv` | verified |
| N3b | Abstract, §VII | 3 of 15 satisfied states rejected (X6, C5, C6), identical across the three rules | experiment | `verification_gate_cases.csv` | verified |
| N4 | Tab. IV | Per-category FC/FR; FCR 0.605 / 0.400 / 0.429 / 0.455 | experiment | `verification_gate_summary.csv` (table generated from `verification_gate_cases.csv` by script) | verified |
| N5 | Abstract, §VII | Median 35.2 ms over the 33 decisions that evaluate Φ (max 52.5); 5 pre-check stops ≤ 8.2 ms | experiment | `results/verification_gate_run.log` line `cases=38 …` | verified |
| N6 | §VI | 20 repetitions after a warm-up call | code | `artifacts/experiments/verification_gate_study.py` (`--reps 20`; the first `gate_decision` call is untimed) | verified |
| N7 | §VI, §VII | 4-core Xeon 2.8 GHz, 15 GiB, no GPU; Python 3.11.15; Playwright 1.56.0; Chromium 141.0.7390.37; LangGraph 1.2.12 | experiment | `lscpu`, `free -h`, `importlib.metadata`, `browser.version` run this session; also `04_results_raw.md` §environment | verified |
| N8 | §VII-B | Router selections per call type and scenario; 3 fallbacks in the default install; substring-keyword probes route to moondream; the recovery model is sticky for the next planning call | experiment | `artifacts/results/routing_resolution.csv` (`artifacts/experiments/routing_default_install.py`, rows `keyword_probe`, `recovery_then_plan`) | verified |
| N9 | §VII-C | 108 collected, 104 passed, 4 failed, 1 collection error; Observatory 20/20; 62.0% line coverage | experiment | `results/junit.xml` (109 entries including the error), `tests_by_file.csv`, `junit_observatory.xml`, `coverage_by_subsystem.csv`. Run by A4; the Lead Editor re-parsed the XML and CSVs. | verified |
| N10 | §VII | Failure causes: 2 need Ollama; 1 timeout (`test_action_failure_never_marks_completed`); 1 needs the missing `scratch/` directory as cwd; the collection error is a missing import on Python 3.11 | experiment | `04_results_raw.md` "Failures in the canonical run 4" | verified |
| N11 | §V | 10,755 backend lines, 1,682 in `nodes.py` | code | `wc -l` (A1 §15); `nodes.py` confirmed 1,682 by the Lead Editor | verified |
| N12 | §IV-C, Eq. (1) | Answer-length threshold 40 chars; budget K = 15 model calls | code | `verification/manager.py:270-272`; `agent/nodes.py:1469,1509` | verified |
| N13 | §IV-D | 3 verify-node retries; 7 failure types; 2 attempts per ladder level; fail after 6 | code | `nodes.py:1369-1373`; `recovery/engine.py:33-41,45-50,61,98-102` | verified |
| N14 | §IV-B | 120 chars per element; ≤ 5 links; cap 50; 1280×800 viewport | code | `browser/dom.py:153-172,195-198,206-207`; `browser/pool.py:128` | verified (A1 §7) |
| N15 | §IV-E | Installed-model list refreshed at every task start | code | `nodes.py:189-192` → `vision/fallback.py:62` → `llm/gateway.py` `list_model_names` → `registry.mark_installed` | verified |
| N16 | §IV-F | Context budget 3,500 tokens | code | `config.py:62`; `rag/context_builder.py:75,104-105` | verified (A1 §9) |
| N17 | §III | Wall-clock limit 5 min | code | `config.py:28`; `agent/runner.py:364-372` | verified |
| N18 | §VIII | Sanitizer has 17 patterns | code | `security/sanitizer.py:16-38` | verified (A1 §10) |
| N19 | §VII | 12 challenge phrases | code | `browser/dom.py:32-45` (the Lead Editor counted 12) | verified |
| N20 | §VI | Repo benchmark list: 8 tasks, 4 without a checkable criterion | code | `experiment/config.py:204-218` | verified |
| N21 | §I, §VI | 30-task, 6-category proposed suite | proposal | §VI protocol (a design, not a result) | n/a |
| N22 | §VII | End-to-end success, FCR, latency, recovery, vision rate, evidence completeness | experiment | **not measured** (no Ollama or live web in this environment) | **todo** (visible `\todo{MEASURE}`) |
| N23 | §VI | Hardware, OS, Ollama version, model digests for end-to-end runs | experiment | not measured | **todo** |
| N24 | §VII | Qualitative case study screenshots | experiment | not measured | **todo** |

## System descriptions (code)

| ID | Section | Claim | Source | Status |
|---|---|---|---|---|
| S1 | §III, Fig. 2 | 11 nodes; router conditions as drawn | `agent/graph.py:18-84` | verified |
| S2 | Fig. 2 caption, §V | Only `verify` can end a task as Completed | `graph.py` routers; `nodes.py:947-966` (a `complete` action leaves status unchanged); `nodes.py:1478-1506` | verified |
| S3 | §V | Terminal guard downgrades a completion when navigation is unverified | `nodes.py:1593-1602` | verified |
| S4 | §III, §V | Checkpoint after every node; resume skips intent parsing | `runner.py:275-306`; `nodes.py:67-75` | verified |
| S5 | §III | API binds loopback; CORS localhost only | `backend/main.py:78-91,149` | verified (A1 §10) |
| S6 | §IV-A | Multi-step trigger: connective or more than 8 words; exact-text plan override | `nodes.py:119,151-171` | verified |
| S7 | §IV-A | Action vocabulary of 8 types | `agent/prompts.py:28-35` | verified |
| S8 | §IV-A | Deterministic overrides, including Google-specific typing | `nodes.py:697-902` | verified |
| S9 | §IV-B | Vision only on `need_help`; viewport fractions; no per-action check; cache | `nodes.py:733-817,1020-1034`; `vision/fallback.py:47-56` | verified |
| S10 | §IV-C | $\Phi$ conjuncts H, T, X, R and error/bot vocabulary | `verification/manager.py:173-292` | verified |
| S11 | §IV-C | Step predicate is dispatch success | `nodes.py:1393-1426` | verified |
| S12 | §IV-C | CAPTCHA pre-check before $\Phi$ → Blocked | `nodes.py:1332-1357` | verified |
| S13 | §IV-D, Tab. III | Strategy label dropped; recovery always re-observes | `recovery/engine.py:198`; `state.py:10-47` (no key); `graph.py:75-80`; A1 ran it to confirm | verified |
| S14 | §IV-E | Deterministic analyzer roles | `llm/analyzer.py:60-189` | verified (A1 §4) |
| S15 | §IV-E, §VII | Stickiness except recovery; fallback chain | `llm/router.py:121-135,163-182` | verified (plus experiment N8) |
| S16 | §IV-E, Tab. III | Cool-down configured but unread | `config.py:49`; grep finds no reader | verified |
| S17 | §IV-E | Default candidate models per role | `config.py:50-61` | verified |
| S18 | §IV-F, Tab. III | Memory write contents; retrieval bypassed by `[]` initial state | `nodes.py:1629-1654`; `runner.py:265-266`; `rag/router.py:71-77` (the Lead Editor read all three) | verified |
| S19 | §IV-G | Desktop executor wraps PyAutoGUI and psutil; not wired; interface-only test; headless fallback returns fixed size and empty screenshot | `desktop/executor.py:23-233`; grep shows only `tests/test_case_study_enhancements.py:27` imports it | verified |
| S20 | §IV-G | File helper not confined to workspace | `agent/code_executor.py:25-30` (read by the Lead Editor) | verified |
| S21 | §IV-G, Tab. II | Everything else in IV-G is a design | `02_local_system_extension.md` Part 2 | verified (labelled Proposed) |
| S22 | §V, Tab. III | `enable_verification` unread | grep: only `api/health.py:48`, `experiment/runner.py:52` | verified |
| S23 | §V | `--eval` runs absent `scratch/` scripts; ablation runner imports a missing function | `main.py:608-622`; `experiment/runner.py:82-83` vs `graph.py:9` | verified |
| S24 | §V | Certification PASS criterion | `scripts/certify.py:40-44` | verified |
| S25 | §V | Evidence layout; overwrite on retry; no integrity protection | `evidence/manager.py`; `nodes.py:986-991,1170-1174` | verified (A1 §8) |
| S26 | §VIII | Approval triggers; re-check at completion; one approval covers the task | `security/approval.py:5-16`; `nodes.py:1499`; `runner.py:85` | verified |
| S27 | §VIII | Audit logs model calls only; locality logged, not enforced | `security/audit.py:51-106`; `llm/gateway.py:113-120` | verified (A1 §10) |
| S28 | §VIII | Title, URL, screenshots not sanitized | `nodes.py:654-677` | verified (A1 §10) |
| S29 | §VIII | Browser flags: automation-detection disabled, UA spoofed, webdriver hidden, `--no-sandbox` | `browser/pool.py:90-93,127,138` | verified (A1 §10) |
| S30 | §VIII | CAPTCHA resume refused while present; fallback engines; no solver | `runner.py:106-189` | verified (A1 §10) |
| S31 | §III | One-time downloads include the vector store's default embedding model on first use | chromadb library default embedding function (not in repo code; no `embedding_function` passed at `memory/provider.py:61`) | verified as library behaviour, **author to confirm** for the installed chromadb version |
| S32 | §III | Observatory issues only reads; no command channel | `observatory/backend/storage.py:32-52`; `backend/api/observability.py:95-100` | verified (A1 §11) |
| S33 | Tab. I (ours) | Loc Y, Web Y, Desk P, Gate Y, Evid Y, Mem P, Inj P, Appr P | S13–S30 above | verified |
| S34 | §VI | Ollama called without temperature or seed | grep `temperature\|seed` in `llm/gateway.py`: no match | verified |
| S35 | §IX | Case-study-specific extraction code | `nodes.py:1100-1142` (read by the Lead Editor) | verified; **author action** (`\todo`) |

## Corrections after mock review (C5)

| ID | Section | Claim, now corrected | Source | Status |
|---|---|---|---|---|
| R1 | §III | Browser is headed by default | `config.py:22`, `pool.py:86-91` | verified |
| R2 | §III, §V | Checkpoints are used only when re-scheduling after approval or CAPTCHA; there is no crash resume | `runner.py:85,96-104,138,188,229` | verified |
| R3 | §IV-B | Selector precedence: the injected id is always used | `browser/executor.py:309-316`, `dom.py:166` | verified |
| R4 | §IV-B | The vision model receives the action verb and target | `nodes.py:758` | verified |
| R5 | §IV-D | Shared retry counter; `replan` reachable only via shortcuts | `nodes.py:1369`; `engine.py:98-112` | verified |
| R6 | §IV-E, §VII-B | Substring keywords; stickiness uses the router's own last choice; recovery routed but no LLM call; vision bypasses the router | `analyzer.py:28-31,115`; `router.py:121`; `engine.py:114-200`; `fallback.py:58-80` | verified (and probed) |
| R7 | §IV-F | Memory is not in the untrusted banner; knowledge retrieval is also inert | `context_builder.py:108-120,139`; `runner.py:265-266` | verified |
| R8 | §IV-C | ŷ = final_answer or the planner's reasoning; Φ runs after each successful action for one-step plans | `nodes.py:1431-1448` | verified (and measured, N3) |
| R9 | §V | Verification records are rewritten on each update and reset on a JSON error | `evidence/manager.py:87-104` | verified (A1 §8; reviewer) |
| R10 | §V | Extraction handler fabricates campus facts | `nodes.py:1100-1142` | verified |
| R11 | §VIII | Risk label comes from the task text only; approval is once per task; no API authentication; locality flag is a substring test | `nodes.py:94-99,257-281`; `approval.py`; `backend/main.py`; `audit.py:68` | verified |
| R12 | §VIII | The CAPTCHA fallback loads result URLs directly | `runner.py:155-176` | verified (reviewer; the Lead Editor read `runner.py:141-189` via A1 §10) |
| R13 | §VIII | The DOM extractor writes `data-pilot-id` into pages | `dom.py:152-153` | verified |
| R14 | Tab. I | Gate cells for WebArena, WebVoyager, OSWorld and AgentDojo changed to N; ours to P | column definition in the Table I caption | verified |

## Post-fix claims (code at commit `5359458`; the paper cites `eb3803e`, which only adds `no_memory` to the default `--eval` presets)

The paper now describes the fixed code. The rows below supersede N1–N5, N9, N11, N15 and the S/R rows wherever they conflict.

| ID | Section | Claim | Type | Source | Status |
|---|---|---|---|---|---|
| F1 | Abstract, §VII, Tab. IV | Before fixes: component FC 8/23, live FC 9/10 of 23, FR 3/15 | experiment | `results/verification_gate_cases_before_fixes.csv` (harness run on a `08653e2` worktree, identical agent code to `2361d50`) | verified |
| F2 | Abstract, §VII, Tab. IV | After fixes: FC 3/23 and FR 1/15 in all three modes (misses C4, P3, N8; FR X6) | experiment | `results/verification_gate_cases.csv` | verified |
| F3 | Abstract, §VII, Tab. IV | Held-out (12 states, 5 unsatisfied): FC 4 before and 3 after; FR 1 (H7) both times; misses H1, H3, H11 | experiment | both CSVs, `split=held_out` | verified |
| F4 | Abstract, §VII | Median 30.6 ms over 35 full decisions (max 39.5); 3 pre-check stops ≤ 6.3 ms | experiment | `results/verification_gate_run.log` | verified |
| F5 | §VII-B | Keyword probes now route to lightweight/qwen2.5:1.5b; cross-task probe gives qwen3.5:2b for a new task's planning; within-task stickiness still keeps deepseek-r1:1.5b | experiment | `results/routing_resolution.csv` (after), `routing_resolution_before_fixes.csv` | verified |
| F6 | §VII-C | 129 tests in 25 files: 126 pass, 3 fail (live web needed; one also needs Ollama); 0 errors; Observatory 20/20; coverage 65.0% (3,256/5,009 lines) | experiment | `results/junit_after_fixes.xml`, `pytest_after_fixes.txt`, `coverage_after_fixes.txt` | verified |
| F7 | §V | 10,867 backend lines, 1,679 in `nodes.py` | code | `wc -l` on the working tree at `5359458` | verified |
| F8 | §V, §IV | Fix list (extraction, gate, CAPTCHA, regex, flags, recovery, memory, routing, eval runner, sampling) | code | `git show 5359458`; `tests/test_verification_fixes.py` | verified |
| F9 | §IV-D | Only `vision_fallback` changes behaviour; `alternative_selector` and `replan` remain labels | code | `nodes.py` `plan_action_node` (`forced_vision`); no other consumer of `recovery_strategy` | verified |
| F10 | §IV-F, §VIII | Retrieval now runs; memory is not bannered or sanitized | code | `runner.py` (None seeding); `rag/context_builder.py:108-120` | verified (code); effect not measured |
| F11 | §VI | Presets exist for all six configurations; `--eval` runs them | code | `experiment/config.py`; `main.py` `run_eval` | verified (code); **not run with a model** |

## Computer-use reframing claims (paper at `eb3803e` code)

| ID | Section | Claim | Source | Status |
|---|---|---|---|---|
| CU1 | Title, Abstract, §I | The agent is **toward** computer use; the implemented backend is the browser only | `10_computer_use_audit.md` rows 1, 2, 6, 9–13 | verified |
| CU2 | §III Tab. II | Browser postconditions are Impl.; the file exists/size predicate is Unit (tested, not called); all others are Prop. | `verification/manager.py` `verify_file_state`; `tests/test_case_study_enhancements.py:127-132`; grep shows no caller | verified |
| CU3 | §IV-A | The loop's observation and execution nodes are browser-bound | `graph.py` nodes `navigate`, `extract_dom`; `nodes.py` `execute_action_node` uses `PlaywrightExecutor` | verified |
| CU4 | §IV-C | The desktop executor (PyAutoGUI, psutil), file helper and file predicate exist and are not connected | `desktop/executor.py:47-233`; importers: tests only | verified |
| CU5 | §V | Tauri native commands only report backend and Ollama status | `src-tauri/src/*.rs` `#[tauri::command]` | verified |
| CU6 | §V Tab. III | Status of 17 capabilities | `10_computer_use_audit.md` | verified |
| CU7 | §VI Tab. V | The protocol is proposed; only the browser family is runnable; safety is partly runnable (browser injection and approval) | code; no computer backend | verified (as a statement of status) |
| CU8 | §IX | The agent exposes no file, process, window or command action | `prompts.py:28-35` action list; `nodes.py` dispatch | verified |
| CU9 | §IX | Evidence screenshots are not redacted | no redaction code in `evidence/manager.py` or `nodes.py` | verified |

## Claims about other work

See `06_citation_audit.md` (32 rows). All citations are verified at abstract or venue level; four are flagged for a full-PDF re-read.

## Removed or softened during drafting (unsupported)

- README claims **not used**:
  - "zero exfiltration";
  - "PrivacyAuditor logs outbound requests";
  - "anti-thrashing cooldown";
  - "episodic strategy learning informs planning";
  - "immutable evidence";
  - "desktop task automation" (as implemented);
  - "cryptographic audit trails".
- Repo result files **not used**: `CERTIFICATION_REPORT.md` (committed as 1/5 PASS in `6a47c8b`, then 5/5 in `e812a71`, with no run log), `VISION_VALIDATION.md` (hard-coded text), the `benchmarks/run.py` template (hard-coded "Simulated" figures), and `MEMORY_VALIDATION.md` (a one-document store).
- Intro: "Most assistants send each observation to a hosted model" became "Several of the agents reviewed … [4 cites]".
- Architecture: "the only outbound traffic" became "apart from one-time weight downloads, outbound traffic consists of …".
- Routing: the inference "every text role resolves to `qwen2.5:1.5b`" was **replaced by a measurement** (N8).
