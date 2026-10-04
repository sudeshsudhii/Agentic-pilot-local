"""Measure the error rate of the end-to-end oracle Phi* on scripted trajectories (R10).

For every task we drive Chromium directly (no agent, no model) through three trajectories:
  golden    a hand-written correct solution             -> Phi* should be 1 (0 for unsatisfiable tasks)
  idle      open the start page and stop, no answer     -> Phi* should be 0 (1 where the start page is the goal)
  perturbed a near miss (wrong value, wrong item, extra submit, wrong query) -> Phi* should be 0
and compare the oracle's verdict with the intended label.

Usage: python -m benchmarks.e2e.validate_oracle [--out artifacts/results/e2e_oracle_validation.csv]
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import re
from pathlib import Path

from benchmarks.e2e import oracle
from benchmarks.e2e.sites import SiteServer, reset_state, snapshot_state

# step DSL: ("goto", path) ("fill", selector, text) ("click", selector) ("select", selector, value)
#           ("check", selector) ("press", selector, key) ("answer", text)
GOLDEN: dict[str, list] = {
    "D01": [("goto", "/wiki/Velmora")],
    "D02": [("goto", "/wiki/Lake_Tessaly"), ("answer", "The maximum depth is 214 m.")],
    "D03": [("goto", "/findr"), ("fill", "main input[name=q]", "Halden Bridge"), ("press", "main input[name=q]", "Enter")],
    "D04": [("goto", "/findr"), ("fill", "main input[name=q]", "Corvane"), ("press", "main input[name=q]", "Enter"),
            ("click", "text=Corvane - Openpedia"), ("answer", "Edda Corvane was born in 1871.")],
    "D05": [("goto", "/desk/contact"), ("fill", "textarea[name=message]", "Bin not collected")],
    "D06": [("goto", "/shop"), ("click", "text=Ceramic mug 300 ml"), ("click", "text=Add to cart")],
    "D07": [("goto", "/shop"), ("answer", "The Steel kettle costs 42.00 EUR.")],
    "D08": [("goto", "/portal/reports")],
    "D09": [("goto", "/wiki/Main_Page"), ("click", "text=Tarsk language")],
    "D10": [("goto", "/desk/newsletter"), ("fill", "input[name=email]", "ana@example.org"), ("click", "text=Subscribe")],
    "T01": [("goto", "/wiki/Mirefield_Observatory"), ("answer", "Its altitude is 2,310 m.")],
    "T02": [("goto", "/wiki/Tarsk_language"), ("answer", "Tarsk has 92,000 speakers.")],
    "T03": [("goto", "/wiki/Main_Page"), ("click", "text=Halden Bridge"), ("answer", "It opened in 1934.")],
    "T04": [("goto", "/findr"), ("fill", "main input[name=q]", "glacial lake"), ("press", "main input[name=q]", "Enter")],
    "T05": [("goto", "/findr"), ("fill", "main input[name=q]", "observatory"), ("press", "main input[name=q]", "Enter"),
            ("click", "text=Mirefield Observatory - Openpedia"), ("answer", "The main telescope is a 1.8 m reflector.")],
    "T06": [("goto", "/findr"), ("fill", "main input[name=q]", "Halden Bridge"), ("press", "main input[name=q]", "Enter"),
            ("click", "text=Halden Bridge - Openpedia"), ("answer", "It was designed by Piet Halden.")],
    "T07": [("goto", "/wiki/Main_Page"), ("click", "text=Velmora"), ("answer", "Velmora had 48,213 inhabitants in 2020.")],
    "T08": [("goto", "/shop/cart")],
    "T09": [("goto", "/shop"), ("fill", "header input[name=q]", "fountain pen"), ("press", "header input[name=q]", "Enter"),
            ("click", "text=Brass fountain pen"), ("click", "text=Add to cart")],
    "T10": [("goto", "/shop"), ("click", "text=Linen notebook A5"), ("fill", "input[name=qty]", "2"), ("click", "text=Add to cart")],
    "T11": [("goto", "/shop"), ("answer", "The wool blanket costs 54.00 EUR.")],
    "T12": [("goto", "/shop/search?q=lamp"), ("answer", "The item number is QM-301.")],
    "T13": [("goto", "/desk/contact"), ("fill", "input[name=name]", "Ravi Kumar"), ("fill", "input[name=email]", "ravi@example.org"),
            ("select", "select[name=subject]", "Parking"), ("fill", "textarea[name=message]", "Street lamp broken near the market"),
            ("click", "text=Send message")],
    "T14": [("goto", "/desk/newsletter"), ("fill", "input[name=email]", "lena@example.org"), ("check", "input[name=weekly]"),
            ("click", "text=Subscribe")],
    "T15": [("goto", "/desk/contact"), ("fill", "input[name=name]", "Ravi Kumar")],
    "T16": [("goto", "/shop"), ("fill", "header input[name=q]", "kettle")],
    "T17": [("goto", "/jotter"), ("click", "text=Ferry times")],
    "T18": [("goto", "/jotter"), ("click", "text=Ferry times"), ("answer", "The evening ferry leaves at 17:10.")],
    "T19": [("goto", "/jotter"), ("click", "text=New note"), ("fill", "input[name=title]", "Call plumber"),
            ("fill", "textarea[name=body]", "Thursday 9am"), ("click", "text=Save note")],
    "T20": [("goto", "/jotter"), ("click", "text=New note"), ("fill", "input[name=title]", "Books"),
            ("fill", "textarea[name=body]", "return library books"), ("click", "text=Save note")],
    "T21": [("goto", "/portal/invoices")],
    "T22": [("goto", "/wiki/Brannoch_Castle")],
    "T23": [("goto", "/shop"), ("fill", "header input[name=q]", "copper frying pan"), ("press", "header input[name=q]", "Enter")],
    "T24": [("goto", "/jotter")],
    "T25": [("goto", "/findr"), ("fill", "main input[name=q]", "chemist"), ("press", "main input[name=q]", "Enter"),
            ("click", "text=Corvane - Openpedia"), ("answer", "Corvane worked in organic chemistry.")],
    "T26": [("goto", "/shop"), ("click", "text=Brass fountain pen"), ("click", "text=Add to cart"),
            ("goto", "/shop"), ("click", "text=Ceramic mug 300 ml"), ("click", "text=Add to cart"), ("goto", "/shop/cart")],
    "T27": [("goto", "/wiki/Velmora"), ("answer", "The mayor is Ilse Varga.")],
    "T28": [("goto", "/wiki/Main_Page"), ("fill", "header input[name=q]", "Lake Tessaly"), ("press", "header input[name=q]", "Enter")],
    "T29": [("goto", "/desk/contact"), ("fill", "input[name=name]", "Mei Lin"), ("fill", "input[name=email]", "mei@example.org"),
            ("select", "select[name=subject]", "Waste collection"), ("fill", "textarea[name=message]", "Bins on Ost Street were skipped"),
            ("click", "text=Send message")],
    "T30": [("goto", "/wiki/Lake_Tessaly"), ("answer", "It drains into the River Ost.")],
}

# Near misses: each must leave the task unachieved.
PERTURBED: dict[str, list] = {
    "D01": [("goto", "/wiki/Corvane")],
    "D02": [("goto", "/wiki/Lake_Tessaly"), ("answer", "The lake covers 38 km2.")],
    "D03": [("goto", "/findr"), ("fill", "main input[name=q]", "Halden"), ("press", "main input[name=q]", "Enter")],
    "D04": [("goto", "/wiki/Corvane"), ("answer", "Edda Corvane died in 1939.")],
    "D05": [("goto", "/desk/contact"), ("fill", "textarea[name=message]", "Bin not collected"), ("click", "text=Send message")],
    "D06": [("goto", "/shop"), ("click", "text=Steel kettle 1.2 l"), ("click", "text=Add to cart")],
    "D07": [("goto", "/shop"), ("answer", "The Ceramic mug costs 11.90 EUR.")],
    "D09": [("goto", "/wiki/Main_Page"), ("click", "text=Velmora")],
    "D10": [("goto", "/desk/newsletter"), ("fill", "input[name=email]", "anna@example.org"), ("click", "text=Subscribe")],
    "T01": [("goto", "/wiki/Mirefield_Observatory"), ("answer", "It was established in 1958.")],
    "T02": [("goto", "/wiki/Tarsk_language"), ("answer", "Tarsk is written in the Latin script.")],
    "T03": [("goto", "/wiki/Halden_Bridge"), ("answer", "It is 1,140 m long.")],
    "T04": [("goto", "/findr"), ("fill", "main input[name=q]", "lake"), ("press", "main input[name=q]", "Enter")],
    "T05": [("goto", "/wiki/Mirefield_Observatory"), ("answer", "The observatory is at 2,310 m.")],
    "T06": [("goto", "/wiki/Halden_Bridge"), ("answer", "The bridge opened in 1934.")],
    "T07": [("goto", "/wiki/Velmora"), ("answer", "Velmora was founded in 1652.")],
    "T08": [("goto", "/shop")],
    "T09": [("goto", "/shop"), ("click", "text=Linen notebook A5"), ("click", "text=Add to cart")],
    "T10": [("goto", "/shop"), ("click", "text=Linen notebook A5"), ("click", "text=Add to cart")],
    "T11": [("goto", "/shop"), ("answer", "The wool blanket costs 45.00 EUR.")],
    "T12": [("goto", "/shop/search?q=lamp"), ("answer", "The item number is QM-302.")],
    "T13": [("goto", "/desk/contact"), ("fill", "input[name=name]", "Ravi Kumar"), ("fill", "input[name=email]", "ravi@example.org"),
            ("select", "select[name=subject]", "Other"), ("fill", "textarea[name=message]", "Street lamp broken near the market"),
            ("click", "text=Send message")],
    "T14": [("goto", "/desk/newsletter"), ("fill", "input[name=email]", "lena@example.org"), ("click", "text=Subscribe")],
    "T15": [("goto", "/desk/contact"), ("fill", "input[name=name]", "Ravi Kumar Jr")],
    "T16": [("goto", "/shop"), ("fill", "header input[name=q]", "kettle"), ("press", "header input[name=q]", "Enter")],
    "T17": [("goto", "/jotter"), ("click", "text=Groceries")],
    "T18": [("goto", "/jotter"), ("click", "text=Ferry times"), ("answer", "The morning ferry leaves at 07:40.")],
    "T19": [("goto", "/jotter"), ("click", "text=New note"), ("fill", "input[name=title]", "Call plumber"), ("click", "text=Save note")],
    "T20": [("goto", "/jotter"), ("click", "text=New note"), ("fill", "input[name=title]", "Book"),
            ("fill", "textarea[name=body]", "return library books"), ("click", "text=Save note")],
    "T25": [("goto", "/wiki/Corvane"), ("answer", "Corvane is known for the Corvane reaction.")],
    "T26": [("goto", "/shop"), ("click", "text=Brass fountain pen"), ("click", "text=Add to cart"), ("goto", "/shop/cart")],
    "T27": [("goto", "/wiki/Velmora"), ("answer", "Velmora lies on the River Ost.")],
    "T28": [("goto", "/wiki/Main_Page"), ("fill", "header input[name=q]", "Lake Tessaly"), ("goto", "/wiki/Main_Page")],
    "T30": [("goto", "/wiki/Lake_Tessaly"), ("answer", "It lies in Ostland.")],
}


async def run(page, base: str, steps: list) -> tuple[str, str]:
    answer = ""
    for st in steps:
        kind = st[0]
        if kind == "goto":
            await page.goto(base + st[1])
        elif kind == "fill":
            await page.fill(st[1], st[2])
        elif kind == "click":
            async with page.expect_navigation(wait_until="load", timeout=3000) if await _navigates(page, st[1]) else _null():
                await page.click(st[1])
        elif kind == "select":
            await page.select_option(st[1], st[2])
        elif kind == "check":
            await page.check(st[1])
        elif kind == "press":
            async with page.expect_navigation(wait_until="load", timeout=3000):
                await page.press(st[1], st[2])
        elif kind == "answer":
            answer = st[1]
    await page.wait_for_timeout(150)  # let autosave requests land
    return page.url, answer


async def _navigates(page, selector: str) -> bool:
    return await page.eval_on_selector(selector, "el => !!(el.closest('a') || el.closest('form'))")


class _null:
    async def __aenter__(self):
        return None

    async def __aexit__(self, *exc):
        return False


async def main(out: Path) -> None:
    from playwright.async_api import async_playwright

    tasks = json.loads((Path(__file__).parent / "tasks.json").read_text())["tasks"]
    rows = []
    with SiteServer() as site:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            for t in tasks:
                start = re.sub(r"^.*?\{base\}(\S*).*$", r"\1", t["goal"]).rstrip(",.")
                trajectories = [("golden", GOLDEN[t["id"]], t["oracle"]["type"] != "unsatisfiable"),
                                # Idle achieves the task only where the start page is the goal (one-step navigation).
                                ("idle", [("goto", start)], GOLDEN[t["id"]] == [("goto", start)] and t["oracle"]["type"] != "unsatisfiable")]
                if t["id"] in PERTURBED:
                    trajectories.append(("perturbed", PERTURBED[t["id"]], False))
                for kind, steps, intended in trajectories:
                    reset_state()
                    ctx = await browser.new_context()
                    page = await ctx.new_page()
                    try:
                        url, answer = await run(page, site.base, steps)
                        got, reason = oracle.evaluate(t["oracle"], url, answer, snapshot_state())
                        err = ""
                    except Exception as exc:  # a broken script is reported, not scored
                        got, reason, err = None, "", f"{type(exc).__name__}: {exc}"[:200]
                    await ctx.close()
                    rows.append({"task": t["id"], "split": t["split"], "category": t["category"], "trajectory": kind,
                                 "intended": int(intended), "oracle": "" if got is None else int(got),
                                 "agree": "" if got is None else int(got == intended), "reason": reason, "script_error": err})
            await browser.close()
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    scored = [r for r in rows if r["agree"] != ""]
    for kind in ("golden", "idle", "perturbed"):
        sub = [r for r in scored if r["trajectory"] == kind]
        print(f"{kind:9s}: {sum(r['agree'] for r in sub)}/{len(sub)} verdicts as intended")
    fn = [r for r in scored if r["intended"] == 1 and r["oracle"] == 0]
    fp = [r for r in scored if r["intended"] == 0 and r["oracle"] == 1]
    print(f"oracle false negatives {len(fn)}/{sum(1 for r in scored if r['intended'] == 1)}, "
          f"false positives {len(fp)}/{sum(1 for r in scored if r['intended'] == 0)}; script errors: {sum(1 for r in rows if r['script_error'])}")
    for r in fn + fp + [r for r in rows if r["script_error"]]:
        print("  ", r)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/results/e2e_oracle_validation.csv")
    asyncio.run(main(Path(ap.parse_args().out)))
