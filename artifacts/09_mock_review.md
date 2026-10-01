# Mock Review: "Agentic Pilot: An Evidence-Driven Local Autonomous AI Agent Framework for Privacy-Preserving Intelligent Task Automation"

Reviewer #2. Expertise: LLM agents, web/GUI automation, systems security.
Draft reviewed: `paper/main.tex` and all `\input` files (sections/, figures/, tables/). Code at commit `2361d50` (backend unchanged at HEAD `2b8db6e`). Evidence: `artifacts/`.
The red `\todo{}` markers are acknowledged (author block, license/DOI, hardware and model digests, the 30-task suite, all end-to-end numbers, the case study, and the case-study extraction code). I judge the paper as it stands and do not penalize the TODOs twice. Where a TODO covers a central claim, I say so.

---

## 1. Summary

The paper presents Agentic Pilot, an open-source browser agent. It runs local Ollama models, drives Chromium through Playwright, and is structured as an 11-node LangGraph state machine. Its main idea is to separate action dispatch from task completion. A rule-based predicate Φ, evaluated on the live page, must hold before the agent reports "completed". The paper formalizes this and defines a false completion rate (FCR). The authors also describe DOM-first grounding with a vision-model fallback, role-based routing to small local models, CAPTCHA halting, a task-level approval gate, and a per-step evidence store. A candid code audit lists which mechanisms are inactive (strategy-specific recovery, memory retrieval, routing cool-down, the verification ablation flag). The only measurements are (a) a 35-fixture offline study of Φ against a dispatch-only baseline (FCR 0.629 → 0.368, one false rejection, median 33.8 ms), (b) a router trace with no inference, and (c) the repository test suite. A desktop/local-system extension is designed but not implemented, and all end-to-end results are left as TODO.

## 2. Scores

