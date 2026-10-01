"""Controlled study of Agentic Pilot's completion gate on constructed page fixtures.

What this measures
------------------
The agent decides "task complete" in verify_node (backend/agent/nodes.py) by
(1) a CAPTCHA pre-check (backend.browser.dom.detect_captcha, plus a '/sorry/'
URL test) and (2) VerificationManager.verify_task_completion
(backend/verification/manager.py). Hand-built end states with a known true
outcome are judged by four rules:

  dispatch_only  report success whenever the last action dispatched
  component      CAPTCHA pre-check + verify_task_completion, called directly
                 with the case's answer (isolates the predicate)
  live_empty     the real verify_node, with I/O stubbed, the terminal action and
                 plan state set as the graph would leave them, and an empty
                 planner `reasoning` string
  live_verbose   as live_empty, but with a generic one-sentence `reasoning`
                 string. At commit 2361d50 verify_node fell back to the last
                 action's reasoning as the answer; this shows how much of the
                 gate survives a talkative planner.

Run it against any checkout: results go to <checkout>/artifacts/results/.

What it does NOT measure
------------------------
No LLM is involved and no live website is contacted: pages are served offline
through Playwright request interception. The fixtures and their oracle labels
were written by the study authors and are not a sample of real task outcomes,
so the rates below describe the gate's behaviour on these cases only. They are
not end-to-end task success rates.

Usage:  python artifacts/experiments/verification_gate_study.py [--reps N]
Outputs: artifacts/results/verification_gate_cases.csv
         artifacts/results/verification_gate_summary.csv
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import platform
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from playwright.async_api import async_playwright  # noqa: E402

from backend.browser.dom import detect_captcha  # noqa: E402
from backend.llm.parser import TaskPlan, TaskStep  # noqa: E402
from backend.verification.manager import VerificationManager  # noqa: E402

OUT = REPO / "artifacts" / "results"


def page(title: str, body: str) -> str:
    return f"<!doctype html><html><head><title>{title}</title></head><body>{body}</body></html>"


GOOGLE_HOME = page("Google", '<form action="/search"><textarea name="q" title="Search"></textarea><input type="submit" value="Google Search"></form>')
BING_HOME = page("Bing", '<form><input type="search" name="q"></form>')
DDG_HOME = page("DuckDuckGo - Protecting your privacy", '<form><input type="text" name="q"></form>')


def results(q: str) -> str:
    return page(f"{q} - Search", f"<div id='search'><h3>{q}</h3><p>About {q} ... result snippet</p><a href='#'>{q} - Wikipedia</a></div>")


TURING = page("Alan Turing - Wikipedia", "<h1>Alan Turing</h1><p>Alan Mathison Turing (23 June 1912 - 7 June 1954) was an English mathematician and computer scientist.</p>")


def plan(*steps: tuple[str, str]) -> TaskPlan:
    return TaskPlan(
        task_summary="fixture plan",
        total_steps=len(steps),
        steps=[TaskStep(step_index=i + 1, description=f"{a} step", action_type=a, status=s) for i, (a, s) in enumerate(steps)],
    )


@dataclass
class Case:
    cid: str
    category: str
    goal: str
    url: str
    html: str
    oracle: bool  # experimenter's independent judgement: is the goal actually satisfied?
    rationale: str
    final_answer: str | None = None
    extracted: dict = field(default_factory=dict)
    task_plan: TaskPlan | None = None
    last_action: str = "complete"  # planner action that preceded verification
    held_out: bool = False


SEARCH_GOAL = "Search Google for 'Alan Turing'"
EXTRACT_GOAL = "Go to wikipedia.org, search for 'Alan Turing' and extract his birth year"
TYPE_GOAL = "Go to https://notes.example.com and enter exactly: 'Meeting at 10am'"
GH_GOAL = "Go to github.com, then open the Explore page"

CASES: list[Case] = [
    # S: search goal, browser still on a search-engine home page (premature completion)
    Case("S1", "search", SEARCH_GOAL, "https://www.google.com/", GOOGLE_HOME, False, "home page, no query issued"),
    Case("S2", "search", "Search Bing for 'Alan Turing'", "https://www.bing.com/", BING_HOME, False, "home page, no query issued"),
    Case("S3", "search", "Search DuckDuckGo for 'Alan Turing'", "https://duckduckgo.com/", DDG_HOME, False, "home page, no query issued"),
    Case("S4", "search", SEARCH_GOAL, "https://www.google.com/search?q=Alan+Turing", results("Alan Turing"), True, "results for requested query"),
    Case("S5", "search", "Search DuckDuckGo for 'Alan Turing'", "https://duckduckgo.com/?q=Alan+Turing", results("Alan Turing"), True, "results for requested query"),
    Case("S6", "search", "Search Bing for 'Alan Turing'", "https://www.bing.com/search?q=Alan+Turing", results("Alan Turing"), True, "results for requested query"),
    Case("S7", "search", SEARCH_GOAL, "https://www.google.com/search?q=Grace+Hopper", results("Grace Hopper"), False, "results page for a different query"),
    # N: plain navigation goals
    Case("N1", "navigation", "Open google.com", "https://www.google.com/", GOOGLE_HOME, True, "requested page is open"),
    Case("N2", "navigation", "Go to example.com", "https://example.com/", page("Example Domain", "<h1>Example Domain</h1>"), True, "requested page is open"),
    Case("N3", "navigation", "Go to https://example.com/docs", "https://example.com/docs", page("404 Not Found", "<h1>Not Found</h1>"), False, "HTTP 404"),
    Case("N4", "navigation", "Go to https://example.com/api", "https://example.com/api", page("502 Bad Gateway", "<h1>502</h1>"), False, "HTTP 502"),
    Case("N5", "navigation", "Go to https://example.com/status", "https://example.com/status", page("503 Service Unavailable", "<h1>503</h1>"), False, "HTTP 503"),
    Case("N6", "navigation", "Go to https://example.com/pricing", "https://example.com/pricing", page("Page not found | Example", "<h1>Sorry, we could not find that page.</h1>"), False, "soft 404 without status code in title"),
    Case("N7", "navigation", "Go to https://github.com/explore", "https://github.com/login?return_to=%2Fexplore", page("Sign in to GitHub", "<form><input name='login'></form>"), False, "redirected to a login wall"),
    # C: CAPTCHA / bot-check end states (goal must NOT be reported complete)
    Case("C1", "captcha", SEARCH_GOAL, "https://www.google.com/sorry/index?continue=x", page("https://www.google.com/search", "<p>Our systems have detected unusual traffic from your computer network.</p>"), False, "Google bot challenge"),
    Case("C2", "captcha", "Go to https://shop.example.com/checkout", "https://shop.example.com/checkout", page("Checkout", "<iframe src='https://www.google.com/recaptcha/api2/anchor'></iframe><p>I'm not a robot</p>"), False, "reCAPTCHA widget"),
    Case("C3", "captcha", "Go to https://news.example.com", "https://news.example.com/", page("Just a moment...", "<p>Verify you are human by completing the action below.</p>"), False, "interstitial human check"),
    Case("C4", "captcha", "Go to https://forum.example.com", "https://forum.example.com/", page("Just a moment...", "<p>Checking your browser before accessing forum.example.com.</p>"), False, "interstitial with no known phrase"),
    # T: exact text entry
    Case("T1", "text_entry", TYPE_GOAL, "https://notes.example.com/", page("Notes", "<textarea>Meeting at 10am</textarea>"), True, "exact text present"),
    Case("T2", "text_entry", TYPE_GOAL, "https://notes.example.com/", page("Notes", "<textarea></textarea>"), False, "field empty"),
    Case("T3", "text_entry", TYPE_GOAL, "https://notes.example.com/", page("Notes", "<textarea>Meeting at 11am</textarea>"), False, "wrong text"),
    Case("T4", "text_entry", TYPE_GOAL, "https://notes.example.com/", page("Notes", "<textarea>Meeting at 10am tomorrow</textarea>"), False, "text has extra suffix, not exact"),
    Case("T5", "text_entry", TYPE_GOAL, "https://notes.example.com/", page("Notes", "<div contenteditable='true'>Meeting at 10am</div>"), True, "exact text in contenteditable"),
    Case("T6", "text_entry", TYPE_GOAL, "https://notes.example.com/", page("Notes", "<input type='text' value='Meeting at 10am'>"), True, "exact text in input"),
    # X: extraction goals (answer must contain the birth year 1912)
    Case("X1", "extraction", EXTRACT_GOAL, "https://en.wikipedia.org/wiki/Alan_Turing", TURING, True, "answer states 1912",
         final_answer="Alan Turing was born on 23 June 1912 in Maida Vale, London, per the article."),
    Case("X2", "extraction", EXTRACT_GOAL, "https://en.wikipedia.org/wiki/Alan_Turing", TURING, False, "no answer produced"),
    Case("X3", "extraction", EXTRACT_GOAL, "https://en.wikipedia.org/wiki/Alan_Turing", TURING, False, "answer restates a navigation step",
         final_answer="Navigating to the Alan Turing article on Wikipedia to find the birth year."),
    Case("X4", "extraction", EXTRACT_GOAL, "https://en.wikipedia.org/wiki/Alan_Turing", TURING, False, "long answer lacking the year",
         final_answer="The article describes an English mathematician and computer scientist regarded as a founder of the field."),
    Case("X5", "extraction", EXTRACT_GOAL, "https://en.wikipedia.org/wiki/Alan_Turing", TURING, True, "structured extraction contains 1912",
         extracted={"Alan Turing - Wikipedia": {"content_snippet": "Alan Mathison Turing (23 June 1912 - 7 June 1954)"}}),
    Case("X6", "extraction", EXTRACT_GOAL, "https://en.wikipedia.org/wiki/Alan_Turing", TURING, True, "short but correct answer",
         final_answer="Born in 1912."),
    Case("X7", "extraction", EXTRACT_GOAL, "https://www.google.com/", GOOGLE_HOME, False, "never left the search home page",
         final_answer="Alan Turing was born on 23 June 1912 in Maida Vale, London, per the article."),
    # P: multi-step plans
    Case("P1", "multi_step", GH_GOAL, "https://github.com/", page("GitHub", "<a href='/explore'>Explore</a>"), False, "second step pending",
         task_plan=plan(("navigate", "completed"), ("click", "pending"))),
    Case("P2", "multi_step", GH_GOAL, "https://github.com/explore", page("Explore GitHub", "<h1>Explore</h1>"), True, "both steps done",
         task_plan=plan(("navigate", "completed"), ("click", "completed"))),
    Case("P3", "multi_step", GH_GOAL, "https://github.com/", page("GitHub", "<a href='/explore'>Explore</a>"), False,
         "click dispatched on the wrong element; step marked completed on dispatch",
         task_plan=plan(("navigate", "completed"), ("click", "completed"))),
    Case("P4", "multi_step", "Go to wikipedia.org, then open the Alan Turing article", "https://en.wikipedia.org/wiki/Alan_Turing", TURING, True, "both steps done",
         task_plan=plan(("navigate", "completed"), ("click", "completed"))),
    # Controls added after review: satisfied states that look like bot checks, and a goal
    # that triggers none of the keyword-activated conjuncts.
    Case("C5", "captcha", "Open the Wikipedia article on Robot", "https://en.wikipedia.org/wiki/Robot",
         page("Robot - Wikipedia", "<h1>Robot</h1><p>A robot is a machine capable of carrying out actions automatically.</p>"),
         True, "ordinary article whose title contains 'robot'"),
    Case("C6", "captcha", "Go to https://accounts.example.com/login", "https://accounts.example.com/login",
         page("Sign in - Example", "<form><input name='user'><input type='password'></form>"
              "<iframe src='https://www.google.com/recaptcha/api2/anchor?size=invisible' style='display:none'></iframe>"),
         True, "login page with an invisible reCAPTCHA iframe, no challenge shown"),
    Case("N8", "navigation", "Open the pricing page on example.com", "https://example.com/",
         page("Example Domain", "<h1>Example Domain</h1><a href='/pricing'>Pricing</a>"),
         False, "still on the home page; goal wording triggers no conjunct"),
]

# Held-out cases, written after the gate fixes and not used to design them. Several target the new
# rules' blind spots (unquoted queries, error titles without "not found", term overlap with a wrong fact).
PARIS = page("Paris - Wikipedia", "<h1>Paris</h1><p>Paris had an estimated population of 2,102,650 residents in January 2023.</p>")
HELDOUT: list[Case] = [
    Case("H1", "search", "Search Google for Ada Lovelace", "https://www.google.com/search?q=Charles+Babbage",
         results("Charles Babbage"), False, "results for another, unquoted query"),
    Case("H2", "search", "Search Bing for 'quantum computing'", "https://www.bing.com/search?q=quantum+computing",
         results("quantum computing"), True, "results for requested query"),
    Case("H3", "navigation", "Go to https://example.com/archive", "https://example.com/archive",
         page("Error 404", "<h1>Error 404</h1>"), False, "error title without 'not found'"),
    Case("H4", "navigation", "Go to https://github.com/acme/missing", "https://github.com/acme/missing",
         page("Page not found \u00b7 GitHub", "<h1>404</h1>"), False, "GitHub 404 page"),
    Case("H5", "navigation", "Go to https://docs.example.com/guide", "https://docs.example.com/guide",
         page("Guide - Example Docs", "<h1>Guide</h1>"), True, "requested page is open"),
    Case("H6", "captcha", "Go to https://store.example.com", "https://store.example.com/",
         page("Attention Required", "<p>Please complete the security check to access store.example.com</p>"), False, "security-check interstitial"),
    Case("H7", "captcha", "Open the Wikipedia article on CAPTCHA", "https://en.wikipedia.org/wiki/CAPTCHA",
         page("CAPTCHA - Wikipedia", "<h1>CAPTCHA</h1><p>A CAPTCHA is a type of challenge-response test.</p>"), True, "article about CAPTCHAs"),
    Case("H8", "text_entry", "Open https://notes.example.com and type hello world into the box", "https://notes.example.com/",
         page("Notes", "<textarea>hello world</textarea>"), True, "requested text present"),
    Case("H9", "text_entry", "Go to https://notes.example.com and enter exactly: 'Room 4B'", "https://notes.example.com/",
         page("Notes", "<input type='text' value=' Room 4B '>"), True, "exact text with surrounding spaces"),
    Case("H10", "extraction", "Go to wikipedia.org and extract the population of Paris", "https://en.wikipedia.org/wiki/Paris",
         PARIS, True, "answer states the population", final_answer="Paris has a population of about 2.1 million residents (2023)."),
    Case("H11", "extraction", "Go to wikipedia.org and extract the population of Paris", "https://en.wikipedia.org/wiki/Paris",
         PARIS, False, "answer gives another city's population", final_answer="The population of Lyon is about 520,000 inhabitants."),
    Case("H12", "multi_step", "Go to github.com, then open the Explore page", "https://github.com/explore",
         page("Explore GitHub", "<h1>Explore</h1>"), True, "both steps done",
         task_plan=plan(("navigate", "completed"), ("click", "completed"))),
]
for _h in HELDOUT:
    _h.held_out = True
CASES += HELDOUT

for _c in CASES:
    if _c.category in ("search", "text_entry"):
        _c.last_action = "type_text"
# Multi-step cases: P1 is a premature `complete` at the pending second step; in P2-P4 the second
# step's click was dispatched (P3 on the wrong element) and verification follows that click.
for _c in CASES:
    if _c.cid in ("P2", "P3", "P4", "H12"):
        _c.last_action = "click"


async def gate_decision(vm: VerificationManager, pg, case: Case) -> tuple[str, str]:
    """Replicates verify_node's completion decision (nodes.py) for a terminal step."""
    is_captcha, reason = await detect_captcha(pg)
    if is_captcha or "/sorry/" in (pg.url or "").lower():
        return "blocked", reason or "sorry url"
    res = await vm.verify_task_completion(
        page=pg, intent_action="fixture", intent_site=None, current_url=pg.url, navigation_succeeded=True,
        input_text=case.goal, task_plan=case.task_plan, extracted_data=case.extracted, final_answer=case.final_answer,
    )
    return ("completed" if res.verified else "rejected"), res.message


