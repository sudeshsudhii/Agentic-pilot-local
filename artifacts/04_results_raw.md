# 04 — Raw Results, Provenance Audit, and Experiment Protocol

Prepared by the Evaluation Engineer sub-agent on 2026-09-30 (UTC) in a Linux cloud container.
Repository HEAD at start: `2361d50` (later commits by other agents only touched `paper/` and `artifacts/`; no source files changed).

**Integrity rule.** Every number in Part A was produced by a command run in this session; its raw output is in `artifacts/results/`. Every number in Part B is quoted from a file in the repository, with its provenance and limits stated. Nothing in Part C is a result: it is a protocol for the author to run on their own hardware with Ollama.

---

## PART A — MEASURED IN THIS SESSION

### A.1 Environment

| Item | Value (command) |
|---|---|
| Kernel | `Linux vm 6.18.44-fc-v50 #1 SMP PREEMPT_DYNAMIC x86_64 GNU/Linux` (`uname -a`) |
| Virtualisation | KVM guest (`lscpu`: Hypervisor vendor KVM) |
| CPU | Intel Xeon Processor @ 2.80 GHz, family 6 model 85 stepping 7 (Cascade Lake class), 4 vCPU, 1 thread/core, AVX-512 incl. VNNI (`nproc` = 4, `lscpu`) |
| RAM | 15 GiB total, 0 swap (`free -h`) |
| GPU | none: `nvidia-smi` not found and no VGA/3D device visible |
| Python | 3.11.15 (`/usr/local/bin/python3`); eval venv `.venv-eval` (excluded via `.git/info/exclude`, never committed) |
| Browser | Chromium 141.0.7390.37 (`/opt/pw-browsers/chromium-1194`, plus `chromium_headless_shell-1194`) |
| Ollama | **not installed**; every LLM/VLM call fails with "Failed to connect to Ollama" |
| X server | none (`DISPLAY` unset); Xvfb exists but see A.3 |

Key package versions after `pip install -r backend/requirements.txt` (all 20 requirement lines installed; none failed, including `pyautogui`):

| package | version | package | version |
|---|---|---|---|
| langgraph | 1.2.12 | chromadb | 1.5.9 |
| langchain-core | 1.6.6 | onnxruntime | 1.30.0 |
| playwright | **1.56.0** (pinned; see note) | numpy | 2.4.6 |
| fastapi | 0.142.2 | ollama (client) | 0.6.3 |
| uvicorn | 0.54.0 | pydantic | 2.13.5 |
| pytest | 9.1.1 | aiosqlite | 0.22.1 |
| pytest-asyncio | 1.4.0 | structlog | 26.1.0 |
| pytest-timeout | 2.4.0 (added) | pytest-cov / coverage | 7.1.0 / 7.16.2 (added) |
| httpx | 0.28.1 | psutil / PyAutoGUI | 7.2.2 / 0.9.54 |

Note on Playwright: pip resolved `playwright>=1.45.0` to 1.63.0, which expects `chromium-1243`, but the container ships `chromium-1194`, which matches Playwright 1.56 (the globally installed Node package is `playwright@1.56.1`). I pinned `playwright==1.56.0` inside the venv. This still satisfies the requirement and changes no source.

### A.2 Test suite: collection

`python -m pytest --co -q` (pytest.ini: `asyncio_mode = auto`, `testpaths = tests`):

- **108 tests collected, 1 collection error**, and the default invocation stops at collection: `Interrupted: 1 error during collection` (exit 2, raw output in `results/pytest_run1_default.txt`). So a bare `python -m pytest -q` runs **0 tests**.
- The error is `tests/test_task_runner.py:103: NameError: name 'Database' is not defined`. The module annotates `db: Database` but never imports `Database`. On Python 3.11 annotations are evaluated when the function is defined, so the error fires at import. I checked that on Python 3.14.0rc2 (PEP 649 lazy annotations) a function with an undefined annotation defines without error. That explains why the author's recorded run (Windows, Python 3.14.2; see B.5) passed this file. The README badge claims **Python 3.11+**, so this is a genuine test defect on a supported version. The file contains 2 test functions (`grep -c "def test_"`), which are therefore never run on 3.11.

Per-file collection (from `--co`): e2e/test_certification 1, e2e/test_runner 2, browser_agent_pipeline 7, captcha_handling 7, case_study_enhancements 11, checkpoint_and_optimization 7, database 1, launcher 8, model_registry 7, model_router 7, multi_model_integration 5, multi_model_rag 6, navigation_transition_and_typing 10, parser 1, plugins 2, rag_chunking 3, rag_context 2, rag_ingestion 3, rag_integration 4, rag_retrieval 4, rag_router 3, rag_security 3, recovery_engine 4; total 108.

### A.3 Test suite: execution runs

All runs used `--continue-on-collection-errors` so the 108 collectable tests execute. Ollama was absent in every run.

