"""Controlled study of Agentic Pilot's completion gate on constructed page fixtures.

What this measures
------------------
The agent decides "task complete" in verify_node (backend/agent/nodes.py) by
(1) a CAPTCHA pre-check (backend.browser.dom.detect_captcha, plus a '/sorry/'
URL test) and (2) VerificationManager.verify_task_completion
(backend/verification/manager.py). This script runs exactly that code against
hand-built end states whose true outcome is known, and compares it with a
dispatch-only rule that reports success whenever the last action dispatched.

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
]


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


async def main(reps: int) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    vm = VerificationManager()
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
            times = []
            for _ in range(reps):
                t0 = time.perf_counter()
                await gate_decision(vm, pg, case)
                times.append((time.perf_counter() - t0) * 1000)
            await pg.close()
            rows.append({
                "case": case.cid, "category": case.category, "goal": case.goal, "url": case.url,
                "oracle_satisfied": int(case.oracle), "oracle_rationale": case.rationale,
                "dispatch_rule": "completed", "gate_decision": decision,
                "gate_reports_complete": int(decision == "completed"),
                "gate_message": msg[:160].replace("\n", " "),
                "gate_ms_median": round(statistics.median(times), 2) if times else "",
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
        for rule in ("dispatch_only", "evidence_gate"):
            rep = [r for r in sub if (rule == "dispatch_only" or r["gate_reports_complete"])]
            false_c = [r for r in rep if not r["oracle_satisfied"]]
            missed = [r for r in pos if rule == "evidence_gate" and not r["gate_reports_complete"]]
            out.append({
                "subset": label, "rule": rule, "n_cases": len(sub), "n_oracle_true": len(pos), "n_oracle_false": len(neg),
                "reported_complete": len(rep), "false_completions": len(false_c),
                "FCR": round(len(false_c) / len(rep), 3) if rep else "",
                "false_rejections": len(missed),
                "false_rejection_rate": round(len(missed) / len(pos), 3) if pos else "",
            })
        return out

    summary = summarise(rows, "all")
    for cat in dict.fromkeys(r["category"] for r in rows):
        summary += summarise([r for r in rows if r["category"] == cat], cat)
    with open(OUT / "verification_gate_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)

    lat = [r["gate_ms_median"] for r in rows if r["gate_ms_median"] != ""]
    print(f"python={platform.python_version()} platform={platform.platform()} reps={reps}")
    print(f"cases={len(rows)} gate latency median-of-medians={statistics.median(lat):.2f} ms "
          f"min={min(lat):.2f} max={max(lat):.2f}")
    for s in summary:
        print(s)
    for r in rows:
        if r["gate_reports_complete"] != r["oracle_satisfied"]:
            print("DISAGREE", r["case"], r["gate_decision"], "oracle=", r["oracle_satisfied"], "-", r["oracle_rationale"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=20)
    asyncio.run(main(ap.parse_args().reps))