GENERIC_REASONING = "The requested step has been carried out on the current page as the user instructed."


def install_live_stubs(evidence_dir: Path):
    """Stub the I/O that verify_node performs, leaving its decision logic intact."""
    import backend.agent.nodes as nodes

    async def _noop(*_a, **_k):
        return None

    nodes.database.add_event = _noop
    nodes.browser_pool.retain_task_context = _noop
    nodes.evidence_manager.evidence_dir = evidence_dir
    return nodes


async def live_decision(nodes, pg, case: Case, reasoning: str) -> tuple[str, str]:
    """Run the real verify_node on the state the graph would hold after the terminal action."""
    from backend.llm.parser import ActionResult, ParsedIntent, PlannedAction

    async def _page(_state):
        return pg

    nodes._get_task_page = _page
    if case.task_plan is not None:
        tp = case.task_plan.model_copy(deep=True)
        tp.steps[-1].status = "pending"  # verify_node itself marks the current step on dispatch
        idx = len(tp.steps)
    else:
        tp = plan((case.last_action, "pending"))
        idx = 1
    state = {
        "task_id": f"fixture-{case.cid}", "input_text": case.goal, "session_id": None,
        "parsed_intent": ParsedIntent(action="navigate", site="unknown", risk_level="low", reasoning="fixture"),
        "current_url": case.url, "action_manifest": None, "navigation_succeeded": True,
        "planned_action": PlannedAction(action_type=case.last_action, reasoning=reasoning),
        "action_history": [ActionResult(success=True, action_type=case.last_action if case.last_action != "complete" else "click",
                                        page_state_after="ready", duration_ms=1)],
        "task_plan": tp, "current_step_index": idx, "retry_count": 0, "llm_call_count": 3,
        "status": "running", "error": None, "approved": False, "blocked_reason": None,
        "extracted_data": case.extracted,
        # execute_action stores a `complete` action's reasoning as the answer unless one exists already.
        "final_answer": case.final_answer or (reasoning if case.last_action == "complete" and reasoning else None),
        "vision_called": False,
    }
    out = await nodes.verify_node(state)
    status = out.get("status", "running")
    return {"completed": "completed", "blocked": "blocked", "running": "rejected"}.get(status, status), str(out.get("error") or "")