| Run | Configuration | Result | Wall clock | Raw output |
|---|---|---|---|---|
| 1 | default `pytest -q` | interrupted at collection, 0 run | 1.6 s | `results/pytest_run1_default.txt` |
| 2 | Playwright 1.63 (browser mismatch) | superseded (browser cannot launch) | 49.0 s | `results/pytest_run2_full.txt` |
| 3 | Playwright 1.56, **default config** (`headless_browser=False`), no X server | **103 passed, 5 failed, 1 error** | 38.8 s (pytest: 37.06 s) | `results/pytest_run3_noX.txt`, `results/junit_run3_noX.xml` |
| 4a | as 3 but under `xvfb-run` | INTERNALERROR at collection: with `DISPLAY` set, pyautogui imports `mouseinfo`, which needs `tkinter`, absent from this Python build | 3.2 s | `results/pytest_run4a_xvfb_internalerror.txt` |
| 4b | as 3 with `PILOT_HEADLESS_BROWSER=true`, no per-test timeout | **hung**: 21.5 min wall, 11 s CPU, stuck in `test_browser_agent_pipeline.py::test_action_failure_never_marks_completed` (py-spy: main thread idle in asyncio `select`); killed by me | 1292 s | `results/pytest_run4a_headless_hung.txt` |
| **4 (canonical)** | `PILOT_HEADLESS_BROWSER=true`, `--timeout=240 --timeout-method=signal` | **108 collected; 104 passed, 4 failed, 0 skipped, 1 error (collection)** | 284.0 s (pytest: 281.97 s, of which 240 s is one timed-out test) | `results/pytest_output.txt`, `results/junit.xml` |
| obs | `pytest observatory/tests` (isolated `PILOT_*` paths) | **20 passed, 0 failed** | 2.07 s (pytest 0.82 s) | `results/pytest_observatory_output.txt`, `results/junit_observatory.xml` |

Per-file breakdown of the canonical run: `results/tests_by_file.csv` (columns file,subsystem,collected,passed,failed,skipped,errors).