| Criterion | Score (1–5) | Justification |
|---|---|---|
| Novelty | 2 | Checking environment postconditions before declaring success is standard: benchmark checkers, classical planning postconditions, and in-loop evaluators (e.g., Pan et al. 2024, Magentic-One's progress ledger). What is new here is a keyword-triggered if-chain inside one agent, not a new idea. |
| Technical soundness | 2 | Φ is largely vacuous on the live path. It reduces to "no HTTP-error title" for goals that trigger no keyword, and its answer and plan conjuncts are satisfied by the planner's own `reasoning` string. The fixture harness does not reproduce the live `verify_node`, and the extraction path contains hard-coded answer fabrication. There are no end-to-end results. |
| Clarity | 4 | Well written, candid and precise about inactive mechanisms. However, several descriptive sentences state the design rather than the code (see §4). |
| Reproducibility | 3 | Component scripts, CSVs and the commit hash are provided, and the numbers match exactly. Dependencies are unpinned (`>=`), Playwright had to be re-pinned by hand, the 30-task suite and oracles are unpublished (TODO), and routing depends on a process-global router state. |
| Significance | 2 | Without end-to-end measurements the community learns only that a hand-written rule accepts or rejects hand-written fixtures written to exercise it. The desktop extension, about a quarter of the method section, is a proposal only. |

**Overall recommendation:** Reject (resubmit after end-to-end evaluation and after fixing Φ and the extraction path).
**Confidence:** 4/5. I read the relevant code paths line by line and re-ran probes on the router, the exact-text extractor, the CAPTCHA detector and the page-state classifier.

---

## 3. Top 5 weaknesses (ranked)

### W1. No end-to-end evidence for any claim about the agent (TODO covers the central result)
The abstract and conclusion frame the paper around an agent that "refuses to report success until a check on the observed page passes". Yet no task was ever run with a model: Sec. VII-D is entirely TODO, and the two "passing" e2e tests accept `failed` as success (`tests/e2e/test_runner.py:34-35,58`). The unit test that most directly targets the central guarantee, `test_action_failure_never_marks_completed`, times out (`artifacts/results/pytest_output.txt:134`). The paper describes this only as "one times out waiting on a browser page" (Sec. VII-C).
**Required fix:** Run the protocol of Sec. VI on at least the 30-task suite in all configurations (i)–(v), with three trials each, an independent blinded oracle and Wilson CIs. Report success rate, FCR, false-rejection rate and cost. Make the core-property test pass before claiming the property.

### W2. On the live path Φ is much weaker than the formal model and the fixture study suggest
- **Keyword triggers.** Every conjunct except ¬β is keyword-triggered (`backend/verification/manager.py:204-228,241,267,283`). For any goal that contains no search/extract keyword, no "type/enter", and has fully-completed steps, Φ ≡ ¬β, i.e., "the title is not one of four HTTP error phrases".
- **Φ runs after any action, and ŷ is that action's reasoning.** Φ is evaluated after *every* successful action once the plan index reaches n (`backend/agent/nodes.py:1431-1435`). For every one-step plan, which is the default for short requests (`nodes.py:119,172-187`), this means from the first action onward. In that call ŷ := `state.final_answer or action.reasoning` for **whatever** action was just executed (`nodes.py:1448`), not only for `complete`. `PlannedAction.reasoning` is a required field (`backend/llm/parser.py:85`). So X is satisfied by any rationale longer than 40 characters that does not start with one of eight verbs (e.g., "I will type Alan Turing into the Wikipedia search box…").
- **R cannot fire on the live path.** Steps below the current index are completed by construction (`nodes.py:1393-1401`, `navigate_node` `:375-382`). The final step is marked on dispatch, and when the planner emits `complete`, ŷ is its non-empty reasoning. So R can essentially never reject in the live agent (the only exception is an empty reasoning string).
- **Consequence for the headline numbers.** The fixture study's X2 ("no answer produced") and P1 ("second step pending") count toward the 15 prevented completions. Both are states the live `verify_node` would very likely accept.

**Required fix:**
1. Re-run the gate study through `verify_node` itself, with `planned_action` and `action_history` populated as the graph would, and report how many of the 15 survive.
2. Stop using planner reasoning as ŷ.
3. Derive per-step predicates from `expected_outcome`.
4. Add negative controls in which no keyword fires.

### W3. The fixture study is a unit test with a strawman baseline, not an evaluation
- **Author-written cases and labels.** The 35 cases and their labels were written by the authors, who knew the rules, and several cases were written specifically to expose known gaps (Sec. VI-A admits this).
- **The baseline accepts everything by construction.** FCR therefore depends only on the case mix.
- **No realistic comparators.** There is no comparison with the planner's self-report, an LLM or VLM judge, or a DOM-diff heuristic.
- **No false-positive controls for β/CAPTCHA.** The CAPTCHA category has n⁺ = 0, so false blocking is never measured. My probe (same harness) shows that the Wikipedia "Robot" article and a page with a hidden invisible-reCAPTCHA iframe are both classified as CAPTCHA and would end as BLOCKED (`backend/browser/dom.py:24,55`).
- **Latency is not representative.** The 33.8 ms figure is measured on pages of a few hundred bytes. Real DOMs make `inner_text()` over `body` plus nine selector counts much slower.

**Required fix:** Build the fixture set from real recorded end states (e.g., sampled from WebArena/Mind2Web trajectories, or from the 30-task E2E runs), labelled by people who do not know Φ. Include satisfied states for every category. Add a planner self-report baseline and a VLM-judge baseline. Measure latency on real pages.

### W4. Case-study-specific answer fabrication and site-specific hacks inside the agent
The `extract` handler (`backend/agent/nodes.py:1105-1139`) is not mere "post-processing written for one case-study site" (Sec. IX):
- It rewrites **every** extraction answer as "3 Useful Pieces of Information about Kattankulathur Campus".
- When fewer than 3 page lines qualify, it inserts three **hard-coded facts** about the SRM campus (`:1121-1127`).
- It defaults the page title to "SRM Institute of Science and Technology" (`:1108`).
- It always populates `extracted_data`, which on its own satisfies conjunct X (`manager.py:273`).

The result is that an agent whose stated purpose is to refuse unverified completion can emit fabricated content as a "verified" answer, store it as evidence, and write it to memory. The click fallback also contains an `"srm"` special case (`nodes.py:1052`) that the paper does not disclose. Plan-step rewriting forces `extract` whenever a step description contains "read" (a substring that also matches "already", "thread", …; `nodes.py:893`).
**Required fix:** Remove this code before any evaluation and state in the paper that it existed. Audit the repository's prior "certification" numbers for dependence on it. List every site-specific rule in an appendix.

### W5. The routing, recovery and security descriptions overstate what runs, and the security design has basic gaps
- **Routing.**
  - Live vision calls never go through the router: the model comes from a hard-coded list (`backend/vision/fallback.py:65`), and no call site passes `has_image=True` (the only `route(` calls are `nodes.py:78,122,619,1529`).
  - The "recovery model" is routed but used for **no** inference, because `RecoveryEngine` makes no LLM call. Its selection nevertheless becomes `selected_model` (`nodes.py:1549`), so later planning sticks to the 7B model.
  - Substring keyword matching sends ordinary text calls to vision or coder models. Probed with the default install: "Find a guitar guide…", "Search Google Images…" and "Open the screening schedule…" all route intent parsing to **moondream** (`backend/llm/analyzer.py:28-31,115`). "fastest" matches the coding keyword "ast" (`analyzer.py:22-26`).
  - `_last_selected_model` is process-global (`router.py:121`), so routing depends on earlier tasks.
- **Recovery.** `retry_count` is shared between `verify` (3 retries, `nodes.py:1369`) and the engine (6 total, `recovery/engine.py:61,98`). The ladder therefore starts at `alternative_selector`, and `replan` is unreachable except through type-specific shortcuts.
- **Security.**
  - Approval is keyed to a free-text, model-produced `action` (`parser.py:15`) matched against `{post, send_email, purchase, delete, transfer}` (`security/approval.py:14`). The intent prompt only offers `post, send_email, fill_form, search, navigate` (`agent/prompts.py:8`), so "buy"/"checkout"/"pay" rely entirely on a model-assigned risk level.
  - No per-action check exists after page content is read.
  - Chromium runs with `--no-sandbox` (`browser/pool.py:92`) while visiting untrusted sites.
  - Typed text, including anything the user asks to enter, is persisted in clear in SQLite events and evidence records (`nodes.py:1005,1015,1208,1255`).

**Required fix:** Correct the text and Table III. Route vision through the router or say that it does not. Either use the recovery model or drop the claim. Use word-boundary or intent-level features. Fix the counter. Gate each executed action deterministically, as the desktop design already proposes. Enable the sandbox by default. Redact typed text.

---

## 4. Specific factual problems (sentence, location, evidence)

Numbers first, all of which I checked. Every number in Tables III (gate), IV (routing) and VI (tests), the 62.0 % coverage, 10,755/1,682 LOC, the 17 sanitizer patterns, the 12 CAPTCHA phrases, 11 graph nodes, the 5-minute timeout, the 3,500-token budget, the 300 s TTL constant and the category breakdown in Sec. VII-A all match `artifacts/results/*.csv`, `coverage.txt` and the code. The problems below are about wording and about what the code actually does.

### Abstract / Introduction
1. **"every evaluation is stored with before/after screenshots and a page snapshot"** (`00_abstract.tex:2`).
   - Φ evaluations are stored only as expected/observed JSON (`nodes.py:1450`).
   - Before/after screenshots exist per *executed action*, named by model-call count and overwritten on retry (`nodes.py:988,1172`).
   - A `complete` action gets a single `final_completion.png`, which is overwritten each attempt (`nodes.py:951`).
   - `dom_snapshot.json` is overwritten on every action (`evidence/manager.py:80-84`).
   - So a rejected evaluation has no retained page snapshot. Sec. V-B partially admits this, but the abstract should not claim it.
2. **"it may report a task complete only when a completion predicate evaluated on the live page holds"** (abstract; `01_introduction.tex:8`). This is true as a necessary condition. But see W2: for most goals the predicate is ¬β plus conjuncts satisfied by the planner's own text. It is not a check that "the environment satisfies the user's goal", which is how premature completion is defined in the introduction (`01_introduction.tex:6`).

### Sec. III Architecture
3. **"A pool of Playwright contexts over one headless Chromium"** (`03_architecture.tex:8`). The default is **headed**: `headless_browser: bool = False` (`backend/config.py:22`, used at `browser/pool.py:86-91`). The artifact log confirms that the default config fails without an X server (`04_results_raw.md:59`).
4. **"checkpoints the state after every node so that a paused or interrupted task can resume"** (`03_architecture.tex:6`), and **"a task resumed after a pause, an approval or a CAPTCHA re-enters the graph with its saved plan"** (`05_implementation.tex:6`).
   - Pause is an in-memory `asyncio.Event` and never re-enters the graph (`agent/runner.py:96-104,275-276`).
   - Nothing resumes an *interrupted* task (crash or restart). Checkpoints are loaded only when approval, CAPTCHA resume or fallback reschedules the same task (`runner.py:85,138,188,229`).
   - `approve()` also drops `session_id` when rescheduling (`runner.py:85`).
5. **"Model calls go through a router"** (`03_architecture.tex:8`) and Fig. 1 (router → Ollama for "text + vision"). Vision calls bypass the router (`vision/fallback.py:58-80,103-109`).
6. **The Observatory "only issues read queries and has no command channel to the agent."** Correct as far as I can see (`observatory/backend/storage.py` issues SELECT only). No issue; listed for completeness.

### Sec. IV-A/B Planning and grounding
7. **"three selectors (an identifier attribute …, a CSS selector and an XPath, tried in that order)"** (`04_methodology.tex:14`). This is a precedence, not a fallback chain. `_locator` returns the first non-empty field (`browser/executor.py:110-116`). Because `selector` is always set (`browser/dom.py:166`), CSS and XPath are never tried.
8. **"repeated navigation to the current site is suppressed"** (`04_methodology.tex:9`). It is replaced by `need_help` *after* the vision branch has already run (`nodes.py:817-829` vs `:733`). `verify` then fails the step, with "Agent needed assistance" going to recovery (`nodes.py:1375-1382`). So "suppression" means entering the failure and recovery path.
9. **"a request to enter literal text becomes a single text-entry step"** (`04_methodology.tex:7`). The detector is a permissive regex (`verification/manager.py:37-41`). My probe shows that "Search Google for the blood type of Alan Turing" yields the exact text `'of Alan Turing'` and "Search for Enter Sandman lyrics" yields `'Sandman lyrics'`. The whole plan is then replaced by "type that text" (`nodes.py:151-171`), and T requires it on the page. This hijacks ordinary tasks. It is not disclosed.
10. **"Identical screenshot–goal pairs are served from a cache."** The "goal" passed to the vision model is `intent.action` (e.g., "search"), not the user goal (`nodes.py:758`). The cache key is therefore screenshot + action + target, and the vision model never sees the user's actual request.

### Sec. IV-C Formal model vs `verification/manager.py` and `verify_node`
11. **"β(o)=1 when … a `chrome-error://` URL, an HTTP error title (404, 500, 502, 503), or a CAPTCHA/bot-check page"** (`04c_formal_model.tex:18`). The code differs in three ways:
    - Titles must contain the specific phrases "404 not found", "500 internal", "502 bad gateway" or "503 service" (`manager.py:209`). "Error 404", "404 – Page Not Found" and "Page not found · GitHub" are not detected.
    - Any URL containing the substring `err_` counts as a browser error (`manager.py:208`).
    - The in-Φ bot-block term applies only when `is_multistep` holds (`:210`). That `is_multistep` (`:206`) omits `requires_search`, unlike the one at `:228`, so the same function uses two definitions.
12. **"H is true when the goal requires search or extraction but o is still a search-engine home page"** (`04c_formal_model.tex:27`).
    - H also fires for *any* plan with more than one step (`manager.py:228`).
    - "Search-engine home page" means exactly four hosts, recognized by `rstrip('/')`/`endswith` (`:231`). `https://www.google.com/?hl=en`, `/webhp` and regional Google domains other than `.co.in` are not recognized.
    - "requires search" is triggered by the substrings "find", "look up" and "query" (`:226`).
13. **"T requires that any literal text requested in g appears in an input, textarea or contenteditable element of the live DOM"**.
    - Matching is by substring (`manager.py:253`), disclosed only later.
    - Only `[contenteditable="true"]` is checked, not `""` or `plaintext-only` (`:247`).
    - "Literal text requested in g" is the regex output from item 9, not a well-defined property of g.
14. **"X requires … an answer longer than 40 characters that is not a restated navigation instruction"**.
    - The "navigation" test is a prefix list that includes "search", "select" and "type" (`manager.py:271`). A correct answer such as "Search results confirm he was born in 1912." is rejected.
    - "Extraction goal" means the substrings extract/gather/collect/information about/page title (`:227`). "What is Turing's birth year?" triggers no X.
15. **"R requires that no plan step remains pending unless an answer has already been produced"**. This is correct as code (`manager.py:283-289`), but see W2: on the live path ŷ is always non-empty when the planner emits `complete` (`nodes.py:955,1448`; `parser.py:85`), so R is essentially dead code there. The formal model should state this.
16. **"The planner maps (g, o_t, 𝓜) … Φ(g,o,ŷ,P)"**, where o = Ω(s) = URL, title, manifest and screenshot. Φ does not use the manifest or the screenshot. It re-reads the live page's title and URL and runs `page.evaluate` over input values (`manager.py:195-196,245-252`). Φ is therefore a function of s_{t+1}, not of o_{t+1}. The four parameters `intent_action`, `intent_site`, `current_url` and `navigation_succeeded` are accepted but never used (`manager.py:176-179`).
17. **"The agent reports success iff Φ=1"** (`04c_formal_model.tex:29`). It is "only if". Φ=1 can still yield `waiting_approval` (`nodes.py:1499`) or be downgraded to FAILED by `complete_node` (`nodes.py:1595-1601`). The next sentence of the paper says this itself.
18. **"Φ … evaluated only when the planner emits complete, when the plan index reaches n, or when a requested text entry has been dispatched"**. This is correct, but the consequence is not stated. For one-step plans, which are the default for requests of eight words or fewer without connectives, Φ runs after *every* successful action with ŷ = that action's reasoning (`nodes.py:1431-1435,1448`). The gate is therefore also the termination rule, not only a check on the planner's `complete`.
19. **"α_t … is 1 when the browser call returned without an exception or a failed low-level check (e.g., reading back the value of a text field)"**. On any non-verification exception, `type_text` falls back to mouse-click-and-type and returns `success=True` without reading the value back (`browser/executor.py:56-79`). Vision-coordinate actions always return success (`nodes.py:1032`). The keyboard-type path without a target does too (`nodes.py:1089-1094`).
20. **"a budget of K=15 model calls (intent parsing, decomposition and planning)"**.
    - `parse_intent` counts 2 whenever `is_multistep`, even if decomposition failed (`nodes.py:247`).
    - Vision calls are not counted (`nodes.py:927`).
    - Each logical call can issue up to 4×4 physical Ollama requests (`llm/gateway.py:80,175`).
21. **"Only the shaded verify node can end a task as Completed"** (Fig. 2 caption). This holds for the compiled graph's routing. However, `complete_node` maps status `running` to `completed` (`nodes.py:1589-1591`), a latent bypass that the paper's safety argument depends on the routers never exercising. Please note this or remove the mapping.

### Sec. IV-D Recovery, routing and memory
22. **"retry → alternative_selector → vision_fallback → replan, one level per two attempts … after six attempts the task fails"** (`04_methodology.tex:23`). The retry counter is shared with `verify`'s three retries (`nodes.py:1369-1373`), so recovery usually starts at `retry_count = 3`, which is level 1. `replan` (level 3) requires `retry_count ≥ 6`, where the engine returns `exhausted` first (`recovery/engine.py:98-112,136`). The generic ladder never reaches `replan`. In addition, verify's `need_help` error text ("Agent needed assistance…") matches no `vision_needed` pattern (`engine.py:39`) and is classified `unknown`.
23. **"recovery calls to a recovery model"** (`04_methodology.tex:28`) and Table IV row "Recovery (recovery) → qwen2.5:7b". The recovery model is selected (`nodes.py:1529`) but never invoked, because `RecoveryEngine.handle_failure` makes no LLM call (`recovery/engine.py:114-200`). Its selection is written to `selected_model` (`nodes.py:1549`), and later `plan_action` calls stick to it (`nodes.py:624`, `router.py:121-135`). I confirmed this with a probe: after a recovery route, the next planner route returns `qwen2.5:7b` with reason "retained (stickiness)".
24. **"image inputs or screen-related wording to a vision model"** and Table IV row "Image input (vision) → moondream / qwen3-vl:2b". No live call routes with `has_image=True` (grep: `route(` only at `nodes.py:78,122,619,1529`; the row comes from the synthetic call at `artifacts/experiments/routing_default_install.py:30`). The live vision model comes from `vision/fallback.py:65`. Conversely, "screen-related wording" is substring matching (`analyzer.py:28-31,115`). With the default install my probe routes *text* intent parsing for "Find a guitar guide on youtube.com" ("gui"), "Search Google Images for cats" ("image") and "Open the screening schedule on imdb.com" ("screen") to **moondream**.
25. **"With the launcher's default installation, every text call resolves to qwen2.5:1.5b"** (`07_results.tex:16`). This holds only for the six probe inputs. It is false in general, per item 24 (vision keywords reach moondream). The coder role reaches the fallback only because qwen2.5-coder is not installed.
26. **"only recovery, which is exempt, and image inputs switch"** (`07_results.tex:16`). Two problems:
    - The recovery switch persists into later planning (item 23), so it is not a one-off exemption.
    - Stickiness is also cross-task, because `model_router` is a process-global singleton whose `_last_selected_model` is used when `active_model` is `None` (`router.py:121`). The "isolated" column therefore describes a fresh process only.
27. **"the list is refreshed every 300 s"** (`04_methodology.tex:28`). The TTL applies to `probe_installed`, which is called only at startup (`agent/runner.py:44`, `main.py:62`). In practice the cache is refreshed on *every* task, because `parse_intent` calls `check_vision_availability` → `list_model_names` → `mark_installed` (`nodes.py:191`, `vision/fallback.py:62`, `llm/gateway.py:60`).
28. **"a builder deduplicates the results and fits them into a 3,500-token budget inside an untrusted-content banner"** (`04_methodology.tex:34`). The untrusted banner wraps only *knowledge* chunks (`rag/context_builder.py:139`, `rag/security.py:11`). Memories are emitted under "=== PAST EXECUTION EXPERIENCE ===" with no untrusted marking or sanitization (`context_builder.py:120-123`), although they contain page-derived URLs and error strings.
29. **"memory is written but not read"** is correct (`runner.py:265-266`; `rag/router.py:67`). The paper omits two things:
    - Knowledge-RAG retrieval is equally bypassed by the same condition. Sec. VIII's mitigation "retrieved knowledge is filtered the same way and marked untrusted" (`08_security.tex:6`) therefore never runs on the live path.
    - A second memory write path exists: `summarize_task` in the runner (`runner.py:315`). The `complete_node` memory write also crashes when `parse_intent` failed (`intent.target` on `None`, `nodes.py:1633`; seen in `pytest_output.txt:81`).

### Sec. V Implementation / Evidence
30. **"append-only verification and recovery records"** (`05_implementation.tex:8`). The file is read, appended in memory and rewritten with `"w"`. A `JSONDecodeError` silently resets the list to `[]`, discarding all earlier records (`evidence/manager.py:91-102`). Action results, Φ results and recovery records are mixed in one file (`nodes.py:1450,1565` and the action-result write in `execute_action_node`).
31. **"Of the four failures, two need Ollama, one times out waiting on a browser page and one needs scripts missing from the repository"** (`07_results.tex:22`). `test_launcher.py::test_different_working_directory` fails because the git-ignored directory `scratch/` is missing as a *cwd* (`tests/test_launcher.py:87-95`; `pytest_output.txt:420`). It runs `main.py --help` and needs no scripts. The timed-out test is the core-property test `test_action_failure_never_marks_completed` (W1), which should be named.
32. **"no test runs the compiled graph"** (`07_results.tex:22`) and Table V "compiled graph not tested". `tests/e2e/test_runner.py` and `test_certification.py` run `TaskRunner._run` → `build_graph()` → `graph.astream` (`agent/runner.py:216-274`), and the certification log shows the graph running parse_intent → recovery → complete (`pytest_output.txt:22,80-81`). What is true is that only failure paths execute, because no LLM responds. Please rephrase.

### Sec. VII-A Gate study
33. **"The gate under test is the agent's own code: the verify node's CAPTCHA pre-check followed by verify_task_completion"** (`06_experimental_setup.tex:10`). The harness re-implements part of `verify_node` (`artifacts/experiments/verification_gate_study.py:148-157`). It passes `final_answer=case.final_answer` instead of `state.final_answer or action.reasoning` (`nodes.py:1448`). It also skips the step-progression logic (`:1393-1426`), the trigger condition (`:1431-1435`), the `manifest.page_state=="captcha"` term (`:1337`), the approval rewrite (`:1499`) and the `complete_node` downgrade. As argued in W2, X2 and P1 would very likely be accepted by the live node.
34. **"… three incomplete extraction answers including one produced while still on the search home page"** (`07_results.tex:6`). X7's answer is complete and correct ("born on 23 June 1912"; `verification_gate_study.py:133-134`). It is ungrounded, not incomplete. X2 has *no* answer. Please describe them accurately.
35. **"A ``page not found'' message without a status code in the title and a redirect to a login page pass (N6, N7); the DOM extractor classifies such pages"** (`07_results.tex:10`). This is false for N6. I ran `DOMExtractor._detect_page_state` on the N6 fixture and it returns **`ready`**: the body text "could not find that page" contains none of "404/500/not found/server error" (`browser/dom.py:111`). Only N7 is classified (`login_required`).
36. **"Every gap maps to a check that needs no model call (… reuse of the page-state classifier …)"**. The classifier labels any page whose body contains "sign in", "log in" or "password" as `login_required`, and any page containing "404" or "500" as `error` (`browser/dom.py:109-111`). Real google.com, Wikipedia (which has a "Log in" link) and a "Fortune 500" page (my probe) would all be rejected. Reusing the classifier as a Φ conjunct would introduce many false rejections. The claim needs a measurement, not an assertion.
37. **"the median time for one full decision (CAPTCHA pre-check plus Φ) over 20 repetitions per case was 33.8 ms"** (`07_results.tex:12`). 33.78 ms is the median over all 35 per-case medians, *including* the three BLOCKED cases that never evaluate Φ (C1 = 0.0 ms). Over the 32 full decisions the median is 33.99 ms (`verification_gate_cases.csv`). The difference is small, but the label is wrong.
38. **"decisions that stop at the URL-based CAPTCHA check took under 8 ms"**. Only C1 stops at the URL check (0.0 ms). C2 (5.77 ms) and C3 (7.06 ms) stop at the body-text phrase check (`verification_gate_cases.csv`; `browser/dom.py:31-48`).

### Sec. VIII Security
39. **"The risk level that triggers approval comes from the same model that reads untrusted content"** (`08_security.tex:8`). The intent model reads only the user's task text, before any navigation (`nodes.py:94-99`), so page content cannot influence it. The real gaps are elsewhere:
    - *Both* the triggering `action` label and the risk level are free-text model outputs (`parser.py:15,19`).
    - The approval set contains labels the intent prompt never offers (`approval.py:14` vs `prompts.py:8`).
    - No executed action is ever re-assessed after page content is read.
40. **"the check is repeated when completion is verified"** (`08_security.tex:6`). The repeated check applies the same function to the same intent (`nodes.py:1499`), so it cannot trigger unless `risk_check` already did. It adds no protection.
41. **"… and it types queries instead of loading result URLs"** (`08_security.tex:10`). The CAPTCHA fallback loads result URLs directly (`https://html.duckduckgo.com/html/?q=…` or `bing.com/search?q=…`, `agent/runner.py:155-158,176`).
42. **"Every model call is logged with destination, a locality flag …"**. The flag is computed by substring (`"127.0.0.1" in destination or "localhost" in destination`, `security/audit.py:68`). It is true for `http://localhost.attacker.example` and false for `http://[::1]:11434`.
43. **"The service listens on loopback and accepts only localhost origins"**. CORS is not access control. The API has no authentication and no Host-header check, so it is open to any local process and to DNS-rebinding from the agent's own browser. Please qualify the claim.
44. **"outbound traffic in the default configuration consists of the browser's requests …"** (`03_architecture.tex:12`). This holds for the tested `chromadb==1.5.9`, whose PostHog client is a no-op. `backend/requirements.txt:8` allows `chromadb>=0.5.0`, where anonymized telemetry is enabled by default, and the code never sets `anonymized_telemetry=False`. Pin the version or disable telemetry.

### Tables
45. **Table I "Gate" column.** WebArena, OSWorld and WebVoyager are marked **P**, and AgentDojo **P**, yet the column is defined as "completion gated at run time by an in-agent environment check". Sec. II-B states that their checks "belong to the benchmark and run after the episode ends". By the paper's own definition these cells are **N**. Given W2, the paper's own "Y" row deserves at most "P".
46. **Table V "Failure classes, retry bounds … 6 attempts"**. Effectively 3 recovery attempts after verify's 3 retries (item 22).
47. **Table IV label "1-step act. (light.)"**. Only single-step *navigation* actions route to the lightweight role. A single-step search (`task_type="search"`, complexity "medium") routes to **general** (`analyzer.py:153-157,182`). The row reflects the synthetic `action_type="navigate"` probe (`routing_default_install.py:27`).
48. **Table VI "RAG and memory (8)"**. None of those eight files tests `memory/provider.py`; they are RAG tests (`tests_by_file.csv`).

---

## 5. Minor issues

- **Length.** The PDF is 10 pages (`main.log:1014`). Most IEEE conferences allow 6–8 pages including references. The desktop design (Sec. IV-E, Table II) takes about a column and a half for something that does not exist and should be shortened or moved to future work.
- **Fig. 1.** The "risk gate" box sits inside the per-step loop next to "plan + sanitize", which suggests per-action gating. It is a once-per-task, pre-navigation check. The router → Ollama "text + vision" edge contradicts the vision path. The arrow to Chroma correctly shows write-only, but the caption should say so.
- **Fig. 2.** `auth_check` is a no-op pass-through (`nodes.py:284-288`) and should be marked as such or dropped. The `navigate → complete (blocked)` edge exists in code but is unreachable, because `navigate_node` never sets `blocked`.
- **Property in Eq. (2).** α ⇏ Φ is a non-implication shown by one counterexample. Calling it a "Property" overstates the formalization. Either state and prove something (e.g., soundness of Φ with respect to Φ* on a defined goal class) or drop the word.
- **FCR.** FCR is a precision-type metric and can be driven to 0 by never completing. Always report it with task success and false-rejection rate, and say so in Sec. IV-C, not only in VI.
- **Sec. IV-A.** "a connective ('and', 'then', a comma)". The code also uses "after", "followed by" and ";" (`nodes.py:119`).
- **Sec. IV-B.** "stripped of cookie and advertising labels". The filter also removes "sponsored", and it runs *after* deduplication and link capping (`dom.py:186-204`), so a removed element can consume a link slot.
- **Sec. V.** "a per-action execution record … and the node trace". `trace.json` is also rewritten on every node (`evidence/manager.py:61-76`), with the same corruption risk as item 30.
- **Sec. VI.** "Both study scripts are in the repository under artifacts/experiments/". They are not in commit `2361d50`, the commit the environment paragraph cites. Give the commit that contains the scripts too.
- **Sec. VI (iv).** "Vision-only grounding: the DOM manifest withheld … a small change". Φ, the text-entry grounding and the Google rule all read the DOM, so this configuration also changes the gate and the deterministic rules. Please specify it.
- **DOM mutation.** The DOM extractor writes `data-pilot-id` attributes into the live page (`dom.py:153`). This is observable by sites and mutates the state Φ reads. It should be mentioned alongside the anti-detection measures.
- **Ethics.** Spoofing a Windows Chrome 124 UA on Chromium 141 and hiding `navigator.webdriver` (`pool.py:127,138`) warrant a clearer ethics statement than "deployments should respect site terms".
- **LaTeX comment.** `04c_formal_model.tex:2` references `07_claims_ledger.md`, a file that appeared only late in `artifacts/`. Keep internal pointers out of the source, or make sure they resolve in the released artifact.
- **LaTeX warnings.** About 30 underfull hbox warnings, mostly in the narrow table `p{}` columns (`main.log:807-962`). Consider `\raggedright` in those columns.
- **Related work gaps.**
  - Agent memory: Agent Workflow Memory, Synapse, Agent S.
  - In-loop verification: Pan et al. 2024 "Autonomous Evaluation and Refinement of Digital Agents", Magentic-One.
  - Local/open agents: Browser Use, OpenAdapt, UI-TARS.
  - Injection defenses: spotlighting, CaMeL, Progent/privilege control. These bear directly on the desktop tier design and the "none of these ties a stored memory to verified evidence" claim.
- **AI-assistance acknowledgment.** It is fine, but check the venue's disclosure policy. Some IEEE venues require this in a specific section.

---

## 6. Questions to the authors

1. If Φ is evaluated inside the real `verify_node` (with `planned_action.reasoning` populated as the planner would), how many of the 15 "prevented" completions remain, and in particular X2 and P1?
2. On the 30-task suite, what fraction of tasks instantiate *no* conjunct beyond ¬β? For those, how does Φ differ from dispatch-only?
3. Was any number in the repository's prior certification or README produced with the SRM-specific extraction code active? Will the E2E study be run after its removal?
4. What is the false-BLOCKED rate of `detect_captcha` on ordinary pages? Pages with invisible reCAPTCHA v3 badges are common on retail and login pages, and titles containing "robot" also trigger it.
5. Why is planner `reasoning` used as the task answer at all? Would a dedicated `answer` field plus answer-to-goal term overlap (your proposed fix) survive a verbose 1.5B planner?
6. How do you prevent the exact-text regex from hijacking ordinary queries ("blood type of …", "Enter Sandman")? Will such goals be in the task suite?
7. The recovery model is routed but never invoked. Was a recovery LLM call removed, or never implemented? Should Table IV keep that row?
8. For the E2E protocol, how will you control cross-task router stickiness (process-global `_last_selected_model`)? Will you restart the backend per trial?
9. Why is `--no-sandbox` the default for an agent that by design browses untrusted pages? Is there a platform that requires it?
10. Which concrete conditions would the proposed `action_gate` apply to *browser* actions, for example clicking a "Buy" button when the intent was "search"? Could it be implemented for the browser before the desktop?
11. What prevents a page the agent visits from issuing requests to `http://127.0.0.1:8765` (DNS rebinding or simple requests), given the absence of API authentication?
12. Will the 35 fixtures be extended with satisfied cases for the CAPTCHA/β category and with labels by annotators who have not seen Φ?

---

*Probes run for this review (not part of the paper):*
- The router on keyword inputs.
- `extract_exact_text_to_type` on everyday goals.
- `_detect_page_state`/`detect_captcha` on the N6, N7 and N1 fixtures plus three extra pages ("Robot – Wikipedia", "Fortune 500", hidden reCAPTCHA iframe).
- A LangGraph check that undeclared state keys are dropped.

All used `.venv-eval` and the paper's harness approach. No repository files were modified.

---

## 7. Lead Editor's response (how each point was handled)

**Every numeric claim was re-checked, and every code claim below was verified first-hand before the paper was changed.**

### Top weaknesses

| # | Response | Where |
|---|---|---|
| W1 | **Accepted; cannot be fixed in this environment.** There is no Ollama or live web here. End-to-end results remain a visible `\todo{MEASURE}`. The timed-out core-property test is now **named** in §VII-C. The paper no longer calls any passing test evidence of task success. | §VII-C/D, README §3 |
| W2 | **Accepted and measured.** The gate study now also runs the **real `verify_node`** (database, browser-pool and evidence I/O stubbed; plan and action state set as the graph leaves them) with empty and with verbose planner `reasoning`. Result: the live gate withholds **14 / 13** of 23 unsatisfied states, versus 15 for the component. P1 is lost in both live variants and X2 with verbose reasoning, as predicted. The formal model now states that ŷ falls back to the planner's reasoning, that Φ runs after every successful action for one-step plans, and that Φ reduces to ¬E when no keyword fires. | `verification_gate_study.py`, Table IV, §IV-C, §VII-A, abstract |
| W3 | **Partly accepted.** Added three controls: satisfied bot-check look-alikes C5 (Wikipedia "Robot") and C6 (hidden invisible-reCAPTCHA iframe), and a no-keyword negative N8. The measured result is that **both C5 and C6 are falsely blocked**, and N8 is falsely accepted. The latency label now reads "33 decisions that evaluate Φ, median 35.2 ms", with pre-check stops ≤ 8.2 ms; small pages are acknowledged. Real recorded end states, blind labelling and a VLM-judge baseline are **not done** and are left to the author (README §4). | Table IV, §VI-A, §VII-A |
| W4 | **Accepted.** §V now states that the extraction handler formats every answer as campus facts and substitutes fixed text, so it can fabricate an answer that satisfies X. §IX lists the site/case-specific rules (the Google rule, the `"srm"` click fallback, the substring step→action rules), and a `\todo` requires removal and disclosure. | §V, §IX |
| W5 | **Accepted; all verified.** Routing: substring keyword matching (probe: "guitar guide", "Google Images" and "screening" → moondream, now in `routing_resolution.csv`); the recovery model routed but unused, then sticky (probe added); cross-task stickiness; the vision fallback bypasses the router. Recovery: the shared counter makes `replan` reachable only through shortcuts. Security: the risk label comes from the task text only (the original sentence was **wrong** and has been removed); approval is once per task and not per action; no authentication; typed text stored in clear; `--no-sandbox`. | §IV-D/E, §VII-B, §VIII, Table III |

### Factual items (numbering follows §4 above)

| Items | Disposition |
|---|---|
| 1 | Abstract changed to "evaluations are logged next to per-action before/after screenshots". §V states that a rejected Φ keeps no snapshot of its own. |
| 2 | §IV-C and §VII-A now state the live weakness explicitly. |
| 3 | Headed default stated (§III). |
| 4 | Resume semantics corrected in §III and §V: re-scheduling after approval or CAPTCHA only; no crash recovery. |
| 5 | "Text-model calls go through a router"; Fig. 1 router labelled "(text)". |
| 7 | Selector "fallback" corrected to precedence. |
| 8 | "Suppressed" corrected: the repeated navigation becomes a failure that enters recovery. |
| 9 | The permissive exact-text pattern and its misfires are disclosed in §IV-A. |
| 10 | Vision input and cache key corrected (action verb and target, not the full request). |
| 11–14, 16–20 | Formal model rewritten: E limited to four title phrases, H definition, T substring match, X prefix list, Φ evaluated on s_{t+1}, "only if", α fallback paths, K counter wording, "Property" changed to "Consequence". |
| 15 | R weakness stated. |
| 21 | Not changed in the text. The `running`→`completed` mapping in `complete_node` is unreachable through the compiled routers. This is noted here for the author as a latent risk (README §4). |
| 22 | Ladder reachability stated. |
| 23–27 | Routing corrections applied. The "refreshed every 300 s" claim is replaced with "refreshed at the start of each task"; the Lead Editor verified this via `check_vision_availability` → `list_model_names` → `mark_installed`. |
| 28–29 | Memory has no untrusted banner; knowledge retrieval is also inert. The §VIII claim "retrieved knowledge is filtered" was removed. |
| 30 | "append-only" changed to "rewritten on each update, reset on parse error". |
| 31–32 | Launcher failure corrected to "a directory absent"; the compiled graph is run only by the e2e tests, through failure paths. |
| 33 | The component harness is kept, the live-node harness added, and both reported. |
| 34 | X7 described as "ungrounded". |
| 35 | The false N6 statement about the page-state classifier was removed. |
| 36 | The "reuse the page-state classifier" suggestion was removed. |
| 37–38 | Latency labels corrected (see W3). |
| 39–44 | §VIII rewritten. The telemetry caveat for older chromadb versions was added to §III, and the ledger asks the author to confirm it. |
| 45 | Table I Gate cells for WebArena, WebVoyager, OSWorld and AgentDojo changed to N. Our own cell changed to P. |
| 46 | Table III now reads "3+3 attempts". |
| 47 | Row label "1-step navigate". The routing table was later folded into text for space. |
| 48 | "RAG (8)". The tests table was later folded into text for space. |

### Minor items

**Addressed:**
- page length: 9 pages total; the body ends just past page 8;
- the Fig. 1 risk gate is marked "(once)";
- Fig. 2 marks auth as a no-op;
- the FCR precision caveat moved into §IV-C;
- the connective list is complete;
- the DOM `data-pilot-id` stamping is disclosed in §VIII;
- the internal pointer was removed from the LaTeX comment.

**Not addressed (left to the author, README):**
- the underfull hbox warnings in narrow table columns (cosmetic);
- additional related work (Agent Workflow Memory, Synapse, Agent S, Pan et al., Magentic-One, Browser Use, OpenAdapt, UI-TARS, spotlighting, CaMeL, Progent). None was verified in this session, and the integrity rules forbid unverified citations.

### Questions

- **Q1:** answered by measurement. 14/15 survive with empty reasoning and 13/15 with verbose reasoning; P1 is lost in both, X2 only with verbose reasoning.
- **Q2 and Q3:** require end-to-end runs and the author's history, and are flagged in the README.

**Final verdict after revision (Lead Editor's view):** the paper is now accurate about what it shows. Its evidence is still component-level, so a venue would likely still reject it until the end-to-end protocol has been run.


---

## 8. Follow-up: code fixes (commit `5359458`)

After the review, the author asked for the fixable items to be fixed in code rather than only disclosed.

**Addressed in code:**
- **W4:** the case-specific extraction and click code was removed.
- **W2:** reasoning is no longer accepted as an answer, and `complete` no longer marks a step done.
- **Gate gaps:** query check, error and login titles, exact matching, goal-term overlap, and a stricter R.
- **CAPTCHA false positives:** title wording made specific; hidden and invisible frames ignored.
- **Regex:** the exact-text pattern no longer hijacks ordinary requests.
- **Routing (W5):** whole-word keywords; stickiness is task-local; recovery is not routed.
- **Inert mechanisms:** the verification flag, memory retrieval and `vision_fallback` now take effect.
- **Evaluation:** the eval runner and `--eval` now run the presets.
- **Tests:** all test defects fixed.

**Effect on the evidence:**
- Design set: 20 of 23 unsatisfied states caught, 1 of 15 satisfied states rejected, identical across modes.
- New held-out set (12 states, written after the fixes): 2 of 5 unsatisfied states caught, versus 1 of 5 before.

The paper reports both sets and calls the design-set gain optimistic by construction.

**Still open:**
- W1: no end-to-end evidence.
- W3: author-written fixtures and no model-judge baseline.
- Per-action approval and per-step predicates.
- The `alternative_selector` and `replan` strategies.
