# 10 — Computer-Use Capability Audit (before the paper reframing)

**Repository state.** Branch `ccr-4b8200f0-5i3k5m` at `ec1f030`, with agent code at `eb3803e`. `origin/main` has no newer commits (`2361d50`).

**Method.** Code was read directly and grep'd for every library or API a computer-use backend would need. Test runs come from `artifacts/results/pytest_after_fixes.txt`. Experiments come from `artifacts/results/*`. Documentation was not counted as evidence.

**Labels.**
- **IMPLEMENTED:** the code exists and runs on the agent's live path.
- **PARTIAL:** code exists but is incomplete, unintegrated, or only partly effective.
- **TESTED:** an automated test exercises the behaviour, not merely its interface.
- **EVALUATED:** measured in an experiment reported in the paper.
- **PROPOSED:** a design exists (artifact 02, paper §IV-G) but no code.
- **FUTURE:** neither design detail nor code exists.

| # | Capability | Code (file:line) | Integrated in agent graph? | Tested? | Evaluated? | Label |
|---|---|---|---|---|---|---|
| 1 | Browser control (Playwright: navigate, click, type, key, scroll, select, extract, screenshot) | `backend/browser/executor.py`, `pool.py`; dispatch in `agent/nodes.py` `execute_action_node` | yes | yes (node tests with stubbed executor; e2e needs web) | component only (gate study runs real Chromium on fixture pages) | IMPLEMENTED, TESTED, component-EVALUATED |
| 2 | Desktop / OS mouse–keyboard control | `backend/desktop/executor.py:47-203` (PyAutoGUI click, write, hotkey, screenshot, size) | **no**: no node, action type or API route imports it; only `tests/test_case_study_enhancements.py:27` | interface only (`hasattr` checks, `:209-216`) | no | PARTIAL (prototype, unintegrated) |
| 3 | Browser-level mouse/keyboard (viewport coordinates from vision) | `nodes.py` `VISION_COORD` branch (Playwright `page.mouse` / `keyboard`) | yes | mocked | no | IMPLEMENTED, TESTED (mock) |
| 4 | Screenshots, browser | `executor.get_screenshot_with_dimensions`; evidence before/after per action | yes | yes | used in gate study | IMPLEMENTED, TESTED |
| 5 | Screenshots, desktop | `desktop/executor.py:181-193` | no | interface only; returns empty bytes headless | no | PARTIAL |
| 6 | Accessibility-tree interaction (UIA / AX / AT-SPI) | none (grep: pywinauto, uiautomation, atspi → 0 hits) | no | no | no | PROPOSED (artifact 02 §2.3) |
| 7 | DOM grounding | `browser/dom.py` `DOMExtractor` | yes | yes | indirectly (gate study pages) | IMPLEMENTED, TESTED |
| 8 | Vision grounding (browser screenshot → viewport point) | `vision/fallback.py`, `nodes.py` `need_help` branch | yes (fires on `need_help`; also forced by `vision_fallback` recovery when a vision model exists) | yes (mocked model) | **no** (needs Ollama) | IMPLEMENTED, TESTED (mock) |
| 9 | Native application interaction | none | no | no | no | FUTURE (design only at the level of artifact 02) |
| 10 | Filesystem operations | `agent/code_executor.py` (read, write, replace, AST check) | **no** (not imported by the agent) | yes (`test_multi_model_integration.py:69`) | no | PARTIAL (unwired; no path confinement) |
| 11 | File-state verification predicate | `verification/manager.py` `verify_file_state` (exists, min size) | **no** (no node calls it) | yes (`test_case_study_enhancements.py:127-132`) | no | PARTIAL (tested, unintegrated) |
| 12 | Process operations | `desktop/executor.py:205-233` `list_processes` (psutil, read-only) | no | no | no | PARTIAL (list only); launch and terminate are PROPOSED |
| 13 | Window operations (focus, title, close) | none | no | no | no | PROPOSED |
| 14 | Permission / approval | `security/approval.py`, `risk_check_node`, `/api/approvals` (task-level, model-assigned risk) | yes | partly (needs web: `test_task_runner.py::test_high_risk_post_waits_for_approval`; e2e) | no | IMPLEMENTED (task-level); per-action tiers PROPOSED |
| 15 | Evidence collection | `evidence/manager.py`; `nodes.py` | yes | yes | no (completeness not measured) | IMPLEMENTED, TESTED |
| 16 | Completion verification (browser Φ) | `verification/manager.py` `verify_task_completion`; `nodes.py` `verify_node` | yes | yes (incl. 19 regression tests) | **yes**, component level: 38 design + 12 held-out states, before and after fixes | IMPLEMENTED, TESTED, component-EVALUATED |
| 17 | Recovery | `recovery/engine.py`; `error_recovery_node` | yes (classification, bounds); only `vision_fallback` changes behaviour | yes | no | IMPLEMENTED (classification), PARTIAL (strategies) |
| 18 | Memory / RAG | `memory/provider.py`, `rag/*`; retrieval active since `5359458` | yes | yes (RAG unit tests) | no | IMPLEMENTED, TESTED, not evaluated |
| 19 | Model routing | `llm/router.py`, `analyzer.py` | yes | yes | routing resolution study (no inference) | IMPLEMENTED, TESTED, EVALUATED (resolution only) |
| 20 | CAPTCHA halt | `browser/dom.py` `detect_captcha`; `verify_node` | yes | yes | in gate study | IMPLEMENTED, TESTED, component-EVALUATED |
| 21 | Tauri shell OS access | `src-tauri/src/*.rs`: commands only for Ollama status and backend health | n/a | n/a | n/a | No OS-control commands |
| 22 | Evaluation scripts | `main.py --eval` → `experiment/runner.py` presets (6) | n/a | presets as data | **not run with a model** | IMPLEMENTED (harness), not EVALUATED |
| 23 | Plugins (Gmail, Forms, Twitter) | `plugins/builtin/*` `execute()` returns `dry_run: True`; never called by the graph | no | registry only | no | PARTIAL (stubs) |

## Consequences for the paper

1. **Agentic Pilot today is a local browser agent.** Its computer-use backend is a prototype plus unwired helpers. The paper can present the computer-use direction only as a **generalized verification model** and an **architecture with one implemented backend (browser)** and one **proposed backend (computer)**.
2. **No experiment** covers desktop, file, process or window actions. The only computer-relevant code with a test is `verify_file_state`, a unit test of an unintegrated predicate. It cannot be reported as an evaluation.
3. **Measured results are browser-component evidence only:** the gate study, routing resolution and the test suite. None of them shows end-to-end task success.
4. **"Privacy-preserving" must stay scoped** to "model inference stays on the host by default" (paper §VIII).
5. **The title must not call the system a computer-use agent without qualification.** A computer-use backend does not exist in the agent.
