# 01 — System Inventory (Repo Analyst)

**Repository:** `/home/user/Agentic-pilot-local` at commit `2361d50`.
**Method:** I read the source code directly. The code is the source of truth. README, wiki and docs claims count as evidence only where the code backs them.
**Citation convention:** `path:line` refers to the file as it is on disk. Paths without a prefix are relative to the repo root.
**Runtime checks:** Two items were checked by running code in the repo's `.venv-eval` (langgraph 1.2.12). Each is marked **[run-verified]**. Everything else comes from reading the code.

---

## 0. Headline findings (details and citations in the sections below)

1. **The `--eval` flag does nothing.** `python main.py --eval` runs eight `scratch/*.py` scripts (`main.py:608-617`). It skips any that are missing (`main.py:622`), and `scratch/` is gitignored (`.gitignore:47`) and absent from the repo. So the command runs nothing and returns 0 (`main.py:628`).
2. **The ablation runner cannot run.** `ExperimentRunner.run_experiment` imports `create_agent_graph` from `backend.agent.graph` (`backend/experiment/runner.py:82-83`). That function does not exist; the module defines only `build_graph` (`backend/agent/graph.py:9`). Every benchmark task therefore raises, the error is caught, and the task is recorded as `failed` (`runner.py:120-123`). Nothing in the repo calls `ExperimentRunner` anyway.
3. **RAG and episodic-memory retrieval never run on the live path.** `TaskRunner._run` seeds `retrieved_knowledge=[]` and `retrieved_memories=[]` (`backend/agent/runner.py:265-266`). `ContextRouter.route_and_retrieve` skips retrieval whenever both are `is not None` (`backend/rag/router.py:71-77`), and `plan_action_node` only re-fetches when both are `None` (`backend/agent/nodes.py:638`). Tests pass because they omit the keys (for example `tests/test_rag_integration.py:42-51`).
4. **Recovery "strategies" are labels only.** `RecoveryEngine` returns `recovery_strategy` (`backend/recovery/engine.py:198`), but the key is not declared in `AgentState` (`backend/agent/state.py:10-47`). LangGraph drops undeclared keys **[run-verified]**. The recovery router looks only at `status` and always loops back to `extract_dom` (`backend/agent/graph.py:75-80`). No code path implements `alternative_selector`, `vision_fallback` or `replan` as different behaviour.
5. **The `no_verification` ablation flag does nothing.** `enable_verification` is read only by the health endpoint (`backend/api/health.py:48`); `verify_node` never checks it.
6. **The routing "cooldown" is not implemented.** `model_switch_cooldown_steps=1` is defined (`backend/config.py:49`) but never read. The only anti-thrashing mechanism is "stickiness" (`backend/llm/router.py:121-135`).
7. **The privacy claims are overstated.** `PrivacyAuditor.record_external_request` is never called anywhere; the only audit calls are LLM calls from the gateway (`backend/llm/gateway.py:113-120`). The `CredentialStore` keyring wrapper (`backend/security/credentials.py:11`) is never used.
8. **The extraction logic is hard-coded to one case study.** It keyword-filters for "Kattankulathur"/"SRM" campus facts, and when fewer than 3 matching lines are found it returns three hard-coded campus facts (`backend/agent/nodes.py:1108-1139`). The click fallback also matches the literal `"srm"` (`nodes.py:1052`).
9. **Some telemetry metrics are synthetic or never populated.**
   - `routing_overhead_ms` is computed from constants: 1.5 ms per routing plus 250 ms per switch (`backend/telemetry/tracer.py:244`).
   - The recovery and verification trace events that the aggregator needs (`tracer.py:212,215`) are only written by tests.
   - `benchmarks/run.py:63-66` prints hard-coded "Simulated" and "Estimated" numbers.

---

## 1. Module map

Status tags:
- **IMPLEMENTED+TESTED**: a test in `tests/` or `observatory/tests/` exercises the module (test file named).
- **IMPLEMENTED-UNTESTED**
- **PROPOSED**: designed, but the code is partial or a stub, or it is never wired in.
- **FUTURE WORK**: config or docs only.

The "Live?" column says whether the code runs on the production path (`TaskRunner` → LangGraph).