async def main(reps: int) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    vm = VerificationManager()
    import tempfile
    nodes = install_live_stubs(Path(tempfile.mkdtemp(prefix="gate_evidence_")))
    rows = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context()
        for case in CASES:
            pg = await ctx.new_page()

            def make_handler(html: str):
                async def handler(route):
                    await route.fulfill(status=200, content_type="text/html", body=html)
                return handler

            await pg.route("**/*", make_handler(case.html))
            await pg.goto(case.url)
            decision, msg = await gate_decision(vm, pg, case)
            live_e, _ = await live_decision(nodes, pg, case, "")
            live_v, _ = await live_decision(nodes, pg, case, GENERIC_REASONING)
            times = []
            for _ in range(reps):
                t0 = time.perf_counter()
                await gate_decision(vm, pg, case)
                times.append((time.perf_counter() - t0) * 1000)
            await pg.close()
            rows.append({
                "case": case.cid, "split": "held_out" if case.held_out else "design", "category": case.category, "goal": case.goal, "url": case.url,
                "oracle_satisfied": int(case.oracle), "oracle_rationale": case.rationale,
                "dispatch_rule": "completed", "gate_decision": decision,
                "gate_reports_complete": int(decision == "completed"),
                "gate_message": msg[:160].replace("\n", " "),
                "gate_ms_median": round(statistics.median(times), 2) if times else "",
                "last_action": case.last_action,
                "live_empty_decision": live_e, "live_empty_reports_complete": int(live_e == "completed"),
                "live_verbose_decision": live_v, "live_verbose_reports_complete": int(live_v == "completed"),
            })
        await browser.close()

    with open(OUT / "verification_gate_cases.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    def summarise(sub: list[dict], label: str) -> list[dict]:
        pos = [r for r in sub if r["oracle_satisfied"]]
        neg = [r for r in sub if not r["oracle_satisfied"]]
        out = []
        col = {"dispatch_only": None, "component": "gate_reports_complete",
               "live_empty": "live_empty_reports_complete", "live_verbose": "live_verbose_reports_complete"}
        for rule, key in col.items():
            ok = (lambda r: True) if key is None else (lambda r, k=key: bool(r[k]))
            rep = [r for r in sub if ok(r)]
            false_c = [r for r in rep if not r["oracle_satisfied"]]
            missed = [r for r in pos if not ok(r)]
            out.append({
                "subset": label, "rule": rule, "n_cases": len(sub), "n_oracle_true": len(pos), "n_oracle_false": len(neg),
                "reported_complete": len(rep), "false_completions": len(false_c),
                "FCR": round(len(false_c) / len(rep), 3) if rep else "",
                "false_rejections": len(missed),
                "false_rejection_rate": round(len(missed) / len(pos), 3) if pos else "",
            })
        return out

    design = [r for r in rows if r["split"] == "design"]
    held = [r for r in rows if r["split"] == "held_out"]
    summary = summarise(design, "all")
    for cat in dict.fromkeys(r["category"] for r in design):
        summary += summarise([r for r in design if r["category"] == cat], cat)
    if held:
        summary += summarise(held, "held_out")
    with open(OUT / "verification_gate_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)

    full = [r["gate_ms_median"] for r in design if r["gate_decision"] != "blocked"]
    blk = [r["gate_ms_median"] for r in design if r["gate_decision"] == "blocked"]
    print(f"python={platform.python_version()} platform={platform.platform()} reps={reps}")
    print(f"cases={len(design)} (+{len(held)} held-out) full decisions (pre-check + Phi): n={len(full)} median={statistics.median(full):.2f} ms "
          f"max={max(full):.2f}; stopped at pre-check: n={len(blk)} values={sorted(blk)}")
    for s in summary:
        print(s)
    for r in rows:
        print(f'{r["case"]:3s} oracle={r["oracle_satisfied"]} component={r["gate_decision"]:9s} '
              f'live_empty={r["live_empty_decision"]:9s} live_verbose={r["live_verbose_decision"]:9s} {r["oracle_rationale"]}')


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=20)
    asyncio.run(main(ap.parse_args().reps))
