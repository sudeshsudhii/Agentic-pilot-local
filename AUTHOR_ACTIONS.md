# Author actions

These are the experiments and checks I could not complete in this session, each with its protocol. The paper has no placeholders. Where data is missing, the claim has been scoped down instead (option b). Each item says which sentence or table it would change once you have the data.

**Why these could not run here:** the session's network policy blocked `huggingface.co` and `registry.ollama.ai`, so no model weights could be downloaded. Live websites were blocked too. Everything that needs no model was run (see `RESPONSE_TO_REVIEWERS.md`).

---

## A1. End-to-end runs with a language model (R1, R2, R3, R4, R13, R14, R15)

**Option chosen in the paper:** (b) scope down, plus this protocol. §VII-E states that no end-to-end result exists, and Table II marks those components "--" under Eval.

**Resources:**
- A computer with Ollama, 16 GB RAM and 10–20 GB of disk.
- About 6–15 hours on CPU for the recommended set. This is my estimate, not a measurement; a GPU is much faster.

**Steps (from the repository root):**

```bash
# 1. Models (default pair used by the agent)
ollama pull qwen2.5:1.5b
ollama pull moondream

# 2. Python environment
pip install -r backend/requirements.txt
playwright install chromium

# 3. Check the harness on the development split first (may be repeated freely)
python -m benchmarks.e2e.run_e2e --split dev --trials 1 --configs full \
       --out artifacts/results/e2e/dev_check

# 4. Freeze: commit the code, then do not change prompts, rules or tasks again.
git commit -am "freeze for end-to-end evaluation" && git push

# 5. Test split, three trials, baselines first
python -m benchmarks.e2e.run_e2e --split test --trials 3 \
  --configs full,no_verification,self_verification,no_memory,no_recovery \
  --out artifacts/results/e2e/run1

# 6. Ablations and per-strategy recovery (optional, same output folder)
python -m benchmarks.e2e.run_e2e --split test --trials 3 \
  --configs gate_without_E,gate_without_H,gate_without_Q,gate_without_T,gate_without_X,gate_without_R,gate_without_B,recovery_retry_only,recovery_vision_only,recovery_replan_only \
  --out artifacts/results/e2e/run1

# 7. Analysis
python -m benchmarks.e2e.analyze_e2e artifacts/results/e2e/run1 --split test
```

**Outputs and where they go in the paper:**

| Output | Fills |
|---|---|
| `analysis/tables/e2e_configs.tex` (success, FCR, FRR with Wilson CIs, Δ success with bootstrap CI and McNemar p, calls, time) | New table in §VII-E. Replace the paragraph "We have not run the end-to-end evaluation…" with a description of this table. |
| `analysis/categories.csv` | Per-category sentence in §VII-E (R9). |
| `analysis/recovery.csv` | Recovery paragraph and table (R14). Change the "Recovery" rows of Table II from "--" to the new evidence. |
| `no_memory` rows plus `analysis/memory_losses.csv` | Memory paragraph (R13). Open each listed episode's evidence folder to judge whether retrieved memory misled the planner. |
| `analysis/overhead.json` | §VII-C: added time, actions, model calls and tokens per task, and false completions avoided (R15). |
| `run_meta.json` | §VI: hardware, Ollama version, model digests, date, git commit. |
| `non_local_page_hosts` in `episodes.jsonl` | §IX: should stay empty; report it if not. |

**After running:** update the abstract's last sentence, the "We do not claim…" sentence in §I, the Eval column of Table II, §VIII ("The evidence does not show that the agent completes tasks") and the conclusion.

## A2. A published framework as a third baseline (R3c)

**Option chosen:** (c). §VI-B says this baseline is left to the authors' runs.

**Protocol:**
1. Use an agent that can drive a local Playwright browser with an Ollama model, for example a BrowserGym-based agent [WorkArena, ICML 2024].
2. Configure it with `qwen2.5:1.5b`, temperature 0, seed 7, and a 15-call budget.
3. Point it at `benchmarks/e2e/sites.py` (`python -m benchmarks.e2e.sites` serves them on port 8800).
4. Give it the test-split goals from `tasks.json`, with `{base}` set to `http://127.0.0.1:8800`.
5. After each episode, save the final URL, the answer and `sites.snapshot_state()`, and score them with `benchmarks/e2e/oracle.evaluate`.

Report the result as one more row of the e2e table, with a McNemar test against `full`.

## A3. Independent labelling of the gate states (R5, R10)

**Option chosen:** (b) disclosed limitation (§VI-A, §X), plus this protocol.

1. Give a person who has not seen `backend/verification/manager.py` the goal, URL, rendered page and answer of each of the 92 states. The CSV has the goal and URL; the HTML is in `artifacts/experiments/verification_gate_study.py` and `gate_heldout2.py`.
2. Ask them for "achieved: yes/no" without showing them the existing labels.
3. Compute Cohen's κ against the author labels, then recompute Table IV with their labels. Simplest way: replace `oracle_satisfied` in a copy of `verification_gate_cases.csv` and rerun `artifacts/experiments/gate_stats.py` on it.
4. Better still, have that person also write 40 new states (held-out 3) before seeing the gate, and run `verification_gate_study.py` on them.

This fills one sentence in §VI-A ("Its limitation is that one author wrote…") and a new row in Table IV.

## A4. Audit of the e2e oracle on real agent episodes (R10)

**Option chosen:** (b). §VII-D states that the validation covers scripted trajectories only.

After A1:
1. Sample 10% of the episodes of `full`, stratified by category.
2. Have a person judge success from the evidence screenshots and the answer, blind to the oracle's verdict.
3. Report agreement and Cohen's κ in §VII-D.

## A5. Chromium background traffic (R7)

**Option chosen:** (b). §IX states that the egress test did not observe the Chromium binary's own background traffic.

**Protocol:** on Linux, run one e2e episode under a network namespace or a firewall rule that logs all outbound connections of the user. For example, `sudo tcpdump -i any -n 'not net 127.0.0.0/8'` while running `run_e2e.py --split dev --tasks D01`. Report any destination. If there are some, add `--disable-background-networking` and similar flags to `backend/browser/pool.py`, then re-test.

## A6. Items that are yours to decide

- **Author block:** `paper/main.tex` has `\author{}`. Add names and affiliations, or leave it empty for a double-blind venue.
- **Archived release:** tag the evaluated commit and archive it (for example, Zenodo DOI), then cite it in §V. The paper currently cites commit `bf0a8a5`.
- **Anti-detection browser settings** (`backend/browser/pool.py`): §IX takes a position on them. Decide whether to keep or remove them.
- **Known weakness found by this revision:** the answer check X is not triggered by "tell me / what / find / get me" requests. Fixing it would change the gate. If you fix it, write a **new** held-out set first and re-run the gate study; do not re-score held-out 2 and present it as unseen.

## A7. References

All 47 references were verified to exist. The 7 added in this revision (McNemar 1947, Wilson 1927, Clopper–Pearson 1934, Efron 1979, Cohen 1960, VisualWebArena ACL 2024, WorkArena ICML 2024) were checked by web search against their publishers' records. No unverifiable reference remains in the paper.