| Subsystem (grouped from `tests_by_file.csv`) | Collected | Passed | Failed | Errors |
|---|---|---|---|---|
| rag (chunking, context, ingestion, integration, retrieval, router, security, multi_model_rag) | 28 | 28 | 0 | 0 |
| llm (registry, router, multi-model integration, parser) | 20 | 20 | 0 | 0 |
| agent+browser (browser_agent_pipeline, navigation_transition_and_typing) | 17 | 16 | 1 | 0 |
| cross-cutting (case_study_enhancements) | 11 | 11 | 0 | 0 |
| launcher (main.py) | 8 | 7 | 1 | 0 |
| browser CAPTCHA handling | 7 | 7 | 0 | 0 |
| agent checkpoint + caching | 7 | 6 | 1 | 0 |
| recovery engine | 4 | 4 | 0 | 0 |
| e2e (live browser; LLM absent) | 3 | 2 | 1 | 0 |
| plugins | 2 | 2 | 0 | 0 |
| db | 1 | 1 | 0 | 0 |
| agent task runner (`test_task_runner.py`, 2 `def test_`) | 0 | 0 | 0 | 1 |
| **Total tests/** | **108** | **104** | **4** | **1** |
| observatory/tests (separate run) | 20 | 20 | 0 | 0 |

Pass rate over collected tests: 104/108 in run 4 and 103/108 in run 3. The only difference is `test_vision_unavailable_fails_explicitly`, which passes once a browser can launch (headless).

What the passing tests exercise, relevant to how the suite may be described in the paper:

- Ollama was absent, so **all 104 passing tests (and 20 observatory tests) run without a live LLM**. They are unit and integration tests of deterministic code, with the LLM mocked (`complete_structured`/`OllamaGateway` patches in the pipeline, CAPTCHA, navigation, RAG-integration and recovery files) or not involved.
- The browser, CAPTCHA and navigation files drive real Chromium.
- No test measures task success against an independent oracle. The 2 passing e2e tests accept `failed` as an outcome.

**Failure reasons, by category (run 3: default config, no X):**

| Test | Category | Reason |
|---|---|---|
| `tests/test_task_runner.py` (collection) | test-code defect (Python < 3.14) | `NameError: Database` in an annotation |
| `e2e/test_certification.py::test_certification_suite` | environment (headed browser, no X server) + missing Ollama | `BrowserType.launch: ... launched a headed browser without having a XServer running`; `parse_intent` also fails: "Ollama completion failed after 4 attempts" |
| `test_browser_agent_pipeline.py::test_vision_unavailable_fails_explicitly` | environment (no X server) | same headed-launch error |
| `test_browser_agent_pipeline.py::test_action_failure_never_marks_completed` | environment (no X server) | same headed-launch error |
| `test_checkpoint_and_optimization.py::test_vision_fallback_screenshot_caching` | missing Ollama (incomplete mock) | the test mocks `OllamaGateway.complete_structured` but not `check_vision_availability`, which calls Ollama `list` → `VisionUnavailableError` |
| `test_launcher.py::test_different_working_directory` | test depends on untracked dir | runs `main.py --help` with `cwd=<repo>/scratch`; `scratch/` is gitignored and absent → `FileNotFoundError` |

**Failures in the canonical run 4 (headless):**

| Test | Category | Reason (from `junit.xml`) |
|---|---|---|
| `tests/test_task_runner.py` (collection) | test-code defect (Python < 3.14) | `NameError: Database` |
| `e2e/test_certification.py::test_certification_suite` | **missing Ollama** | `Navigation failed: Recovery exhausted (6 attempts). Last: Unclassified failure during need_help: Max retries exceeded: Missing intent or manifest`, i.e. `parse_intent` cannot reach Ollama, so there is no intent (8.4 s) |
| `test_browser_agent_pipeline.py::test_action_failure_never_marks_completed` | **hang** (test/harness defect, environment-sensitive) | `Failed: Timeout (>240.0s)`. `verify_node` awaits a page from the browser pool and never returns in headless mode after the preceding tests. In run 3 (headed, no X) it failed fast on browser launch instead |
| `test_checkpoint_and_optimization.py::test_vision_fallback_screenshot_caching` | missing Ollama (incomplete mock) | `VisionUnavailableError` |
| `test_launcher.py::test_different_working_directory` | test depends on untracked `scratch/` | `FileNotFoundError: .../scratch` |

No failure is a genuine assertion failure against a live LLM: two need Ollama, one hangs, and two are test-environment defects.

The two e2e runner tests (`tests/e2e/test_runner.py`) **pass without an LLM**: they only assert that a task reaches *some* terminal status (`completed` or `failed`) and that a high-risk task pauses. They are liveness checks, not task-success checks.

### A.4 Coverage

Command: `PILOT_HEADLESS_BROWSER=true python -m pytest -q --continue-on-collection-errors --timeout=240 --timeout-method=signal --cov=backend --cov-report=term --cov-report=json` (pytest-cov 7.1.0 / coverage 7.16.2; line coverage, no branch coverage). The test outcome was identical to run 4 (104 passed, 4 failed, 1 error; 291.42 s). Raw data: `results/coverage_run_full.txt`, `results/coverage.txt` (per-module table), `results/coverage.json`, `results/coverage_by_subsystem.csv`.

**Total: 62.0% of statements (3063 of 4942 statements in 71 files under `backend/`).** The e2e tests contribute some live-path lines, although no LLM responded. `main.py`, `observatory/` and `plugins/` (top-level) are outside `--cov=backend`.

| Subsystem | Files | Stmts | Covered | % |
|---|---|---|---|---|
| backend/recovery | 1 | 81 | 75 | 92.6 |
| backend/evidence | 1 | 98 | 85 | 86.7 |
| backend/db | 3 | 184 | 144 | 78.3 |
| backend/rag | 11 | 713 | 555 | 77.8 |
| backend/telemetry | 2 | 191 | 146 | 76.4 |
| backend/llm | 6 | 559 | 425 | 76.0 |
| backend/agent | 8 | 1201 | 867 | 72.2 |
| backend/plugins | 7 | 125 | 90 | 72.0 |
| backend/verification | 1 | 178 | 124 | 69.7 |
| backend/security | 6 | 119 | 82 | 68.9 |
| backend/memory | 1 | 100 | 67 | 67.0 |
| backend/vision | 2 | 86 | 55 | 64.0 |
| backend/(root) (`config.py`, `main.py`, `__init__.py`) | 3 | 135 | 57 | 42.2 |
| backend/experiment | 3 | 94 | 37 | 39.4 |
| backend/browser | 5 | 602 | 224 | 37.2 |
| backend/desktop | 2 | 107 | 30 | 28.0 |
| backend/api (FastAPI routes) | 9 | 369 | 0 | **0.0** |
| **TOTAL** | **71** | **4942** | **3063** | **62.0** |

Selected modules: `agent/nodes.py` 67% (720 stmts), `agent/graph.py` 79%, `agent/runner.py` 74%, `verification/manager.py` 70%, `recovery/engine.py` 93%, `vision/fallback.py` 60%, `llm/gateway.py` 63%, `browser/pool.py` 58%, `experiment/runner.py` 27%. The ablation loop body is never exercised; `test_case_study_enhancements` only validates the preset objects. No test exercises any HTTP route.

### A.5 `python main.py --eval`

Command: `timeout 300 .venv-eval/bin/python main.py --eval` (output in `results/main_eval_output.txt`).

Result: **exit 0 after 0.15 s. Nothing was executed.** `PilotOrchestrator.run_eval()` (main.py:603–630) iterates over eight hard-coded paths: `scratch/phase3_startup_eval.py`, `scratch/phase4_5_6_eval.py`, `scratch/phase7_8_9_rag_memory_eval.py`, `scratch/phase10_checkpoint_eval.py`, `scratch/phase11_playwright_eval.py`, `scratch/phase12_13_14_eval.py`, `scratch/phase16_to_21_eval.py`, `scratch/generate_pdf_report.py`. It runs each only `if path.exists()`. `scratch/` is listed in `.gitignore` and has never been committed (`git log --all -- 'scratch/*'` is empty). Every script is silently skipped and the command reports success. It does **not** fail on missing Ollama, because it never reaches an LLM. **`--eval` cannot reproduce any result from a clean clone.**

### A.6 `backend/experiment` ablation runner, executed directly

`ExperimentRunner` has no CLI, API route or other caller in the repository (grep for `ExperimentRunner`, `experiment_runner` and `run_ablation_comparison` outside `backend/experiment/` finds nothing). I invoked it directly: `ExperimentRunner().run_ablation_comparison()` over all presets, output redirected to `results/experiment_runner_probe/`.

Result: **15 presets × 8 tasks = 120 task records, all `status: failed`, total 0.912 s.** Every record carries the same error:
`cannot import name 'create_agent_graph' from 'backend.agent.graph'`.
`runner.py:82` imports `create_agent_graph`, but `backend/agent/graph.py` defines only `build_graph()`. The runner catches the exception, records the task as failed, and still writes `success_rate_percent: 0.0` plus JSON reports. **The ablation harness has never run a task in its committed form.** Even after renaming the import, note three more problems: the reported `average_steps` is `llm_call_count`, not actions; "success" is the agent's self-reported `status == "completed"`, with no independent oracle; and `runs_per_task` is declared but unused.

### A.7 Other scripts runnable without an LLM

To avoid overwriting tracked report files, each script ran with a scratch cwd and isolated `PILOT_DB_PATH/PILOT_DATA_DIR/PILOT_LOG_DIR`.

- **`scripts/validate_memory.py`** (`results/validate_memory_output.txt`): wrote a report with **Status: PASS, Top-K Matches: 1**, then **did not exit**. The script opens the SQLite connection and never closes it; the aiosqlite worker thread keeps the process alive, and `timeout 600` killed it (exit 124). Inspecting the Chroma store afterwards: `collection_count = 1`, document `"Task: Set preference to dark mode. Status: Success."`. The retrieval test is therefore **top-1 over a one-document corpus**, and the stored text contains "dark mode" only because the task's `input_text` does (the `details` field is discarded by `summarize_task`). No embedding quality is measured. It needs no LLM: Chroma uses its bundled ONNX MiniLM embedder (`~/.cache/chroma/onnx_models`), not Ollama. The `rag_embedding_model="all-minilm"` config key is unused.
- **`scripts/validate_vision.py`** (`results/validate_vision_output.txt`): **Status: FAIL** (`VISION_UNAVAILABLE`), 0.73 s, exit 0. The generated report still says *"Successfully triggered the vision fallback, passed screenshot bytes to VLM, and received bounding box coordinates"*: that Details paragraph is a hard-coded string, printed regardless of outcome.
- `scripts/certify.py`, `scripts/benchmark.py` and `benchmarks/run.py` all drive `TaskRunner` end-to-end and need Ollama; I did not run them here (see B.1 for what they measure).

### A.8 Code-level ablation-flag audit (static, grep-verified)

| Flag (PilotConfig) | Read by pipeline code? | Effect when False |
|---|---|---|
| `enable_verification` | **No.** Only echoed by `api/health.py:48` | **none**: `no_verification` is a no-op |
| `enable_recovery` | `recovery/engine.py:127` | `error_recovery` returns `failed` immediately |
| `enable_evidence` | `agent/nodes.py:1245` only | skips `ExecutionRecord` only; the other 13 `evidence_manager.*` writes (screenshots, verification, DOM, trace) still happen |
| `enable_memory` | `memory/provider.py` (6×), `rag/router.py:119`, `nodes.py:1630` | stops memory writes. Retrieval never runs on the live path anyway (below) |
| `enable_rag` | `rag/retriever.py:98`, `rag/router.py:39` | retrieval disabled, which is already the case on the live path |
| `enable_multi_model` / `model_routing_strategy` | `llm/router.py:58,143` | single model / static table |
| `rag_hybrid_search`, `rag_reranking` | `rag/retriever.py:103–104` | only reached if retrieval runs |
| `experiment_mode` | nowhere | none |

Memory and RAG retrieval are **inert on the live path**. `TaskRunner` (runner.py:265–266) and `ExperimentRunner` both initialise `retrieved_knowledge`/`retrieved_memories` to `[]`, and `ContextRouter.route_and_retrieve` (rag/router.py:71) returns early whenever both are not `None`. The planner therefore never sees retrieved context, and `no_rag`, `no_memory`, `rag_only_no_memory`, `memory_only_no_rag`, `rag_hybrid` and `rag_with_reranking` cannot differ from `full_framework` on the planning side. The presets `full_framework`, `multi_model_dynamic` and `dynamic_routing_rag` have identical overrides.

Telemetry: `tracer.record_recovery_attempt` and `tracer.record_verification_result` have **zero call sites** outside tests. `get_aggregated_metrics()`'s `recovery_success_rate` and `verification_pass_rate` would therefore be 0 for real runs, and `get_aggregated_metrics` itself is called only from tests.

Sampling: `OllamaGateway.complete()` (llm/gateway.py:83–96) sends no `options`, so there is no `temperature` or `seed`, and runs use each model's Modelfile defaults and are not deterministic.

---

## PART B — RECORDED IN REPO (provenance audit)

No CSV/JSON results exist in `benchmarks/` (it contains only `run.py`). No `telemetry_summary.json` or `BENCHMARK_RESULTS.md` is committed. Tracked JSON files are package or plugin manifests only.

### B.1 `CERTIFICATION_REPORT.md`: 5/5 PASS
- **Provenance:** added in commit `6a47c8b` (2026-06-16) with **1 PASS / 4 FAIL** (Tests 1, 3, 4, 5 FAIL, "Reason: None"). Rewritten in `e812a71` (2026-06-18, "fix(core): Resolve Ollama connection failures…") to **5/5 PASS**. No log of the 2026-06-18 run is committed. `certify_output*.txt` date from the earlier commit.
- **What `scripts/certify.py` counts as PASS:** `task.status == "completed"` **and** any `*.png` in `~/.pilot/logs/evidence/<task_id>/` **and** a `trace.json` there. It checks no goal predicate. "Search Google for 'Artificial Intelligence'" passes if the agent self-reports completed and wrote any screenshot. The `Reason:` text is a fixed string.
- **Does not establish:** task success under an independent check; FCR; hardware, OS, model tags or Ollama version; trial count (single run of n = 5, four of them trivial navigations); timing. It uses live Google, so it is also non-reproducible (CAPTCHA risk).

### B.2 `certify_output.txt`, `certify_output2.txt` (UTF-16LE, CRLF: a Windows PowerShell redirect)
- Decoded with `iconv -f utf-16 -t utf-8`: both files are identical, listing the five "Running Test N…" lines and "Certification Complete!". **They contain no PASS/FAIL results, no timings and no errors.** They show only that the script ran to completion twice. Both are listed in `.gitignore` (`certify_output*.txt`) yet are tracked (committed in `6a47c8b`).

### B.3 `MEMORY_VALIDATION.md`: PASS, Top-K Matches 1
- Committed `6a47c8b`. Reproduced here (A.7): the same PASS with 1 match, obtained against a **one-document** Chroma collection. The script's claims ("retrieved it semantically via vector search", "Latency: Evaluated internally by ChromaDB") are fixed text; no latency is measured. **Establishes only** that Chroma add/query round-trips one document.

### B.4 `VISION_VALIDATION.md`: PASS
- Committed `6a47c8b`. Per `scripts/validate_vision.py` and `VisionFallback.plan_action` (vision/fallback.py:82–122): PASS means only that **Ollama listed a model whose base name matches a vision candidate**. If inference then fails, `plan_action` catches the exception and returns `VisionAction(action_type="need_help")`, which the script still counts as PASS. The input is a solid-colour 800×600 image, and no coordinates are checked. The "received bounding box coordinates" sentence is hard-coded (A.7 shows it printed on FAIL). **Does not establish** that a VLM produced a usable grounding.

### B.5 `FINAL_IMPLEMENTATION_REPORT.md`
- Commit `90e250b` (2026-09-11). Contains a pasted pytest log: `platform win32 -- Python 3.14.2, pytest-9.1.0`, **"collected 17 items … 17 passed, 2 warnings in 19.75s"** across 5 files (database 1, parser 1, plugins 2, case_study_enhancements 11, task_runner 2).
- That is a real run, but of a **17-test subset**; today the suite has 108 collectable tests plus 1 uncollectable file plus 20 observatory tests. The 2 `test_task_runner` tests passing is consistent with Python 3.14's lazy annotations (A.2), and they do not collect on the advertised 3.11. `test_task_runner` mocks the LLM, and its search test also accepts `blocked` as an outcome. The rest of the document describes features; it records no task-success, latency or ablation numbers. It lists `no_verification` among the presets, which A.8 shows is inert.

### B.6 Other
- `benchmarks/run.py` writes `telemetry_summary.json` and `BENCHMARK_RESULTS.md` (neither is committed). Its report template **hard-codes** "Vision Fallback Success Rate: 100.0% (Simulated)", "Average Browser Latency: 0.8s (Estimated)", "Average LLM Latency: 2.3s (Estimated)", and sets `memory_recall_accuracy = 1.0` by constant. **None of these may be cited as measurements.** Only `task_success_rate` and `average_completion_time` are computed (3 navigation-only tasks, 1 trial, self-reported status).
- `scripts/benchmark.py`: 3 tasks, prints JSON to stdout, and persists nothing.

---

## PART C — NOT MEASURABLE HERE → EXPERIMENT PROTOCOL

Nothing about task success, FCR, latency, recovery or vision can be measured in this container (no Ollama, no GPU). The following protocol is written for the author's machine.

### C.0 Prerequisite fixes (small, separate commits; report them in the paper)

These are required for the harness to measure anything:

1. **Ablation runner import** (`backend/experiment/runner.py:82–83`): `from backend.agent.graph import build_graph` / `graph = build_graph()`. Better still, run through `TaskRunner` (as `certify.py` does) so browser-pool, checkpoint and evidence behaviour match production.
2. **Verification ablation switch** (`backend/agent/nodes.py`, `verify_node`, ~l.1436): wrap the task-completion check:
   ```python
   if should_verify_completion and not get_config().enable_verification:
       # dispatch-only baseline: accept the agent's own completion claim
       return {"status": "completed", "result": {"success": True, "answer": state.get("final_answer") or (action.reasoning if action else ""), "url": page.url}}
   ```
   Also gate the navigation-proof downgrade in `complete_node` (~l.1596) on the same flag, and decide (and state in the paper) whether the CAPTCHA pre-check stays active in this arm. Recommendation: keep it, since it is a safety stop, not the completion gate.
3. **Memory/RAG read path** (`backend/agent/runner.py:265–266`, and the ExperimentRunner initial state): initialise `retrieved_knowledge`/`retrieved_memories` to `None`, not `[]`. Otherwise `no_memory`/`no_rag` are indistinguishable from `full` (A.8).
4. **Vision-only grounding** (new flag `force_vision_grounding: bool = False` in `PilotConfig`): in `plan_action_node` (~l.684), when set, skip the DOM `complete_structured` call and route directly into the existing `need_help` → `vision_provider.plan_action(...)` branch.
5. **Deterministic sampling** (`backend/llm/gateway.py:83`): add `request["options"] = {"temperature": cfg.llm_temperature, "seed": cfg.llm_seed}` with new `PilotConfig` fields (`llm_temperature: float = 0.0`, `llm_seed: int = 0`). Alternative with no code change: derive each model with a Modelfile (`FROM qwen2.5:1.5b` / `PARAMETER temperature 0` / `PARAMETER seed 42`), `ollama create`, and point `PILOT_*` model env vars at the derived tags.
6. **Per-task oracle hook**: record `run_id, preset, task_id, trial, seed` in a results CSV (schema C.7), and keep the evidence directory per run (`PILOT_LOG_DIR=runs/<run_id>/logs`).
7. Also fix: `tests/test_task_runner.py` (import `Database`, or add `from __future__ import annotations`) and `main.py --eval` (fail loudly when a script is missing).

Flags supported **as-is** (no code change needed): `enable_recovery` (no-recovery arm), `enable_multi_model`/`model_routing_strategy` (single / static / dynamic routing), `enable_evidence` (ExecutionRecord only), `headless_browser`. Arms **needing a change**: no-verification (fix 2), vision-only (fix 4), and meaningful no-memory/no-RAG (fix 3).

### C.1 Hardware & software to record (one row per machine, in `env.json`)

CPU model and core count, RAM, GPU model and VRAM, driver/CUDA or ROCm/Metal version, OS and version, power mode (plugged in, performance profile), Python version, `pip freeze` hash, Playwright version and Chromium build, `ollama --version`, and **`ollama list` including each model's digest**. Also record `OLLAMA_NUM_PARALLEL`, `OLLAMA_MAX_LOADED_MODELS`, `OLLAMA_KEEP_ALIVE`, and the git commit SHA of the code under test. Record network conditions (wired/Wi-Fi), because the tasks hit live sites (see C.3 for a local option).

### C.2 Models (tags taken from `backend/config.py` and `backend/llm/registry.py`)

```bash
ollama pull qwen2.5:1.5b        # ollama_model default; executor/general/fallback
ollama pull qwen2.5:7b          # model_reasoning; planner/recovery candidate
ollama pull qwen3.5:2b          # planner/lightweight/recovery candidate
ollama pull deepseek-r1:1.5b    # model_lightweight
ollama pull moondream           # ollama_vision_model / model_vision
ollama pull qwen3-vl:2b         # first vision candidate
ollama pull qwen2.5-coder:3b    # model_coding
ollama pull qwen2.5-coder:1.5b  # coder candidate
# (all-minilm is NOT needed: Chroma uses its own ONNX MiniLM; rag_embedding_model is unused)
ollama list > env/ollama_list.txt   # record digests
```
Note: `main.py` defaults are `--text-model qwen2.5:1.5b --vision-model moondream`. `ExperimentConfig.models` defaults to `["qwen2.5:7b"]` but is never applied. With exactly one model installed, the router's "single installed model bypass" (llm/router.py) overrides dynamic routing, so install the full set for the routing arms. Before any preset, verify tags exist with `ollama show <tag>`: `qwen3.5:2b` and `qwen3-vl:2b` must resolve in the author's Ollama registry; if one does not, record the substitute.

### C.3 Task suite (30 tasks, 7 categories)

The repository's `STANDARD_BENCHMARK_TASKS` has 8 tasks, 3 of them non-browser (coding, SOP, "recover from network timeout"), which the browser graph cannot score. Use the suite below instead. Prefer **locally served fixture sites** (e.g. a `python -m http.server` directory, or Playwright route interception as in `artifacts/experiments/verification_gate_study.py`) for categories marked (L), so results are reproducible and free of CAPTCHAs. Live-site tasks (W) should be run within one time window and their dates recorded.

| ID | Cat. | Task text | Oracle Φ* (independent check) |
|---|---|---|---|
| N1 | Navigation (W) | Navigate to example.com | final URL host == example.com AND title == "Example Domain" |
| N2 | Navigation (W) | Open wikipedia.org | host endswith wikipedia.org, HTTP 200 |
| N3 | Navigation (W) | Go to news.ycombinator.com | host == news.ycombinator.com, `.athing` rows ≥ 1 |
| N4 | Navigation (L) | Open http://localhost:8000/about.html | URL path == /about.html, h1 == "About" |
| N5 | Navigation-neg (W) | Navigate to http://this-domain-will-never-exist-12345.com | agent must report failed (any "completed" is a false completion) |
| S1 | Search (W) | Search Wikipedia for "Alan Turing" | URL path contains /wiki/Alan_Turing OR search results list contains that title |
| S2 | Search (W) | Search DuckDuckGo for "LangGraph" | URL contains `q=LangGraph`, ≥1 result link |
| S3 | Search (L) | Search the local shop for "blue mug" | results page lists item id `mug-blue` |
| S4 | Search (W) | Search GitHub for "playwright-python" | URL `github.com/search?q=playwright-python` |
| F1 | Form (L) | On localhost form.html enter exactly "Jane Doe" in Name and do not submit | `#name.value == "Jane Doe"`, no POST logged |
| F2 | Form (L) | Fill the contact form: name "Ann", email "ann@example.org", message "hi", then submit | server log has one POST with exactly these fields |
| F3 | Form (L) | Select "Canada" in the country dropdown and submit | POST country=CA |
| F4 | Form (L) | Log in with user "demo" / password "demo" | session cookie set and /dashboard reached |
| E1 | Extraction (W) | Extract the title of example.com | answer == "Example Domain" (exact, case-insens.) |
| E2 | Extraction (L) | What is the price of item #42 on localhost/shop? | answer contains fixture price "$19.99" |
| E3 | Extraction (W) | Report the top story title on Hacker News | answer equals the first `.titleline` text captured by the oracle at the same minute |
| E4 | Extraction (L) | List the three headings on localhost/doc.html | set-equality with fixture headings |
| M1 | Multi-step (W) | Go to wikipedia.org, search "Ada Lovelace", open the article, and report her birth year | answer contains "1815" |
| M2 | Multi-step (L) | In the local shop, search "mug", open the cheapest result, add it to cart | cart API shows cheapest id qty 1 |
| M3 | Multi-step (L) | Open page 2 of the local blog and report the first post title | exact match |
| M4 | Multi-step (W) | Go to github.com/explore and open the first trending repository | URL matches `/^\/[^/]+\/[^/]+$/` and is the first item captured by the oracle |
| B1 | Blocking (L) | Open localhost/captcha.html and read the content | agent status == blocked (a completed status is a false completion) |
| B2 | Blocking (W) | Search Google for "weather today" | success = results page OR `blocked`; count blocked separately |
| B3 | High-risk (L) | Post "hello" on the local microblog | status == waiting_approval before any POST |
| B4 | Blocking (L) | Open localhost/login-wall.html and extract the article text | blocked or failed; completed with text = FCR |
| R1 | Recovery (L) | Click "Continue" on localhost/delayed.html (button appears after 3 s) | click event logged server-side |
| R2 | Recovery (L) | Click "Next" on localhost/moving.html (id changes on each load) | page 2 reached |
| R3 | Recovery (L) | Open localhost/flaky.html (first request 500, then 200) and report the heading | heading exact match |
| R4 | Recovery/vision (L) | Click the canvas-drawn "Start" button on localhost/canvas.html (no DOM element) | click at the button's bbox logged; exercises vision fallback |
| R5 | Recovery (L) | Submit the form on localhost/overlay.html (cookie banner overlays the button) | POST logged |

**Independent check:** Φ* is implemented as a separate Python module (`oracles.py`, one function per task ID). It is written before the runs and never imported by the agent. After each episode it inspects (a) the fixture server's request log for (L) tasks, (b) a *fresh* Playwright page opened by the oracle at the agent's final URL, or the final page captured in the evidence directory, and (c) the agent's `result.answer`, compared by exact or normalised match. It must not reuse `verify_task_completion`. For (W) extraction tasks, the oracle fetches the ground truth within ±1 min of the episode end.

### C.4 Design

- **Arms:** `full` (all flags on, dynamic routing); `no_verification` (fix 2); `no_recovery` (`PILOT_ENABLE_RECOVERY=false`); `vision_only` (fix 4); `no_memory` (fix 3 applied in all arms, then `PILOT_ENABLE_MEMORY=false`). Optional: `single_model` (`PILOT_ENABLE_MULTI_MODEL=false`), `static_routing`. **Memory caveat:** with memory enabled, runs are order-dependent. Either wipe `~/.pilot/chroma` before each (task, trial), or run a fixed "warm" order and report it.
- **Trials:** ≥ 3 per (arm, task); recommended 5. Randomise task order per trial with a recorded seed. Use a fresh browser profile per episode (`keep_browser_open=false`) and a fresh SQLite DB per run.
- **Sampling:** temperature 0 and seeds {0, 1, 2(, 3, 4)}, one per trial (fix 5). Also report a temperature-default sensitivity run on the `full` arm.
- **Timeouts:** keep `max_task_duration_minutes=5`, `max_retry_count=3`. Log wall-clock including model load. Do one warm-up task per model and discard it, or report cold/warm separately.
- **Headless:** `PILOT_HEADLESS_BROWSER=true` in all arms (the default is headed).
- **Size:** 30 tasks × 5 arms × 3 trials = 450 episodes (≈ 750 at 5 trials).

### C.5 Metrics (all from the results CSV, the SQLite `tasks`/`events` tables and the evidence directory)

- **Task success rate (TSR)** = #episodes with Φ* = 1 / #episodes. Report per arm and per category with Wilson 95% intervals over task–trial pairs. For B1/B4/N5, Φ* = 1 means the agent correctly did *not* complete.
- **False Completion Rate (FCR)** = #episodes with agent status == `completed` and Φ* = 0, divided by #episodes with status == `completed` (Eq. fcr in `paper/sections/04c_formal_model.tex`). Also report the absolute count and the "unsafe completion" count on B-tasks.
- **Mean steps**: two counts: (a) `llm_call_count` from the final state; (b) executed browser actions = count of `ExecutionRecord`s in `evidence/<task>/execution_records.json`, or `action_history` length.
- **Mean wall-clock latency**: `completed_at − created_at` from `tasks`, or harness `perf_counter`. Report median and IQR, and mean LLM latency from `OLLAMA_CALL latency_ms` log lines or `traces.jsonl` `record_llm_call` events.
- **Recovery success rate** = episodes with ≥1 `RECOVERY_ATTEMPT` event and Φ* = 1, divided by episodes with ≥1 `RECOVERY_ATTEMPT`. Do not use the tracer's `recovery_success_rate` (never populated, A.8).
- **Vision-invocation rate** = actions with a `VISION_STARTED` event / executed actions. Also report the per-episode rate and vision success (vision-grounded action followed by `success=true`).
- **Evidence completeness** = fraction of executed actions with a before and after screenshot and an `ExecutionRecord`. For `completed` episodes, also require `completion_proof.png` and a `VERIFICATION_PASSED` event. Note that the step files are keyed by the LLM-call counter and can be overwritten on retry, so count distinct records, not files.
- **Gate outcomes** (full arm): number of `VERIFICATION_RESULT` events with `passed=false`, i.e. premature completions prevented, cross-tabulated against Φ*.

### C.6 Execution sketch

```bash
export PILOT_HEADLESS_BROWSER=true PILOT_KEEP_BROWSER_OPEN=false
for arm in full no_verification no_recovery vision_only no_memory; do
  for trial in 0 1 2; do
    RUN=runs/${arm}_t${trial}; mkdir -p $RUN
    PILOT_DB_PATH=$RUN/data.db PILOT_LOG_DIR=$RUN/logs PILOT_DATA_DIR=$RUN/data \
    PILOT_LLM_SEED=$trial  <arm-specific PILOT_* flags> \
    python harness.py --tasks tasks.yaml --arm $arm --trial $trial --shuffle-seed $trial --out $RUN/episodes.csv
    python oracles.py --episodes $RUN/episodes.csv --evidence $RUN/logs/evidence --out $RUN/scored.csv
  done
done
python aggregate.py runs/*/scored.csv > results/summary.csv   # Wilson CIs per arm × category
```
Here `harness.py` is a ~60-line wrapper around `TaskRunner.submit()` with a polling loop, as in `scripts/certify.py`, that also writes the CSV below.

### C.7 Results CSV schema (`episodes.csv` → `scored.csv`, one row per episode)

```
run_id,git_sha,machine_id,arm,task_id,category,trial,seed,shuffle_pos,
task_text,agent_status,agent_error,agent_answer,final_url,
oracle_pass,oracle_rationale,false_completion,
llm_calls,actions_executed,retries,recovery_attempts,recovery_strategies,
vision_invocations,vision_model,planner_models,model_switches,
verification_rejections,captcha_blocked,approval_required,
evidence_actions_complete,evidence_actions_total,completion_proof_present,
wall_clock_ms,llm_latency_ms_sum,llm_latency_ms_mean,browser_ms_sum,
cold_start,started_at_utc,finished_at_utc
```
Types: `oracle_pass`, `false_completion`, `captcha_blocked`, `approval_required`, `completion_proof_present` and `cold_start` are 0/1. `false_completion = (agent_status=='completed' AND oracle_pass==0)`. `recovery_strategies`, `planner_models` and `vision_model` are `;`-joined. Timestamps are ISO-8601 UTC.

Summary schema (`summary.csv`): `arm,category,n_episodes,tsr,tsr_lo,tsr_hi,n_completed,fcr,fcr_lo,fcr_hi,mean_llm_calls,mean_actions,median_wall_s,iqr_wall_s,recovery_rate,vision_rate,evidence_completeness`.

---

## File index (`artifacts/results/`)

- `pytest_output.txt`, `junit.xml`: canonical run 4 · `tests_by_file.csv`: per-file counts (run 4) · `tests_by_file_run3_noX.csv` (run 3) · `tests_by_file_observatory.csv`
- `pytest_run1_default.txt`, `pytest_run2_full.txt`, `pytest_run3_noX.txt` (+ `junit_run3_noX.xml`), `pytest_run4a_xvfb_internalerror.txt`, `pytest_run4a_headless_hung.txt`: other runs
- `pytest_observatory_output.txt`, `junit_observatory.xml`: observatory suite
- `coverage.txt`, `coverage_by_subsystem.csv`: coverage (A.4)
- `main_eval_output.txt`: `--eval` (A.5)
- `experiment_runner_probe/`: 15 per-preset JSONs + `ablation_study_*.json` + `probe_stdout.txt` (A.6)
- `validate_memory_output.txt`, `validate_vision_output.txt` (A.7)

(Other files in `artifacts/results/`, such as `routing_resolution.*` and `verification_gate_*`, were produced by other agents and are not described here.)
