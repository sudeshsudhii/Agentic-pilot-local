"""ACTUAL component measurements used as inputs to the simulation (no language model needed).

  M1  completion decisions on the 92 constructed gate states under three rules:
      dispatch-only, basic success detection (error check E only, no bot-check halt), full Phi
  M2  latency of browser operations, DOM extraction, screenshots and Phi on the local sites
  M3  the real RecoveryEngine's classification and strategy sequence for six failure modes
  M4  the real Chroma memory store: retrieval rank of relevant records for synthetic queries

Writes benchmarks/simulation/inputs/*.csv|json. Usage: python -m benchmarks.simulation.measure_inputs
"""

from __future__ import annotations

import asyncio
import csv
import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent / "inputs"
sys.path.insert(0, str(ROOT / "artifacts" / "experiments"))


def write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def pct(xs: list[float], q: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))]


# ---------------------------------------------------------------- M1
async def m1_gate_rules() -> None:
    from playwright.async_api import async_playwright

    import verification_gate_study as v
    from backend.config import get_config

    cfg = get_config()
    vm = v.VerificationManager()
    rows = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context()
        for case in v.CASES:
            pg = await ctx.new_page()

            def handler_for(html):
                async def h(route):
                    await route.fulfill(status=200, content_type="text/html", body=html)
                return h

            await pg.route("**/*", handler_for(case.html))
            await pg.goto(case.url)
            cfg.verification_disabled_checks = ["H", "Q", "T", "X", "R"]
            basic, _ = await v.gate_decision(vm, pg, case, skip_bot_check=True)
            cfg.verification_disabled_checks = []
            full, _ = await v.gate_decision(vm, pg, case)
            rows.append({"case": case.cid, "split": case.split, "category": case.category, "oracle": int(case.oracle),
                         "dispatch_accepts": 1, "basic_accepts": int(basic == "completed"), "phi_accepts": int(full == "completed")})
            await pg.close()
        await browser.close()
    write_csv(OUT / "m1_gate_rules.csv", rows)
    for rule in ("basic_accepts", "phi_accepts"):
        for split in ("design", "held_out", "held_out_2"):
            sub = [r for r in rows if r["split"] == split]
            neg = [r for r in sub if not r["oracle"]]
            pos = [r for r in sub if r["oracle"]]
            print(f"M1 {rule:13s} {split:10s} withheld {sum(1 - r[rule] for r in neg)}/{len(neg)}  rejected {sum(1 - r[rule] for r in pos)}/{len(pos)}")


# ---------------------------------------------------------------- M2
async def m2_latency(reps: int = 30) -> None:
    from playwright.async_api import async_playwright

    from backend.browser.dom import DOMExtractor
    from backend.verification.manager import VerificationManager
    from benchmarks.e2e.sites import SiteServer, reset_state

    timings: dict[str, list[float]] = {k: [] for k in ("navigate", "click", "fill", "dom_extract", "screenshot", "phi")}
    vm = VerificationManager()
    with SiteServer() as site:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1280, "height": 720})
            await page.goto(site.base + "/shop")  # warm-up
            for _ in range(reps):
                reset_state()
                t = time.perf_counter(); await page.goto(site.base + "/shop"); timings["navigate"].append((time.perf_counter() - t) * 1000)
                t = time.perf_counter(); await DOMExtractor().extract(page); timings["dom_extract"].append((time.perf_counter() - t) * 1000)
                t = time.perf_counter(); await page.screenshot(); timings["screenshot"].append((time.perf_counter() - t) * 1000)
                t = time.perf_counter(); await page.fill("header input[name=q]", "kettle"); timings["fill"].append((time.perf_counter() - t) * 1000)
                t = time.perf_counter()
                async with page.expect_navigation():
                    await page.click("text=Steel kettle 1.2 l")
                timings["click"].append((time.perf_counter() - t) * 1000)
                t = time.perf_counter()
                await vm.verify_task_completion(page=page, intent_action="navigate", intent_site=None, current_url=page.url,
                                                navigation_succeeded=True, input_text=f"Go to {site.base}/shop and open the Steel kettle")
                timings["phi"].append((time.perf_counter() - t) * 1000)
            await browser.close()
    out = {k: {"n": len(v), "median_ms": round(statistics.median(v), 2), "p95_ms": round(pct(v, 0.95), 2),
               "mean_ms": round(statistics.mean(v), 2), "samples_ms": [round(x, 2) for x in v]} for k, v in timings.items()}
    (OUT / "m2_latency.json").write_text(json.dumps(out, indent=1))
    for k, v in out.items():
        print(f"M2 {k:12s} median {v['median_ms']:8.2f} ms  p95 {v['p95_ms']:8.2f} ms")


# ---------------------------------------------------------------- M3
FAILURE_MODES = {
    # Messages in the form the executor and nodes produce them.
    "navigation_failure": "Navigation failed: net::ERR_NAME_NOT_RESOLVED at http://shop.example",
    "timeout": "Timeout 30000ms exceeded while waiting for selector",
    "missing_element": "Element has no usable selector: element not found on page",
    "invalid_submission": "Input verification failed: field value does not match requested text",
    "unexpected_state": "Agent needed assistance: page layout differs from plan, need_help",
    "missing_confirmation": "Max iterations exceeded without satisfying goal: FAIL - task_completed expected True",
}