| Module | Function / class | Inputs → Outputs | Status | Live? |
|---|---|---|---|---|
| `backend/agent/graph.py` | `build_graph()` (`:9-84`) | – → compiled `StateGraph(AgentState)`, or `None` if langgraph cannot be imported (`:12-15`) | IMPLEMENTED-UNTESTED as a whole graph. `tests/test_navigation_transition_and_typing.py:21` imports it but never calls it. | Yes |
| `backend/agent/nodes.py` | `parse_intent_node` (`:58-252`) | `input_text` → `ParsedIntent`, `TaskPlan`, routing fields | IMPLEMENTED+TESTED (`test_checkpoint_and_optimization.py`, `test_multi_model_integration.py`) | Yes |
| | `risk_check_node` (`:257-281`) | `parsed_intent` → `status` in {`running`, `waiting_approval`} and `approval_id` | IMPLEMENTED+TESTED indirectly via `tests/e2e/test_runner.py:38-58` (live Ollama). `tests/test_task_runner.py` has a collection error. | Yes |
| | `auth_check_node` (`:284-288`) | state → `{status}` unchanged (pass-through stub) | PROPOSED | Yes (no-op) |
| | `navigate_node` (`:291-397`) | `parsed_intent.site` → `current_url`, `navigation_succeeded` | IMPLEMENTED+TESTED (`test_navigation_transition_and_typing.py`) | Yes |
| | `extract_dom_node` (`:427-521`) | page → `ActionManifest`, or `status=blocked` on CAPTCHA | IMPLEMENTED+TESTED (`test_captcha_handling.py`) | Yes |
| | `retrieve_context_node` (`:575-593`) | state → `retrieved_knowledge`, `retrieved_memories` | IMPLEMENTED+TESTED (`test_rag_integration.py`) | Runs, but retrieval is bypassed (§9) |
| | `plan_action_node` (`:596-934`) | intent, manifest, context → `PlannedAction` | IMPLEMENTED+TESTED (`test_browser_agent_pipeline.py`, `test_multi_model_integration.py`, `test_rag_integration.py`) | Yes |
| | `execute_action_node` (`:938-1304`) | `PlannedAction` → `ActionResult`, evidence files | IMPLEMENTED+TESTED (`test_browser_agent_pipeline.py`, `test_rag_integration.py`) | Yes |
| | `verify_node` (`:1307-1511`) | state → `status` in {`running`, `failed`, `blocked`, `completed`, `waiting_approval`} | IMPLEMENTED+TESTED (`test_browser_agent_pipeline.py`, `test_navigation_transition_and_typing.py`, `test_captcha_handling.py`) | Yes |
| | `error_recovery_node` (`:1514-1582`) | `error`, `retry_count` → status, retry | IMPLEMENTED+TESTED (`test_multi_model_integration.py` imports it; `test_recovery_engine.py`) | Yes |
| | `complete_node` (`:1586-1682`) | final state → persisted task, memory write, browser retain/release | IMPLEMENTED-UNTESTED in isolation (reached only by e2e) | Yes |
| `backend/agent/state.py` | `AgentState` TypedDict (`:10-47`) | – | IMPLEMENTED+TESTED (imported by several tests) | Yes |
| `backend/agent/runner.py` | `TaskRunner` (`:22-372`) | `input_text` → task_id, and runs `graph.astream` | IMPLEMENTED+TESTED (`test_captcha_handling.py` for resume/fallback, `tests/e2e/*`). `tests/test_task_runner.py` fails to collect: `NameError 'Database'` at line 103, see `artifacts/results/pytest_run1_default.txt`. | Yes |
| `backend/agent/checkpoint.py` | `CheckpointManager` (`:49-181`) | state → JSON under `<data_dir>/checkpoints/<task>.json` (`:56-57,64-66`) | IMPLEMENTED+TESTED (`test_checkpoint_and_optimization.py`, `test_recovery_engine.py`) | Yes |
| `backend/agent/prompts.py` | `INTENT_SYSTEM_PROMPT` (`:3-21`), `ACTION_PLANNING_SYSTEM_PROMPT` (`:23-49`), `TASK_DECOMPOSITION_PROMPT` (`:51-80`) | – | IMPLEMENTED (used by nodes) | Yes |
| `backend/agent/code_executor.py` | `CodeExecutor` (read/write/replace/AST syntax check) | path, text → `ActionResult` | IMPLEMENTED+TESTED (`test_multi_model_integration.py:69`) | **No**: not referenced by any backend module |
| `backend/llm/router.py` | `ModelRouter.route` (`:42-199`) | task_type, text, flags → `RoutingDecision` | IMPLEMENTED+TESTED (`test_model_router.py`, `test_checkpoint_and_optimization.py`) | Yes |
| `backend/llm/registry.py` | `ModelRegistry`, `DEFAULT_KNOWN_MODELS` (`:71-172`) | – → model metadata | IMPLEMENTED+TESTED (`test_model_registry.py`) | Yes |
| `backend/llm/analyzer.py` | `CapabilityAnalyzer.analyze` (`:60-189`) | text, action, flags → role and capabilities | IMPLEMENTED+TESTED (`test_checkpoint_and_optimization.py`) | Yes |
| `backend/llm/gateway.py` | `OllamaGateway.complete` / `complete_structured` (`:75-195`) | prompts (+ image) → text or a Pydantic model | IMPLEMENTED+TESTED via mocks; the live path is only in e2e | Yes |
| `backend/llm/parser.py` | schemas and `parse_model_response` (`:198-215`) | raw text → model | IMPLEMENTED+TESTED (`test_parser.py`) | Yes |
| `backend/browser/dom.py` | `detect_captcha` (`:12-74`), `DOMExtractor` (`:77-208`) | Page → `(bool, reason)` / `ActionManifest` | IMPLEMENTED+TESTED (`test_captcha_handling.py`) with a mocked page | Yes |
| `backend/browser/executor.py` | `PlaywrightExecutor` (`:14-321`) | Page, element → `ActionResult` | IMPLEMENTED; unit tests mock it (e.g. `test_navigation_transition_and_typing.py:185-186`) | Yes |
| `backend/browser/actions.py` | `ActionExecutor` (older duplicate of the executor) | – | IMPLEMENTED-UNTESTED | **No**: not imported anywhere |
| `backend/browser/pool.py` | `BrowserPool` (context pool, retain/release, idle watchdog) | – | IMPLEMENTED+TESTED (`test_recovery_engine.py:94`) | Yes |
| `backend/desktop/executor.py` | `DesktopExecutor` (pyautogui click/type/hotkey/screenshot) | coordinates/text → `ActionResult` | IMPLEMENTED+TESTED (interface only: `test_case_study_enhancements.py:209`) | **No**: not wired into the graph |
| `backend/verification/manager.py` | `VerificationManager`, `extract_exact_text_to_type` | page/state → `VerificationResult` | IMPLEMENTED+TESTED (`test_case_study_enhancements.py`, `test_navigation_transition_and_typing.py`, `test_browser_agent_pipeline.py`) | Yes |
| | `verify_visual` (`:128-130`) | → always `verified: True` | PROPOSED (stub) | No |
| | `verify_dom_mutation` (`:87-101`) | → always `verified: True` | PROPOSED (no-op check) | Yes |
| `backend/recovery/engine.py` | `RecoveryEngine` (`:53-210`) | state → status and retry_count | IMPLEMENTED+TESTED (`test_recovery_engine.py`, `test_case_study_enhancements.py:136`) | Yes (classification and bounds only) |
| | strategy execution (alt selector / vision / replan) | – | PROPOSED: labels only (§6) | No |
| `backend/evidence/manager.py` | `EvidenceManager`, `ExecutionRecord` (`:15-147`) | bytes/records → files under `<log_dir>/evidence/<task>` | IMPLEMENTED+TESTED (`test_case_study_enhancements.py:64`, `test_multi_model_integration.py:18`, `test_rag_integration.py`) | Yes |
| `backend/replay/system.py` | `ReplaySystem.load_replay` | task_id → dict | IMPLEMENTED-UNTESTED. It reads `~/.pilot/evidence` (`:11`), but evidence is written to `~/.pilot/logs/evidence`, so it misses | Via `GET /api/tasks/{id}/replay` (`backend/api/tasks.py:140-148`) |
| `backend/memory/provider.py` | `ChromaProvider` (`:55-171`) | text → SQLite `memories` + Chroma `pilot_memories` | IMPLEMENTED+TESTED only indirectly (mocked in router tests); `scripts/validate_memory.py` exists | Writes yes; reads bypassed (§9) |
| `backend/memory/manager.py` | re-export (`:7-15`) | – | IMPLEMENTED | – |
| `backend/rag/*` | `ContextRouter`, `KnowledgeRetriever`, `KnowledgeStore`, `ContextBuilder`, ingestion (`chunker`, `loader`, `pipeline`) | query → chunks; files → chunks | IMPLEMENTED+TESTED (`test_rag_*.py`, `test_multi_model_rag.py`) | Retrieval bypassed on the live path; **no ingestion entry point** (no API route or CLI calls `IngestionPipeline`) |
| | `_apply_reranking` (`retriever.py:192-215`) | chunks → rescored chunks | IMPLEMENTED-UNTESTED (no test mentions reranking) | No |
| `backend/security/sanitizer.py` | `InputSanitizer` (`:44-103`) | text → text with `[SANITIZED_CONTENT]` | IMPLEMENTED+TESTED (`test_case_study_enhancements.py:164`, `test_rag_security.py`) | Yes (DOM element text; RAG chunks) |
| `backend/security/audit.py` | `PrivacyAuditor` (`:22-122`) | LLM call metadata → JSONL | IMPLEMENTED+TESTED (`test_case_study_enhancements.py:184`) | LLM calls only |
| | `record_external_request` (`:82-106`) | – | PROPOSED: never called | No |
| `backend/security/approval.py` | `requires_approval`, `build_approval_prompt` | intent → bool/str | IMPLEMENTED+TESTED (e2e `test_high_risk_approval_flow`; `test_plugins.py:13` is a plugin-level risk test) | Yes |
| `backend/security/credentials.py` | `CredentialStore` (keyring) | – | IMPLEMENTED-UNTESTED | **No** |
| `backend/security/sessions.py` | `SessionRegistry` | – | PROPOSED (in-memory; unused, and `auth_check_node` never calls it) | No |
| `backend/vision/fallback.py`, `provider.py` | `VisionFallback.plan_action`, `check_vision_availability` | screenshot → `VisionAction` | IMPLEMENTED+TESTED (`test_checkpoint_and_optimization.py:211`, which **fails** in `artifacts/results/pytest_run2_full.txt`; `test_browser_agent_pipeline.py:231`, also **fails**) | Yes (on `need_help`) |
| `backend/telemetry/tracer.py` | `TelemetryTracer` → `<log_dir>/traces.jsonl` (`:23-25`) | events → JSONL; aggregation | IMPLEMENTED+TESTED (`test_case_study_enhancements.py:219`, `test_multi_model_integration.py:48`) | Partially (§9, §14) |
| `backend/telemetry/broadcaster.py` | `ObservabilityBroadcaster` (`:58-139`) | events → WS/SSE subscribers | IMPLEMENTED+TESTED (`observatory/tests/test_observatory.py`) | Yes (fed by `Database.add_event`, `backend/db/database.py:215-227,247-264`) |
| `backend/telemetry/tracker.py` | `TelemetryTracker` → `~/.pilot/evidence/<task>/telemetry.json` (`:49-53`) | – | IMPLEMENTED-UNTESTED | **No**: never called |
| `backend/telemetry/profiler.py` | `LatencyProfiler`, `run_baseline_profile_audit` (`:164`) | – | IMPLEMENTED-UNTESTED | No: standalone audit only |
| `backend/experiment/config.py` | `ABLATION_PRESETS` (15), `STANDARD_BENCHMARK_TASKS` (8) | – | IMPLEMENTED+TESTED as data (`test_case_study_enhancements.py:242`) | – |
| `backend/experiment/runner.py` | `ExperimentRunner` | preset → JSON | PROPOSED/**broken** (ImportError, §12) | No |
| `backend/plugins/*` | `PluginRegistry.find_for_intent` (`runtime.py:32-39`); `GmailPlugin.execute` etc. | intent → plugin id / dry-run result | Registry: IMPLEMENTED+TESTED (`test_plugins.py`). `execute()`: PROPOSED (dry-run, e.g. `builtin/gmail.py:47-52`; never called by the graph) | Only `plugin_id` is recorded |
| `backend/api/*` | FastAPI routes (tasks, approvals, sessions, plugins, settings, health, observability) | HTTP ↔ runner/DB | IMPLEMENTED-UNTESTED (no API tests) | Yes |
| `backend/db/database.py` | `Database` (aiosqlite) | – | IMPLEMENTED+TESTED (`test_database.py`, `observatory/tests/test_observatory.py`) | Yes |
| `backend/config.py` | `PilotConfig` (env prefix `PILOT_`, `:12`) | env → settings | IMPLEMENTED+TESTED (`test_case_study_enhancements.py:32`) | Yes |
| `observatory/backend/*` | `EventStreamManager`, `ReadOnlyStorage`, API | Pilot WS/SSE + SQLite → dashboard | IMPLEMENTED+TESTED (`observatory/tests/test_observatory.py`, 20 tests; **not** in default `pytest.ini` testpaths, `pytest.ini:3`) | Separate process |
| `main.py` | `PilotOrchestrator` launcher | CLI → subprocesses | IMPLEMENTED+TESTED (`tests/test_launcher.py`; `test_different_working_directory` fails in `pytest_run2_full.txt`) | – |
| Routing cooldown | `model_switch_cooldown_steps` (`backend/config.py:49`) | – | FUTURE WORK (config only) | No |

---

## 2. LangGraph node graph (from `backend/agent/graph.py`)

### Nodes (`graph.py:18-28`)
`parse_intent`, `risk_check`, `auth_check`, `navigate`, `extract_dom`, `retrieve_context`, `plan_action`, `execute_action`, `verify`, `error_recovery`, `complete`.

### Edges and routers

| From | Type | Condition → Target | Line |
|---|---|---|---|
| `START` | edge | → `parse_intent` | `:30` |
| `parse_intent` | `parse_router` | `status=="failed"` → `error_recovery`; else → `risk_check` | `:32-37` |
| `risk_check` | `risk_router` | `status=="waiting_approval"` → `complete`; else → `auth_check` (**including `status=="failed"`** from `nodes.py:264`) | `:38-43` |
| `auth_check` | edge | → `navigate` | `:44` |
| `navigate` | `navigate_router` | `status=="blocked"` → `complete`; `navigation_succeeded` → `extract_dom`; else → `error_recovery` | `:46-53` |
| `extract_dom` | `extract_dom_router` | `status=="blocked"` → `complete`; else → `retrieve_context` | `:55-60` |
| `retrieve_context` | edge | → `plan_action` | `:61` |
| `plan_action` | edge (**unconditional**, even when the node returns `status` of `failed`/`blocked`) | → `execute_action` | `:62` |
| `execute_action` | edge | → `verify` | `:63` |
| `verify` | `verify_router` | `status=="running"` → `extract_dom`; `status=="failed"` → `error_recovery`; anything else (`completed`, `blocked`, `waiting_approval`) → `complete` | `:65-73` |
| `error_recovery` | `recovery_router` | `status` in {`failed`, `blocked`} → `complete`; else (`running`) → `extract_dom` | `:75-82` |
| `complete` | edge | → `END` | `:83` |

The routers are registered without a `path_map`. When run, `draw_mermaid()` on the compiled graph shows only `START→parse_intent→END` **[run-verified]**, so paper figures must be drawn by hand from the table above. The runner does not pass a `recursion_limit` (`runner.py:274`). The installed langgraph 1.2.12 defaults it to 10007 (`.venv-eval/.../langgraph/_internal/_config.py:32`). `requirements.txt` allows `langgraph>=0.2.0` (`backend/requirements.txt:4`).

The real iteration bound is in code:
- `verify_node` fails the task when `llm_call_count >= 15` (`nodes.py:1469,1509`).
- `llm_call_count` increases by 1 or 2 in parse (`:247`) and by 1 per plan (`:927`).
- `RecoveryEngine` caps retries at 6 (`engine.py:61`).
- The runner watchdog cancels tasks older than `max_task_duration_minutes=5` (`runner.py:364-372`, `config.py:28`).

### What each node does (`backend/agent/nodes.py`)

- **parse_intent** (`:58-252`):
  - If the checkpoint already holds `parsed_intent` and `task_plan`, it returns them without calling an LLM (`:67-75`).
  - Otherwise it routes with `task_type="intent_parsing", complexity="low"` (`:78-83`) and calls `complete_structured(INTENT_SYSTEM_PROMPT → ParsedIntent)` (`:94-99`).
  - It matches a plugin (`:113`).
  - The task counts as multi-step if the text contains " and ", " then ", " after ", " followed by ", "," or ";", or has more than 8 words (`:119`). It then re-routes with `task_type="planning", complexity="high"` and asks for a `TaskPlan` (`:121-149`).
  - If `extract_exact_text_to_type` finds literal text to type, the plan is replaced by a one-step `type_text` plan (`:151-171`). Otherwise a one-step default plan is built if none exists (`:172-187`).
  - It probes vision availability (`:189-192`) and emits the MODEL_SELECTED, PLAN_CREATED, STEP_PROGRESS and VISION_STATUS events (`:197-233`).
- **risk_check** (`:257-281`): calls `requires_approval(intent)` unless `approved` is set. If approval is needed it writes an `approvals` row and returns `waiting_approval`.
- **auth_check** (`:284-288`): logs and returns the current status. There is no auth logic.
- **navigate** (`:291-397`):
  - It skips re-navigation when the page is already on the target, or when `current_step_index>1` (`:306-310`).
  - Otherwise it calls `PlaywrightExecutor.navigate` (`:315`), which makes up to 3 attempts with a 15 s timeout, retrying only on transient errors (`executor.py:164-189`).
  - It waits for `domcontentloaded` with a 10 s timeout (`:335`), saves `after_navigation.png` (`:358-371`), and marks plan step 1 completed if it is a navigate/open step (`:373-389`).
- **extract_dom** (`:427-521`): runs `DOMExtractor.extract` (`:432`). If `detect_captcha` fires, `page_state=="captcha"`, or the URL contains `/sorry/`, it saves `captcha_detected.png`, emits CAPTCHA_DETECTED and BLOCKED, retains the browser, and returns `status=blocked` with `recovery_options=["manual_captcha","safe_search_fallback"]` (`:436-480`). Otherwise it saves `dom_observation.png` (`:482-499`).
- **retrieve_context** (`:575-593`): calls `context_router.route_and_retrieve(state)`. On error it degrades to empty lists.
- **plan_action** (`:596-934`), in order:
  1. If already blocked, return `need_help` (`:599-605`).
  2. Route with `task_type=intent.action` and complexity `high` if the plan has more than one step, else `medium` (`:619-625`).
  3. Reuse the retrieved context, or fetch it if both lists are `None` (`:636-641`).
  4. Build the budgeted context (`:644-651`).
  5. Sanitize the DOM element text (`:654-655`).
  6. Build the prompt: goal, step index, plan, knowledge, memory, title, URL, page state, elements as JSON (`:669-682`).
  7. Call the LLM for a `PlannedAction`; on exception the action becomes `need_help` (`:686-694`).
  8. **Deterministic overrides:**
     - exact-text entry uses a DOM-scored main input with a threshold score ≥ 40 (`:697-731`, scorer `:524-572`);
     - if the action is `need_help`, fall back to vision (`:733-817`);
     - CAPTCHA blocks the task (`:822-829`);
     - navigation-loop protection (`:833-843`);
     - on Google, force `type_text` into the search box with Enter (`:846-867`);
     - convert a direct `google.com/search` navigation into typing "to avoid bot detection" (`:869-880`);
     - keyword-based step overrides: "open/click/result" → click, "extract/gather/read/collect" → extract, "return/finish/complete/report" → complete (`:883-902`).
- **execute_action** (`:938-1304`):
  - `complete` saves `final_completion.png` and the DOM snapshot and returns the result (`:948-966`). `need_help` returns an error (`:968-973`).
  - Otherwise it saves `before_step_{llm_call_count}.png` and the DOM snapshot (`:986-991`), then dispatches by action type (`:1018-1164`).
  - `VISION_COORD` actions click or type at viewport percentages parsed from `reasoning` (`:1020-1034`).
  - It saves `after_step_N.png` (`:1170-1174`) and reads back the entered value for `type_text` (`:1177-1193`).
  - It writes an `ExecutionRecord` if `enable_evidence` is set (`:1244-1291`) and appends to `action_history` (`:1293-1295`).
- **verify** (`:1307-1511`): see §5.
- **error_recovery** (`:1514-1582`): routes to the recovery role (`:1529-1535`), delegates to `recovery_engine.handle_failure` (`:1548`), saves the recovery record to `verification.json`, and emits RECOVERY_ATTEMPT and RETRY_ATTEMPTED (`:1563-1580`).
- **complete** (`:1586-1682`):
  - `running` is mapped to `completed` (`:1590-1591`).
  - **Navigation-proof gate:** a `completed` task whose intent names a site is downgraded to `failed` if `navigation_succeeded` is false (`:1593-1602`).
  - It persists the task (`:1619-1626`).
  - It stores a strategy memory (on success) or a failure memory (on failure) if `enable_memory` is set (`:1629-1654`).
  - It retains the browser for completed tasks (when `keep_browser_open`) and for blocked tasks; otherwise it releases it (`:1656-1680`).

### Non-LangGraph fallback runner
**None exists.** The `graph.py` docstring promises "a simple fallback runner" (`graph.py:1`), but `build_graph()` returns `None` without langgraph (`:14-15`) and `TaskRunner._run` then raises `RuntimeError("LangGraph could not be built")` (`runner.py:217-219`). The comment at `runner.py:362` says the old `_execute_intent` path was removed. Execution is `graph.astream(state)` (`runner.py:274`) with a pause gate and a checkpoint after every node (`:275-306`).

---

## 3. AgentState schema (`backend/agent/state.py:10-47`)

| Field | Type | Line |
|---|---|---|
| task_id | `str` | 13 |
| input_text | `str` | 14 |
| parsed_intent | `ParsedIntent \| None` | 15 |
| current_url | `str \| None` | 16 |
| action_manifest | `ActionManifest \| None` | 17 |
| action_history | `list[ActionResult]` | 18 |
| retry_count | `int` | 19 |
| status | `str` | 20 |
| approval_id | `str \| None` | 21 |
| error | `str \| None` | 22 |
| result | `dict \| None` | 23 |
| plugin_id | `str \| None` | 24 |
| llm_call_count | `int` | 25 |
| planned_action | `PlannedAction \| None` | 26 |
| approved | `bool` | 27 |
| navigation_succeeded | `bool` | 28 |
| session_id | `str \| None` | 29 |
| task_plan | `TaskPlan \| None` | 30 |
| current_step_index | `int` | 31 |
| retrieved_knowledge | `list[dict] \| None` | 32 |
| retrieved_memories | `list[dict] \| None` | 33 |
| retrieval_metadata | `dict \| None` | 34 |
| selected_model | `str \| None` | 35 |
| model_role | `str \| None` | 36 |
| routing_reason | `str \| None` | 37 |
| model_switch | `bool` | 38 |
| extracted_data | `dict \| None` | 39 |
| final_answer | `str \| None` | 40 |
| last_action_status | `str \| None` | 41 |
| vision_called | `bool` | 42 |
| vision_model | `str \| None` | 43 |
| vision_status | `str \| None` | 44 |
| step_progress | `str \| None` | 45 |
| blocked_reason | `str \| None` | 46 |
| recovery_options | `list[str] \| None` | 47 |

There are 34 fields and no reducers: every update overwrites the previous value.

`status` values used in code: `running`, `failed`, `blocked`, `waiting_approval`, `completed` (nodes) and `queued`/`cancelled` (runner/DB).

Keys returned by nodes but **not** in the schema, and therefore silently dropped **[run-verified]**: `recovery_strategy` (`engine.py:174,198`).

Supporting Pydantic schemas (`backend/llm/parser.py`):
- `ParsedIntent` (`:12-21`): action, target, content, site="unknown", risk_level, confidence, reasoning.
- `TaskStep` (`:24-33`) and `TaskPlan` (`:36-42`).
- `InteractiveElement` (`:46-61`).
- `ActionManifest` (`:64-70`).
- `PlannedAction` (`:73-88`): action_type, element_id, text, value, url, key, direction, press_enter, extracted_data, reasoning, confidence, selector_quality, grounding_quality.
- `ActionResult` (`:91-101`).

---

## 4. Model router

**Roles.** `ModelRole` has the values planner, executor, vision, coder, recovery, lightweight, general (`registry.py:34-43`). The router maps coder→"coding", planner→"reasoning" and executor→"general" (`router.py:97-103`).

**Default model tags.** Config fields are all in `backend/config.py`; the rest are in `backend/llm/registry.py`.

| Setting | Value | Line |
|---|---|---|
| `ollama_model` (base / single mode) | `qwen2.5:1.5b` | `config.py:15` |
| `ollama_vision_model` | `moondream` | `config.py:16` |
| `model_reasoning` | `qwen2.5:7b` | `config.py:44` |
| `model_vision` | `moondream` | `config.py:45` |
| `model_coding` | `qwen2.5-coder:3b` | `config.py:46` |
| `model_lightweight` | `deepseek-r1:1.5b` | `config.py:47` |
| `model_fallback` | `qwen2.5:1.5b` | `config.py:48` |
| `model_routing_strategy` | `"dynamic"` (also `"static"`, `"single"`) | `config.py:43` |
| `model_candidates_by_role` | planner [qwen3.5:2b, qwen2.5:7b, deepseek-r1:1.5b]; executor [qwen2.5:1.5b, qwen2.5:7b]; vision [qwen3-vl:2b, moondream]; coder [qwen2.5-coder:3b, qwen2.5-coder:1.5b]; lightweight [deepseek-r1:1.5b, qwen3.5:2b, qwen2.5:1.5b]; recovery [qwen2.5:7b, qwen3.5:2b]; general [qwen2.5:1.5b, qwen2.5:7b]; fallback [qwen2.5:1.5b] | `config.py:50-61` |
| Registry profiles (priority) | qwen2.5:7b (10), qwen3.5:2b (9), qwen2.5:1.5b (5), deepseek-r1:1.5b (9), moondream (8), qwen3-vl:2b (10), qwen2.5-coder:3b (10), qwen2.5-coder:1.5b (8) | `registry.py:71-172` |
| Installed-model probe TTL | 300 s | `registry.py:178,251` |
| Launcher defaults | text `qwen2.5:1.5b`, vision `moondream`, alt vision `qwen3-vl:2b`; it pulls only the text model and one vision model | `main.py:88-90,332,348` |

**Selection rule** (`ModelRouter.route`, `router.py:42-199`):
0. If `enable_multi_model` is false or the strategy is `"single"`, return `ollama_model` (or `ollama_vision_model` if the input has an image) (`:58-67`).
1. If the probe found exactly one installed model, bypass routing and use it (`:70-81`).
2. `CapabilityAnalyzer.analyze` (`analyzer.py:60-189`) is a deterministic keyword classifier, checked in this priority order:
   - forced capabilities (`:77-101`);
   - recovery → [recovery, reasoning] (`:104-112`);
   - vision (image, or keywords such as "screenshot", "screen", "visual", "gui", "image", "coord", "pixel") (`:28-31,115-123`);
   - coding keywords (`:22-26,126-138`);
   - lightweight: `task_type` in {intent_parsing, fast_filter}, or complexity "low" and not complex, or a navigate/open/go/browse action that is not complex → [lightweight, fast] (`:153-165`);
   - complex → planner [planning, reasoning] (+long_context if more than 3000 tokens). "Complex" means `task_type` planning, complexity high, a connective or comma, more than 10 words, or a reasoning keyword (`:141-150,167-179`);
   - default → general.
3. Candidates are taken from `model_candidates_by_role` in **configuration order** (not priority), filtered to installed models only after a probe has run (`registry.py:291-326`). If none match, the router falls back to capability search sorted by priority (`router.py:112-117`, `registry.py:328-343`). Before any probe, uninstalled models can be selected (`router.py:70,108`).
4. **Stickiness (the only anti-thrashing mechanism):** if the active model has all the required capabilities and the call is not a recovery call, keep it and set `model_switch=False` (`router.py:121-135`).
5. With the static strategy, a configured per-role model is used (`:143-155`). Otherwise the router takes `candidates[0]` (`:157-161`).
6. **Fallback chain** when there are no candidates, with `fallback_used=True`: `model_fallback` (if registered and installed) → `ollama_model` → the first enabled registry model → `ollama_model` (`:163-182`).

`model_switch` means the previous selection differed from this one (`:184`).

**Cooldown.** `model_switch_cooldown_steps=1` (`config.py:49`) is **never read**; the only references outside config are in docs. `_step_counter` is incremented (`router.py:55`) but never used.

**Gateway retry.**
- Ollama calls are attempted `max_retry_count+1 = 4` times (`config.py:25`, `gateway.py:80`).
- Backoff is `0.25·2^attempt` seconds, and only for connection/timeout-like errors (`gateway.py:126-144`).
- Structured parsing makes up to 4 attempts, with a corrective re-prompt and a `0.1·(attempt+1)` s sleep (`gateway.py:175-192`).
- JSON mode uses `format="json"` (`:94-95`).

**Vision model selection bypasses the router.** `VisionFallback.check_vision_availability` scans the installed models in the order [`qwen3-vl:2b`, `moondream`, `moondream:latest`, `qwen2.5-vl:7b`], then any model with the VISION capability (`vision/fallback.py:58-80`). `model_router` is imported there but not used (`fallback.py:8`).

**Inference about the default install (not run):** the launcher pulls only `qwen2.5:1.5b` and a vision model (`main.py:332,348`). With those installed:
- planner candidates (qwen3.5:2b, qwen2.5:7b, deepseek-r1:1.5b) are all missing;
- `qwen2.5:1.5b` lacks the PLANNING capability (`registry.py:100-112`);
- so planning falls back to `qwen2.5:1.5b` through `model_fallback` (`router.py:166-169`).

Multi-model routing therefore only shows up if extra models are pulled manually.

---

## 5. Verification logic

### Action success versus task success
- **Action success** is `ActionResult.success` from the executor.
  - `type_text` fills the field, then `verify_input_value` requires the read-back value to equal the input exactly, or `inner_text` to contain it (`executor.py:33-34`, `verification/manager.py:103-126`). But on any **non-VerificationError** exception the executor falls back to a mouse click plus `keyboard.type` and returns `success=True` **without verification** (`executor.py:56-77`).
  - `click` calls `verify_dom_mutation`, which **always returns verified** (`manager.py:87-101`, called at `executor.py:282`).
  - `navigate` calls `verify_url`, which raises on a `chrome-error://` URL or page content containing `ERR_NAME_NOT_RESOLVED` / `ERR_CONNECTION_REFUSED` (`manager.py:69-85`).
- **Step advance.** If the last action succeeded and plan steps remain, `verify_node` marks the current step `completed` and advances the index. It does **not** check the step's `expected_outcome` (`nodes.py:1393-1426`).
- **Task success** is decided only when `should_verify_completion` holds (`nodes.py:1431-1435`): the action is `complete`; or `cur_step_idx >= len(steps)`; or an exact-text `type_text` succeeded. It then calls `VerificationManager.verify_task_completion` (`nodes.py:1439-1449`).

### `verify_node` decision order (`nodes.py:1307-1511`)
1. If already `blocked`, stay blocked (`:1323-1329`).
2. Run `detect_captcha(page)`, check `manifest.page_state=="captcha"`, or check for `/sorry/` in the URL. If any hits: emit BLOCKED, retain the browser, return `blocked` (`:1332-1357`).
3. If `state.error` is set:
   - `VISION_UNAVAILABLE` → `failed` (`:1361-1363`);
   - "Verification failed" → `failed` (`:1365-1367`);
   - else if `retry_count < 3` → `retry_count+1`, `running` (loops to `extract_dom` **without** calling the RecoveryEngine) (`:1369-1370`);
   - else → `failed "Max retries exceeded"` (`:1371-1373`).
4. If the action is `need_help` → `failed` (`:1375-1382`).
5. Step progression (above).
6. Completion verification. If it is rejected: return `running` (the "premature completion prevented" path), or `failed` once `llm_call_count >= 15` (`:1462-1471`). If it passes: save `completion_proof.png`, emit VERIFICATION_PASSED, and return `completed`. If `requires_approval(intent)` holds and the task is not approved, return `waiting_approval` instead (`:1478-1506`).
7. Otherwise return `running`, or `failed` if `llm_call_count >= 15` (`:1509-1511`).

### `VerificationManager.verify_task_completion` predicates (`manager.py:173-292`)
- **Error state** (`:193-222`):
  - `url.startswith("chrome-error://")` or `"err_"` in the URL;
  - title contains "404 not found", "500 internal", "502 bad gateway" or "503 service";
  - bot block (`sorry/index`, `recaptcha` in the URL, or "unusual traffic" in the title), **only if the task is multi-step** (`:210`);
  - any of these → FAIL.
- **Search-homepage guard** (`:225-238`): the task is multi-step (the input contains search/find/look up/query or an extract keyword, or the plan has more than one step), and the URL ends with google.com, google.co.in, bing.com or duckduckgo.com with no "search" or "q=" → FAIL (`premature_completion_prevented`).
- **Exact text** (`:241-264`): if `extract_exact_text_to_type(input)` returns text, some `input`, `textarea` or `[contenteditable]` value on the page must contain it.
- **Extraction** (`:267-280`): if the input asks to extract, gather, collect, "return the findings", "information about" or "page title", then `extracted_data` must be non-empty, **or** `final_answer` must be longer than 40 characters and not start with navigat/open/go to/start/search/click/select/type.
- **Plan completion** (`:283-289`): non-verify steps that are not `completed` count as a FAIL only if there is **no** `extracted_data` or `final_answer`.
- **Pass/fail rule:** `verify_expected_vs_observed` does key-by-key case-insensitive equality or substring matching. It sets `verified = (mismatches == 0)` and `confidence = 1 − mismatches/len(expected)` (`manager.py:134-171`). There is **no confidence threshold**; the confidence value is recorded but plays no part in the decision.

### Other gates
- `complete_node` downgrades `completed` to `failed` without navigation proof (`nodes.py:1593-1602`).
- `enable_verification` is **not consulted** anywhere in the agent (only `api/health.py:48`).

### CAPTCHA and error-page detection
- `detect_captcha` (`browser/dom.py:12-74`) checks:
  - URL contains `/sorry/`, `sorry/index`, `recaptcha` or `captcha`;
  - title contains "sorry...", "captcha" or "robot";
  - body text contains one of 12 phrases, e.g. "unusual traffic", "verify you are human", "security check", "attention required! | cloudflare" (`:32-45`);
  - one of 9 selectors matches, e.g. `iframe[src*='recaptcha']` or `iframe[src*='challenges.cloudflare.com']` (`:54-64`).
- `_detect_page_state` (`dom.py:100-115`) returns `login_required` if the URL has "login" or the body contains "sign in", "log in" or "password". It returns `error` if the body contains "404", "500", "not found" or "server error", and `loading` on busy/spinner selectors. These are coarse heuristics that are likely to produce false positives (my observation).

---

## 6. Recovery strategies (`backend/recovery/engine.py`)

**Failure taxonomy.** `FAILURE_TYPES` (`:33-41`) is matched by case-insensitive substring in dict order; the first match wins (`:66-73`):

| Failure type | Patterns |
|---|---|
| `captcha` | captcha, recaptcha, sorry/index, unusual traffic, automated queries, bot verification, i'm not a robot |
| `transient` | timeout, Timeout, net::ERR_, CONNECTION |
| `element_not_found` | Element has no usable, Unsupported action, missing element, not found, element not found |
| `verification_failed` | Verification failed, Input verification failed |
| `navigation_failed` | Navigation failed, DNS, chrome-error |
| `vision_needed` | need_help, Cannot find element |
| `llm_failure` | LLM failure, Structured LLM response, not valid JSON |

Anything else is `unknown`.

Because matching is ordered, an error such as `"Navigation failed: … net::ERR_NAME_NOT_RESOLVED"` (produced at `executor.py:185`) is classified as `transient`, not `navigation_failed`. That is my inference from `:66-73`.

**Escalation order.** `STRATEGY_LEVELS = ["retry","alternative_selector","vision_fallback","replan"]` (`:45-50`).

**Constants.**
- `max_retries_per_strategy=2` and `max_total_retries=6` (`:61`).
- Level index = `min(retry_count // 2, 3)` (`:102`).
- Overrides:
  - captcha → `blocked` (`:95-96`);
  - `retry_count >= 6` → `exhausted` (`:98-99`);
  - `vision_needed` → `vision_fallback` (`:105-106`);
  - `verification_failed` with `retry_count >= 2` → `replan` (`:107-108`);
  - `navigation_failed` → `retry` if `retry_count < 2`, else `replan` (`:109-110`).
- `enable_recovery=False` → immediately `failed` (`:127-129`).

**What happens with the strategy.**
- `handle_failure` returns `{retry_count+1, status:"running", error:None, recovery_strategy}` (`:194-200`).
- `recovery_strategy` is not an `AgentState` key and is dropped (§3).
- `recovery_router` sends every `running` status back to `extract_dom` (`graph.py:75-80`).

So in practice every strategy is the same thing: re-observe the page and re-ask the planner LLM. No code applies alternative selectors, forces vision, or triggers re-decomposition. The in-memory `_recovery_history` (`:64,206-210`) is never read by the agent.

**Interaction with `verify_node`.**
- Failed actions are first retried by `verify_node` itself while `retry_count < 3` (`nodes.py:1369-1370`).
- The engine is therefore first reached at `retry_count=3` → level index 1 (`alternative_selector`), then `vision_fallback` at 4 and 5, then `exhausted` at 6.
- The `retry` level is reached only on failures that arrive before any verify retries: navigation failure (`graph.py:49-51`) or parse failure (`graph.py:32-35`).
- There is a second, separate retry counter in the executor: navigation makes 3 attempts with a 0.2 s sleep, retrying only on Playwright timeouts or `net::ERR_` errors (`executor.py:164-189`).
- Separately, `max_retry_count=3` (`config.py:25`) controls **Ollama call** retries (`gateway.py:80,175`), not action retries. `wiki/Configuration.md:67` claims otherwise.

---

## 7. Grounding

**DOM extraction** (`browser/dom.py`):
- **Query selector:** `button,input,textarea,select,a,[role="button"],[role="link"],[contenteditable="true"]` (`:144`).
- **Per-element fields** (`:153-172`): `tag`, `role`, `aria-label`, `text_content` (the first 120 chars of `innerText` or `value`), `placeholder`, `type`, visibility (non-zero rect, not hidden, not `display:none`), `interactable` (visible, not disabled, not `aria-hidden`), `xpath`, `css_selector`, and a bounding box centre with width/height.
- **Element IDs:** each element gets `element_id = "pilot-el-{index}"`, and the extractor **stamps** `data-pilot-id` onto the live DOM (`:152-153`).
- **Selectors:**
  - `selector = [data-pilot-id="…"]` (`:166`);
  - `css_selector` = `#id`, else `tag.class1.class2`, else `tag` (`:123-129`);
  - `xpath` = `//*[@id=…]` or an index path (`:130-143`).
  - The executor tries `selector`, then `css_selector`, then `xpath` (`executor.py:309-316`).
- **Filtering and compression** (`:174,179-208`):
  - only interactable elements are kept;
  - they are sorted by `_element_rank`: submit/send/post/publish/continue/next = 0, input/textarea = 1, select = 2, a = 3, other = 4 (`:211-227`);
  - duplicates by (role, aria_label, text) are removed;
  - **at most 5 `<a>` links** are kept (`:195-198`);
  - labels containing cookie, advertisement or sponsored are dropped (`:203-204`);
  - **the manifest is capped at 50 elements** (`:206-207`).
- **Sanitization:** `text_content`, `aria_label` and `placeholder` are sanitized before being put into the prompt (`nodes.py:654-655`, `sanitizer.py:86-94`).

**When vision fallback triggers.** Vision is called only when, after the LLM call and the exact-text override, the planned action is `need_help` (`nodes.py:733`). That can come from an LLM choice, an LLM exception (`:693-694`), or a missing intent or manifest (`:610-611`). The fallback:
- takes a full-page screenshot (`executor.py:218-226`);
- calls `vision_provider.plan_action(screenshot, intent.action, exact_text or target or content)` (`nodes.py:758`);
- sends the image as base64 in `images` to Ollama chat in JSON mode (`gateway.py:90-95`).

**Vision model:** the first installed model from the priority list in §4. If none is installed, `VisionUnavailableError` → `status failed`, `error VISION_UNAVAILABLE` (`fallback.py:85-88`, `nodes.py:803-816`).

**What vision returns.** `VisionAction{action_type ∈ click/type_text/navigate/complete/need_help, text, url, x_percent, y_percent, reasoning}` (`fallback.py:22-29`). If it is not `need_help`, the node:
- builds `PlannedAction(element_id="VISION_COORD", reasoning="x,y")` (`nodes.py:777-785`);
- executes it by clicking at `viewport.width·x` and `viewport.height·y` (1280×800 context, `pool.py:128`), plus `keyboard.type` for text (`nodes.py:1020-1032`);
- records the result as `success=True` with no post-check (`:1032`).

**Vision cache:** a SHA-256 hash of screenshot + goal + target, holding 30 entries with FIFO eviction (`fallback.py:47-56,90-96,111-115`). Note that `vision_provider` is a module singleton (`provider.py:24`), while `nodes.py:190,735` builds throw-away `VisionFallback()` instances only for the availability checks.

---

## 8. Evidence record schema and on-disk layout

**Base directory.** `EvidenceManager.evidence_dir = resolve_path(log_dir)/"evidence"` = **`~/.pilot/logs/evidence/<task_id>/`** (`evidence/manager.py:44-52`, `config.py:19`). It is **not** `~/.pilot/evidence/` as the README and ARCHITECTURE.md say.

Files written per task:

| File | Written by | Semantics |
|---|---|---|
| `after_navigation.png` | `nodes.py:362` | once per navigation |
| `dom_observation.png` | `nodes.py:485` | **overwritten** on every `extract_dom` loop |
| `captcha_detected.png` | `nodes.py:442` | on CAPTCHA |
| `before_step_{llm_call_count}.png` / `after_step_{llm_call_count}.png` | `nodes.py:988-989`, `:1172-1173` | pre/post per executed action. The name is keyed by `llm_call_count`, so a retry at the same count overwrites it. |
| `final_completion.png` | `nodes.py:951` | on a `complete` action |
| `completion_proof.png` | `nodes.py:1480` | on verified completion |
| `dom_snapshot.json` | `evidence/manager.py:80-85` | the `ActionManifest`, **overwritten** each step (`nodes.py:953,991`) |
| `verification.json` | `manager.py:87-104` | appended list of each `ActionResult` (`nodes.py:1241`), task `VerificationResult` (`:1450`) and recovery records (`:1565`) |
| `execution_records.json` | `manager.py:113-134` | appended list of `ExecutionRecord` (only if `enable_evidence`, `nodes.py:1245`) |
| `trace.json` | `manager.py:61-78` | appended `{node, timestamp, status, error}` per LangGraph node (`runner.py:279-285`) |

**`ExecutionRecord` fields** (`evidence/manager.py:15-37`): `task_id`, `step_id` (`"S%03d"` of `llm_call_count`, `nodes.py:1247`), `step_index`, `action{type, element_id, text, url}`, `before_state{url, screenshot}`, `execution_result` (the full `ActionResult` dump), `after_state{url, screenshot, page_state}`, `evidence{before_screenshot, after_screenshot, dom_snapshot:"dom_snapshot.json"}`, `verification{action_success, error}`, `knowledge_context[{document_id, chunk_id, score}]`, `model`, `model_role`, `routing_reason`, `timestamp`, `duration_ms`, `node_name` (`nodes.py:1248-1290`).

Records are written only for executed browser actions: not for `complete` or `need_help` (`nodes.py:948-973`), and not for navigation in `navigate_node`. There is no integrity or immutability protection (plain `open(...,"w")`).

**Other persisted state:**

| What | Location | Source |
|---|---|---|
| SQLite database | `~/.pilot/data.db` | `config.py:17` |
| Checkpoints | `~/.pilot/data/checkpoints/<task>.json` (atomic replace) | `checkpoint.py:56-57,124-128` |
| Chroma store | `~/.pilot/chroma` | `memory/provider.py:59`, `rag/store.py:33` |
| Traces | `~/.pilot/logs/traces.jsonl` | `tracer.py:23-25` |
| Privacy audit | `~/.pilot/logs/privacy_audit.jsonl` | `config.py:81` |
| Profiling | `~/.pilot/logs/profiling/profile_events.jsonl` | `profiler.py:54-56` |
| Experiments | `~/.pilot/experiments/` | `config.py:85` |

`TelemetryTracker` would write `~/.pilot/evidence/<task>/telemetry.json` (`tracker.py:49-53`), but it is never called. `ReplaySystem` reads `~/.pilot/evidence/` (`replay/system.py:11`), which is a path mismatch with the evidence writer.

---

## 9. Memory and RAG

**SQLite tables** (`backend/db/database.py:53-112`):
- `tasks`: task_id, input_text, status, session_id, risk_level, parsed_intent_json, result_json, error, approval_id, timestamps.
- `task_events`: id, task_id, type, message, payload_json.
- `approvals`
- `settings`
- `sessions`: never written by the agent.
- `memories`: memory_id, type, content, task_id, tags_json, created_at, last_accessed_at, access_count.

**Chroma collections.** Both use a `PersistentClient` at `~/.pilot/chroma`, and neither passes an `embedding_function` or `hnsw:space` metadata:
- `pilot_memories` (`memory/provider.py:58-61`);
- `pilot_knowledge` (`rag/store.py:26-37`, `config.py:68`).

`rag_embedding_model="all-minilm"` (`config.py:77`) is **never read**, so Chroma's library default embedding function applies. `store.py:111-112` converts distance to similarity assuming cosine distance in [0,2]. Chroma's default space is L2 (library behaviour, not checked in this repo), so the `rag_similarity_threshold=0.45` (`config.py:70`) may not mean what its name suggests.

**What is stored:**
- `complete_node` on success: a `strategy` memory `"Strategy for '<action target>': {steps: llm_call_count, url, plugin}. Outcome: success."` (`nodes.py:1634-1645`, `provider.py:134-146`).
- `complete_node` on failure: a `failure_pattern` memory with the error and URL (`nodes.py:1646-1652`, `provider.py:148-160`).
- `TaskRunner` at the end of every non-approval run: an `episodic` summary `"Task: … Status: Success/Failed."` (`runner.py:314-315`, `provider.py:121-132`).

No selectors, action sequences or DOM paths are stored.

**Retrieval design:**
- `ContextRouter.route_and_retrieve` (`rag/router.py:62-134`) queries with `"{intent.action} {target or content}"` (`:82`).
- Knowledge RAG runs only if `should_retrieve_knowledge` passes (`:36-60`): `enable_rag`, and one of: a trigger keyword (e.g. "how to", "sop", "docs", "install"; `:19-23`), a plan with more than one step, or more than 4 words.
- `KnowledgeRetriever.retrieve` (`retriever.py:77-166`):
  - `top_k=5`, threshold 0.45 (`config.py:69-70`);
  - optional hybrid scoring `0.7·vector + 0.3·(query-term overlap ratio)` (`retriever.py:168-190`);
  - optional rerank bonus of +0.15 for an exact phrase and +0.10 for a heading-word match (`:192-215`);
  - LRU query cache with 100 entries and a 3600 s TTL (`:30-33`, `config.py:75`).
- Memory is always attempted when `enable_memory` is set: `retrieve_relevant(query, 3)` plus `retrieve_strategies(query, 2)` (`router.py:118-128`, `provider.py:90-119,162-168`).

**Influence on planning.** `plan_action_node` hands the retrieved lists to `ContextBuilder.build_context(role)` (`nodes.py:644-651`). The builder:
- uses a 3500-token budget (`config.py:62`);
- gives 65% to knowledge and 35% to memory (`context_builder.py:75,104-105`);
- estimates tokens as characters/4 (`:39-41`);
- deduplicates (`:43-64`);
- formats role-specific wrappers and the untrusted-content banner (`:139-167`, `rag/security.py:11-60`).

The result is inserted into the planning prompt as `{knowledge_block}` / `{memory_block}` (`nodes.py:666-674`).

**On the live path this influence is zero.** `TaskRunner` initialises both lists to `[]` (`runner.py:265-266`). A checkpoint restore also yields `[]` (`checkpoint.py:38-39,111-112`). The reuse short-circuit (`rag/router.py:71-77`) therefore returns the empty lists, and neither the Chroma query nor the knowledge query ever executes. The same is true for the experiment runner's initial state (`experiment/runner.py:104-105`). Memory is **written but never read** in production.

**No ingestion path is wired up.** `IngestionPipeline` is exported (`rag/__init__.py:10`) but no API, CLI or startup code calls it. `rag_knowledge_dir` (`config.py:76`) is unused. As shipped, the knowledge collection is empty unless populated externally.

---

## 10. Security

**Prompt-injection sanitizer** (`security/sanitizer.py`):
- There are 17 regexes (`:16-38`) in four groups:
  - instruction overrides: "ignore (all) previous instructions", "forget previous…", "disregard previous", "you are now a", "act as (if you are|a)", "new instructions:", "system:", `[system]`, `<system>`;
  - delimiters: "```system", "--- new prompt", "### instruction|system|prompt";
  - exfiltration phrasing: "send this/the/all data… to", "transmit … to http", "email … to x@y";
  - role manipulation: "you must always/never", "override your instructions".
- Each match is replaced with `[SANITIZED_CONTENT]` and a counter is incremented (`:54-84`). It is a pure denylist.
- **Applied to:** DOM element `text_content`, `aria_label` and `placeholder` (`nodes.py:655`), and RAG chunks (`rag/security.py:46`).
- **Not applied to:**
  - page title and URL, which go straight into the prompt (`nodes.py:676-677`);
  - memory content (`context_builder.py:113`);
  - extracted page text;
  - element `css_selector`/`xpath`;
  - the screenshot sent to the VLM.
- `sanitize_page_content` (`:96-98`) is never called.
- Separate credential-shaped redaction exists only for observability events: `broadcaster.redact_sensitive` (`telemetry/broadcaster.py:16-41`), and the observatory's `_redact` (`observatory/backend/storage.py:17`).

**PrivacyAuditor.** It **exists** (`security/audit.py:22`). It logs:
- per LLM call: timestamp, `task_id` (always `"global"` because it is not passed; see `gateway.py:114-120`), model, destination (`ollama_base_url`), `is_local` (the string contains `127.0.0.1` or `localhost`), prompt and response byte counts, and latency (`audit.py:51-80`);
- nothing on the browser side: `record_external_request` (`:82-106`) is **never called**. Browser traffic, form submissions and page fetches are not audited.

`is_local` is recorded but **not enforced**: a remote `PILOT_OLLAMA_BASE_URL` would be accepted and used (`gateway.py:32`). Separately, `tracer.record_llm_call` stores the **first 500 characters of every prompt and response** in `traces.jsonl` (`tracer.py:43-52`). That is local, but it is sensitive-content logging.

**Credentials and keyring.** `CredentialStore` wraps `keyring.set/get/delete_password("Pilot", …)` (`credentials.py:8-27`) but is **referenced nowhere**. `auth_check_node` is a no-op (`nodes.py:284-288`). `SessionRegistry` (`sessions.py:10-33`) is unused.

**Approval gate / risk check.** `requires_approval` returns True if `intent.action` is in {post, send_email, purchase, delete, transfer}, or if `risk_level` is in {high, critical} (`security/approval.py:5-16`).
- `risk_level` is chosen by the intent LLM following the rubric in `prompts.py:11-15`.
- If the LLM omits it, `sanitize_schema_data` fills the missing required string with the literal `"default"` (`llm/parser.py:161-167`), which does **not** trigger approval.
- The gate runs once before navigation (`nodes.py:266`) and is re-checked at verified completion (`nodes.py:1499`).
- The decision goes through `POST /api/approvals/{id}/respond` (`api/approvals.py:18-31`) → `TaskRunner.approve` (`runner.py:75-94`).
- `auto_approve_low_risk` (`config.py:23`) and `approval_timeout_seconds=10` (`config.py:24`) are **never read** by the gate.
- CAPTCHA resume and fallback re-schedule with `approved=True` (`runner.py:138,188`).

**`code_executor` sandboxing.** **None.**
- `_resolve_safe_path` resolves relative paths against the workspace root but accepts any absolute path, with no containment check (`agent/code_executor.py:25-30`).
- It reads and writes arbitrary files (`:32-101`).
- It never executes code; it only calls `ast.parse` (`:103-134`).
- It is not wired into the graph (only `tests/test_multi_model_integration.py:10`).

**Browser isolation.** Chromium is launched with `--no-sandbox` and `--disable-blink-features=AutomationControlled` (`browser/pool.py:90-93`). Contexts use a spoofed Chrome 124 user agent (`pool.py:127`) and an init script that hides `navigator.webdriver` (`pool.py:138`).

**CAPTCHA policy.**
- It detects the challenge (§5), sets `blocked`, retains the browser for a human, and records `recovery_options ["manual_captcha","safe_search_fallback"]` (`nodes.py:465-480`).
- It does not solve CAPTCHAs; no solver code exists.
- Resuming via `POST /api/tasks/{id}/resume` re-checks `detect_captcha` and refuses while the CAPTCHA is still present (`runner.py:106-139`, `api/tasks.py:64-81`).
- Fallback via `POST /api/tasks/{id}/fallback` goes to `html.duckduckgo.com` or Bing (`runner.py:141-189`).

The system does, however, **actively reduce bot detectability**: the webdriver masking and UA spoofing above, and rewriting direct `google.com/search` navigation into typed queries "that triggers bot detection" (`nodes.py:869-880`). An ethics or limitations section should disclose this.

**API exposure.**
- The backend binds to `127.0.0.1` (`backend/main.py:149`).
- CORS allows only localhost origins (`:78-91`).
- There is no authentication on any route.
- `POST /api/setup/pull-model` runs `ollama pull <model>` with a user-supplied model name (argv form, no shell; `api/settings.py:51-66`).
- The evidence file route checks for path traversal with `abspath().startswith` (`api/tasks.py:121-137`).

---

## 11. Observatory

**What it is.** A separate FastAPI service on 127.0.0.1:8766 (`observatory/backend/main.py:67-69`) plus a React/Vite dashboard: 2,596 lines in `observatory/frontend/src`, with 13 panel components, e.g. `ModelRouterPanel.tsx`, `VerificationPanel.tsx`, `LangGraphStateView.tsx`.

**How it gets telemetry.**
- `EventStreamManager` connects to Pilot's `ws://127.0.0.1:8765/ws/observability` and falls back to SSE `/api/observability/stream`, with exponential-backoff reconnects (`observatory/backend/event_stream.py:20,115-190`).
- Pilot publishes into that stream from `Database.add_event`, which forwards every task event to `broadcaster.broadcast`. The broadcaster redacts credential-like keys and patterns and keeps a 500-event ring buffer (`backend/db/database.py:215-227,247-264`, `telemetry/broadcaster.py:58-110`).
- The Pilot endpoints are `backend/api/observability.py:19-114`.

**Is it read-only?** By convention, not by enforcement. `ReadOnlyStorage` (`observatory/backend/storage.py:32-52`) opens `~/.pilot/data.db` with plain `aiosqlite.connect(path)`, not SQLite `mode=ro`, but it issues only SELECTs. It also reads checkpoint JSON (`storage.py:159-170`) and serves evidence files from `~/.pilot/logs/evidence` with a containment check (`observatory/backend/api.py:79-84`). The only control it sends upstream is WS `ping` / `subscribe_task` (`backend/api/observability.py:95-100`). It cannot steer the agent.

**Tests.** 20 tests in `observatory/tests/test_observatory.py`, excluded from default collection because `pytest.ini:3` sets `testpaths = tests`.

---

## 12. Experiment framework

**What `python main.py --eval` does.** `PilotOrchestrator.run_eval` (`main.py:603-631`) runs, if present:
- `scratch/phase3_startup_eval.py`
- `scratch/phase4_5_6_eval.py`
- `scratch/phase7_8_9_rag_memory_eval.py`
- `scratch/phase10_checkpoint_eval.py`
- `scratch/phase11_playwright_eval.py`
- `scratch/phase12_13_14_eval.py`
- `scratch/phase16_to_21_eval.py`
- `scratch/generate_pdf_report.py`

(`main.py:608-617`). `scratch/` is gitignored (`.gitignore:47`) and **absent**, and missing scripts are silently skipped (`main.py:622`). **Result: a no-op that exits 0.** It never touches `backend/experiment/`.

**Ablation presets** (`backend/experiment/config.py:23-201`), exact keys and overrides:

| Preset | Overrides |
|---|---|
| `full_framework` | multi_model=T, strategy=dynamic, rag=T, evidence=T, verification=T, recovery=T, memory=T |
| `single_model` | multi_model=F, strategy=single, rag/evidence/verification/recovery/memory=T |
| `multi_model_static` | multi_model=T, strategy=static, rest T |
| `multi_model_dynamic` | multi_model=T, strategy=dynamic, rest T (**identical to `full_framework`**) |
| `dynamic_routing_rag` | multi_model=T, strategy=dynamic, rest T (**identical to `full_framework`**) |
| `no_rag` | rag=F, evidence/verification/recovery/memory=T |
| `rag_only_no_memory` | rag=T, memory=F, evidence/verification/recovery=T |
| `memory_only_no_rag` | rag=F, memory=T, evidence/verification/recovery=T (**same flags as `no_rag`**) |
| `rag_hybrid` | rag=T, rag_hybrid_search=T, rest T. The description says "BM25" (`:124`); the code uses a set-overlap ratio (`retriever.py:175-187`) |
| `rag_with_reranking` | rag=T, rag_reranking=T, rest T. The description says "neural/cross-encoder" (`:136`); the code uses fixed string bonuses (`retriever.py:192-215`) |
| `no_evidence` | evidence=F, rest T |
| `no_verification` | verification=F, rest T. **No effect on agent code** (§5) |
| `no_recovery` | recovery=F, rest T |
| `no_memory` | memory=F, rest T (**same flags as `rag_only_no_memory`**) |
| `baseline_direct` | rag, evidence, verification, recovery, memory all F. multi_model is not overridden, so it inherits the base config |

That is 15 presets but only 10 distinct flag sets. `STANDARD_BENCHMARK_TASKS` (`config.py:204-218`) holds 8 strings: 4 browser tasks, 1 "screenshot" task, 1 coding task, 1 SOP task and 1 "recover from network timeout" task. The last four have no ground-truth success criterion.

**`ExperimentRunner.run_experiment`** (`experiment/runner.py:30-171`):
- It mutates the cached `PilotConfig` via `setattr` and restores it afterwards (`:49-65,136-139`).
- For each task it attempts `from backend.agent.graph import create_agent_graph` (`:82-83`). **That symbol does not exist** (`graph.py` defines only `build_graph`), so each task gets `ImportError` → `status="failed"` (`:120-123`).
- Even if the import were fixed, the database is never connected in this path, and `update_task` would raise (`database.py:123-128`). That is my inference: nothing in `runner.py` calls `database.connect()`.
- `approved=True` is forced, auto-approving high-risk actions (`:99`).
- `ExperimentConfig.models` and `runs_per_task` are unused (`config.py:17,19`).
- No code calls `ExperimentRunner` or `run_ablation_comparison`.

**Metrics recorded:** `total_tasks`, `completed_tasks`, `success_rate_percent` (status=="completed"), `average_duration_ms`, `average_steps` (= `llm_call_count`), and per-task `{task_id, task_text, status, duration_ms, step_count, error}` (`runner.py:141-163`).

**Outputs:** `~/.pilot/experiments/exp_<preset>_<epoch>.json` and `ablation_study_<epoch>.json` (`runner.py:26,166-168,195-197`).

**Other evaluation scripts:**
- `benchmarks/run.py` runs 3 navigation prompts through `TaskRunner` (`:17-21`) and writes `BENCHMARK_RESULTS.md` with **hard-coded** "Vision Fallback Success Rate 100% (Simulated)", "Browser Latency 0.8s (Estimated)" and "LLM Latency 2.3s (Estimated)", plus `memory_recall_accuracy: 1.0` (`:27,63-66`).
- `scripts/certify.py` runs 5 prompts. A test passes if the task is completed **and** any `.png` plus `trace.json` exist (`:40-44`).
- `scripts/validate_vision.py` reports PASS whenever no exception is raised. `VisionFallback.plan_action` converts model errors into a `need_help` action (`vision/fallback.py:117-122`), so PASS does not imply a successful VLM call. The report text claims "received bounding box coordinates" unconditionally (`validate_vision.py:38`).
- `scripts/benchmark.py` runs 3 prompts and prints raw status.
- `tracer.get_aggregated_metrics` (`tracer.py:128-281`) computes completion, recovery and verification rates, and RAG/routing stats, from `traces.jsonl`. In production, no code emits the `recovery/attempt` or `verification/check` events (the only callers are `tests/test_case_study_enhancements.py:229-231`), so those rates are always 0. `routing_overhead_ms` and `routing_efficiency` are formula constants, not measurements (`tracer.py:243-246`).

---

## 13. Test suite

Counts come from grepping `^\s*(async )?def test_` per file. No `parametrize`, `skip` or `xfail` markers are used.

| Subsystem | Test files (test functions) | Total |
|---|---|---|
| Agent nodes / pipeline / CAPTCHA / checkpoint / runner | `test_browser_agent_pipeline.py` (7), `test_navigation_transition_and_typing.py` (10), `test_captcha_handling.py` (7), `test_checkpoint_and_optimization.py` (7), `test_recovery_engine.py` (4), `test_task_runner.py` (2, **fails to collect**) | 37 |
| LLM routing / registry / parser | `test_model_router.py` (7), `test_model_registry.py` (7), `test_multi_model_integration.py` (5), `test_parser.py` (1) | 20 |
| RAG | `test_rag_chunking.py` (3), `test_rag_context.py` (2), `test_rag_ingestion.py` (3), `test_rag_integration.py` (4), `test_rag_retrieval.py` (4), `test_rag_router.py` (3), `test_rag_security.py` (3), `test_multi_model_rag.py` (6) | 28 |
| Cross-cutting (config, evidence, verification, recovery, sanitizer, privacy, desktop, telemetry, ablation presets) | `test_case_study_enhancements.py` (11) | 11 |
| DB / plugins / launcher | `test_database.py` (1), `test_plugins.py` (2), `test_launcher.py` (8) | 11 |
| **E2E** (live Ollama + Chromium + network) | `tests/e2e/test_certification.py::test_certification_suite` (1); `tests/e2e/test_runner.py::test_runner_execution_flow`, `::test_high_risk_approval_flow` (2) | 3 |
| Observatory | `observatory/tests/test_observatory.py` (20), not in the default testpaths | 20 |

In total that is 25 test files and **130** test functions: 110 under `tests/` and 20 under `observatory/tests/`.

A concurrent run in this workspace (`artifacts/results/pytest_run2_full.txt`, run with `--continue-on-collection-errors`) reports **103 passed, 5 failed, 1 collection error**. The failures are:
- `e2e/test_certification_suite`
- `test_vision_unavailable_fails_explicitly`
- `test_action_failure_never_marks_completed`
- `test_vision_fallback_screenshot_caching`
- `test_launcher::test_different_working_directory`

The collection error is `test_task_runner.py` (`NameError: Database` at line 103). A plain `pytest -q` stops at that collection error (`pytest_run1_default.txt`).

Caveats:
- `tests/e2e/test_runner.py` accepts either `completed` or `failed` (`:35,58`), so it cannot fail on the agent's outcome.
- No test calls `build_graph()` or runs a full graph with mocks. Node tests call node functions directly with `PlaywrightExecutor` and the gateway patched (e.g. `test_navigation_transition_and_typing.py:185-186`).
- `main.py --test` runs only 3 files (`main.py:593-597`).
- The wiki's `--cov` command needs `pytest-cov`, which is not in `backend/requirements.txt`.

---

## 14. Discrepancies (docs/README/wiki claim → what the code shows)

1. **"Zero Exfiltration"** (`README.md:425`), **"zero cloud egress"** (`wiki/Home.md:69`), and **"100% data privacy"** (`wiki/Home.md:5`).
   - LLM calls go to a configurable `ollama_base_url`, and locality is logged but not enforced (`audit.py:68`, `gateway.py:32`).
   - The browser necessarily sends user-provided form content to target sites.
   - There is no egress control of any kind.
   - Chroma's default embedding function may fetch model weights on first use. That is library behaviour and was not checked here; no `embedding_function` is set (`provider.py:61`, `store.py:37`).
   - **Partially supported**, only in the sense that LLM inference runs locally by default.
2. **"Outbound requests and payload sizes are logged by `PrivacyAuditor` … to ensure no data exfiltration"** (`README.md:220`), and **"Logs all outbound traffic"** (`docs/configuration.md:67`).
   - `record_external_request` is never called. Only Ollama call sizes are logged, all under `task_id="global"`.
   - "Cryptographic privacy audit trails" (`wiki/Configuration.md:78`) is false: the log is plain appended JSONL (`audit.py:116-122`).
3. **"credentials (stored in OS keychain via `keyring`)"** (`README.md:219,426`).
   - `CredentialStore` exists but nothing uses it.
   - There is no login or auth flow (`auth_check_node` is a no-op).
4. **"anti-thrashing cooldown"** (`README.md:42`, `docs/architecture.md:62`), and `PILOT_MODEL_SWITCH_COOLDOWN_STEPS` "hold an active model" (`wiki/Configuration.md:57`, `docs/configuration.md:19`).
   - The config field is never read.
   - Only capability-based stickiness exists (`router.py:121-135`).
5. **"python main.py --eval — Run research ablation benchmarks"** (`README.md:311`).
   - It runs missing `scratch/` scripts and so does nothing.
   - `ExperimentRunner` is broken (ImportError) and never called.
6. **Recovery "escalation ladder"** (`wiki/CAPTCHA-and-Failure-Recovery.md:9-63`): alt-selector, vision fallback, replan, "exponential backoff", "increased JSON temperature constraints".
   - The strategies are computed labels that are then dropped. No behaviour differs between them.
   - There is no backoff or temperature logic in `engine.py`.
   - The `socket hung up` and `URL mismatch` signatures (`wiki …:58,60`) are not in `FAILURE_TYPES`.
7. **"Episodic Strategy Learning … to inform future planning"** (`README.md:52`) and "learning which selectors, workflows, and navigation paths succeed" (`wiki/Experience-and-Learning.md:3`).
   - Retrieval is bypassed on the live path (§9).
   - The stored "strategy" is only `{steps, url, plugin}` (`nodes.py:1635-1639`), with no selectors or workflows.
8. **Evidence location and immutability.** "`~/.pilot/evidence/`" (`README.md:50,79`, `docs/architecture.md:36`) and "immutable … `before.png`, `after.png`, `trace.json`, `dom_snapshot.json`, `telemetry.json`" (`ARCHITECTURE.md:33`).
   - The actual path is `~/.pilot/logs/evidence/`.
   - The files are `before_step_N.png` / `after_step_N.png`.
   - `dom_snapshot.json` and `dom_observation.png` are overwritten.
   - `telemetry.json` is never produced (the tracker is unused).
   - `ReplaySystem` looks in the wrong directory, so the `/replay` endpoint returns 404 for real tasks.
9. **"Hard Verification Gate … `ACTION_SUCCESS != TASK_SUCCESS`"** (`README.md:47`) and "DOM Mutation Check (compute DOM diff)" (`wiki/Evidence-and-Verification.md:19,99`).
   - Task-level gating is implemented (§5).
   - `verify_dom_mutation` always passes.
   - `verify_visual` is a stub.
   - `type_text` has an unverified success fallback.
   - Step completion is based on action success only.
   - `enable_verification=False` changes nothing.
   - **Partially supported.**
10. **"LangGraph construction … with a simple fallback runner"** (`graph.py:1`). There is no fallback runner (`runner.py:217-219`).
11. **"Chromium Sandbox"** (`wiki/Architecture.md:62`). The browser is launched with `--no-sandbox` (`pool.py:92`).
12. **"Sequential IDs `[ID 0]`, `[ID 1]`"** (`wiki/Browser-Automation.md:64`). IDs are the strings `pilot-el-<n>` (`dom.py:152`). This is minor.
13. **`PILOT_MAX_RETRY_COUNT` = "max retries per individual action before strategy escalation"** (`wiki/Configuration.md:67`) and "Maximum recovery attempts per action" (`docs/configuration.md:41`). It actually governs Ollama call retries (`gateway.py:80,175`). Action retries are hard-coded as 3 (`nodes.py:1369`) and 6/2 (`engine.py:61`).
14. **Models named in docs but absent from the code registry.** `qwen2.5:0.5b` (`wiki/Home.md:39`, `wiki/Local-LLM-and-Model-Routing.md:69`, `wiki/Installation-and-Setup.md:32`) is not among `DEFAULT_KNOWN_MODELS` (`registry.py:71-172`).
15. **The Observatory is described as "Read-Only"** (`docs/observability.md:31`). It is read-only by convention only: the SQLite connection is not opened read-only (`storage.py:47`).
16. **Ablation preset descriptions:**
    - "BM25/lexical" (`experiment/config.py:124`) versus a set-overlap ratio in code;
    - "local neural/cross-encoder reranking" (`:136`) versus fixed string bonuses;
    - "blind LLM completion" for `no_verification` (`:159`) versus no code effect;
    - three presets are identical to `full_framework`.
17. **Test-suite description.** "Database Isolation … in-memory SQLite (`sqlite:///:memory:`)" (`wiki/Testing-and-Evaluation.md:76`): no test uses `:memory:`; they use `tmp_path` files. The "Escalation Resolution Rate … via alternative selectors or vision fallback" metric (`:86`) cannot be measured, because the strategies are not executed and recovery events are not traced.
18. **Validation reports and certification artifacts.**
    - `CERTIFICATION_REPORT.md` (all PASS) is produced by `scripts/certify.py`, whose pass criterion is only "completed + any PNG + trace.json" (`certify.py:40-44`).
    - `VISION_VALIDATION.md`'s "received bounding box coordinates" is a template string (`validate_vision.py:38`).
    - The `BENCHMARK_RESULTS.md` template embeds hard-coded simulated or estimated figures (`benchmarks/run.py:63-66`).
    - None of these is evidence of performance.
19. **Case-study hard-coding not disclosed in the docs.**
    - `extract` actions always produce a "Kattankulathur Campus" answer and, when there are fewer than 3 relevant lines, **fabricated fallback facts** (`nodes.py:1108-1139`).
    - The default page title is "SRM Institute of Science and Technology" (`:1108`).
    - The click fallback matches the literal `"srm"` (`:1052`).
    - This inflates extraction "success" for any task and invalidates generic extraction claims.
20. **Plugins** (Gmail, Twitter, Google Forms) listed as capabilities. `execute()` is never invoked by the graph, and the plugins are dry-run stubs (`plugins/builtin/gmail.py:47-52`); only `plugin_id` is recorded (`nodes.py:237`).
21. **"Desktop task automation"** (`README.md:24`). `DesktopExecutor` exists but no graph node or action type dispatches to it.
22. **The `auto_approve_low_risk` setting** is exposed in the settings API and UI (`api/settings.py:29,43-47`) but has no effect on approval (`security/approval.py:8-16`). The `ollama_model` DB setting (`api/settings.py:39-40`) is likewise never read by the gateway, which uses `config.ollama_model` (`gateway.py:78`).

---

## 15. Lines of code (`wc -l`, all lines including blanks and comments)

| Subsystem | LOC |
|---|---|
| `backend/agent` (graph, nodes 1682, runner 372, checkpoint 185, code_executor 139, prompts 81, state 49) | 2,593 |
| `backend/llm` (registry 347, parser 218, gateway 204, router 203, analyzer 193) | 1,193 |
| `backend/browser` (pool 391, executor 323, dom 227, actions 192) | 1,134 |
| `backend/rag` (incl. ingestion 434) | 1,355 |
| `backend/telemetry` (tracer 285, profiler 263, broadcaster 142, tracker 57) | 747 |
| `backend/api` | 684 |
| `backend/db` | 472 |
| `backend/experiment` | 431 |
| `backend/security` (audit 125, sanitizer 107, sessions 36, credentials 27, approval 25) | 321 |
| `backend/verification` | 320 |
| `backend/plugins` | 271 |
| `backend/desktop` | 242 |
| `backend/recovery` | 214 |
| `backend/memory` | 195 |
| `backend/evidence` | 151 |
| `backend/vision` | 146 |
| `backend/replay` | 43 |
| `backend/config.py` + `backend/main.py` + `__init__` | 243 |
| **backend total (Python)** | **10,755** |
| `observatory/backend` (Python) | 796 |
| `observatory/frontend/src` (TSX/TS/CSS) | 2,596 |
| `frontend/src` (TSX/TS/CSS) | 1,780 |
| `src-tauri/src` (Rust) | 205 |
| `main.py` (launcher) | 777 |
| `tests/` (Python) | 3,373 |
| `observatory/tests` | 477 |
| `scripts/` | 369 |
| `benchmarks/` | 75 |

`nodes.py` alone accounts for 15.6% of the backend: 1,682 of 10,755 lines.