def m3_recovery() -> None:
    from backend.recovery.engine import RecoveryEngine

    eng = RecoveryEngine()
    rows = []
    for mode, msg in FAILURE_MODES.items():
        ftype = eng.classify_failure(msg)
        seq = [eng.select_strategy(ftype, r) for r in range(7)]
        rows.append({"failure_mode": mode, "error_message": msg, "classified_as": ftype, "strategies_retry0_to_6": " > ".join(seq)})
        print(f"M3 {mode:20s} -> {ftype:20s} {' > '.join(seq)}")
    write_csv(OUT / "m3_recovery.csv", rows)


# ---------------------------------------------------------------- M4
MEMORY_GROUPS = [
    # (group id, stored records [(text, relevant_to_group)], query)
    ("shop_kettle", ["Task: Go to the Quillmart shop and add the steel kettle to the cart. Status: Success.",
                     "Task: Search Quillmart for kettle and open the product page. Status: Success."],
     "Add a steel kettle to my cart on Quillmart"),
    ("wiki_velmora", ["Task: Open the Openpedia article on Velmora and report its population. Status: Success.",
                      "Task: Find the mayor of Velmora on Openpedia. Status: Success."],
     "What is the population of Velmora according to Openpedia?"),
    ("desk_contact", ["Task: Send a message through the CivicDesk contact form about parking. Status: Success.",
                      "Task: Fill the CivicDesk contact form and submit it. Status: Failed. Error encountered: Input verification failed"],
     "Submit a complaint through the CivicDesk contact form"),
    ("jotter_note", ["Task: Create a note titled Groceries in Jotter. Status: Success."],
     "Add a new note in Jotter called Call plumber"),
    ("findr_search", ["Task: Search Findr for Halden Bridge. Status: Success.",
                      "Task: Use Findr to look up glacial lakes. Status: Success."],
     "Search Findr for the observatory"),
    ("newsletter", ["Task: Subscribe ana@example.org to the CivicDesk newsletter. Status: Success."],
     "Sign lena@example.org up for the CivicDesk newsletter"),
    ("lake_depth", ["Task: Report the maximum depth of Lake Tessaly from Openpedia. Status: Success."],
     "How deep is Lake Tessaly?"),
    ("portal_conflict", ["Task: Open the portal reports page and read the Q3 total. Status: Failed. Error encountered: redirected to sign-in",
                         "Task: Open the portal reports page and read the Q3 total. Status: Success."],
     "Read the Q3 total on the portal reports page"),
    ("shop_price", ["Task: Find the price of the wool blanket on Quillmart. Status: Success."],
     "How much does the brass fountain pen cost on Quillmart?"),
    ("unrelated", [], "Book a train ticket from Velmora to Mirefield"),  # no relevant memory exists
]
DISTRACTORS = [
    "Task: Search Google for Alan Turing. Status: Success.",
    "Task: Open github.com and go to the Explore page. Status: Success.",
    "Task: Type exactly Meeting at 10am into the notes app. Status: Success.",
    "Task: Go to wikipedia.org and extract the population of Paris. Status: Success.",
    "Task: Open the pricing page on example.com. Status: Failed. Error encountered: page not found",
    "Task: Search Bing for quantum computing. Status: Success.",
    "Task: Log in to the bank portal and download a statement. Status: Failed. Error encountered: approval required",
    "Task: Find the weather in Chennai. Status: Success.",
]


async def m4_memory(k: int = 3) -> None:
    tmp = tempfile.mkdtemp(prefix="sim_mem_")
    os.environ["PILOT_DB_PATH"] = str(Path(tmp) / "data.db")
    from backend.config import get_config
    get_config.cache_clear()
    from backend.db.database import Database
    import backend.db.database as dbmod
    import backend.memory.provider as prov

    db = Database(os.environ["PILOT_DB_PATH"])
    await db.connect()
    dbmod.database = db
    prov.database = db
    store = prov.ChromaProvider()
    relevant_ids: dict[str, set[str]] = {}
    for gid, records, _ in MEMORY_GROUPS:
        relevant_ids[gid] = set()
        for text in records:
            rec = await store.store_memory(text, memory_type="episodic", task_id=f"{gid}")
            relevant_ids[gid].add(rec.memory_id)
    for text in DISTRACTORS:
        await store.store_memory(text, memory_type="episodic", task_id="distractor")
    rows = []
    for gid, records, query in MEMORY_GROUPS:
        got = await store.retrieve_relevant(query, limit=k)
        ids = [m.memory_id for m in got]
        rel = relevant_ids[gid]
        hits = [i for i in ids if i in rel]
        first = next((n + 1 for n, i in enumerate(ids) if i in rel), None)
        rows.append({"group": gid, "query": query, "n_relevant": len(rel), "retrieved": len(ids), "relevant_in_top_k": len(hits),
                     "precision_at_k": round(len(hits) / k, 3), "recall_at_k": round(len(hits) / len(rel), 3) if rel else "",
                     "reciprocal_rank": round(1 / first, 3) if first else 0.0,
                     "top1": got[0].content[:90] if got else ""})
        print(f"M4 {gid:16s} hits {len(hits)}/{len(rel)} rr {rows[-1]['reciprocal_rank']} top1: {rows[-1]['top1'][:60]}")
    write_csv(OUT / "m4_memory.csv", rows)
    await db.close()


async def main() -> None:
    OUT.mkdir(exist_ok=True)
    await m1_gate_rules()
    await m2_latency()
    m3_recovery()
    await m4_memory()


if __name__ == "__main__":
    asyncio.run(main())
