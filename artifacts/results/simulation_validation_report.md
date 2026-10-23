# Independent validation report: heldout simulation (Agent 4)

Inputs: `benchmarks/simulation/out/heldout/{scenarios.csv, recovery_scenarios.csv, results.json}`. All values recomputed from the CSVs with independent code (`/tmp/claude-0/-home-user-Agentic-pilot-local/9002c3ac-134c-52d7-af0a-ddf50aa21ff5/scratchpad/validator.py`); the authors' simulate.py / stats.py were not read or imported. Wilson 95% intervals use z = 1.959964. Comparison tolerance = 0.001.

## Sanity checks

- Scenario rows: 100; unique ids: 100
- OK: no_verification TP+FP+FN+TN = 100
- OK: basic_detection TP+FP+FN+TN = 100
- OK: evidence_gated TP+FP+FN+TN = 100
- OK: enhanced_validation TP+FP+FN+TN = 100
- OK: abl_no_evidence_collection TP+FP+FN+TN = 100
- OK: abl_no_evidence_validation TP+FP+FN+TN = 100
- OK: abl_no_memory TP+FP+FN+TN = 100
- OK: abl_no_recovery TP+FP+FN+TN = 100
- OK: mem_filtered TP+FP+FN+TN = 100
- OK: abl_no_evidence_validation vs no_verification per-scenario identical (reported and y): 0 differing rows
- OK: abl_no_evidence_collection vs evidence_gated per-scenario identical (reported and y): 0 differing rows
- INFO: no_verification_y differs from y_base in 10 scenarios
- INFO: basic_detection_y differs from y_base in 10 scenarios
- INFO: evidence_gated_y differs from y_base in 11 scenarios
- INFO: enhanced_validation_y differs from y_base in 15 scenarios
- INFO: abl_no_evidence_collection_y differs from y_base in 11 scenarios
- INFO: abl_no_evidence_validation_y differs from y_base in 10 scenarios
- INFO: abl_no_memory_y differs from y_base in 9 scenarios
- INFO: abl_no_recovery_y differs from y_base in 18 scenarios
- INFO: mem_filtered_y differs from y_base in 10 scenarios
- INFO: repeated==1 count: 44

## 1. Per-configuration metrics (N = 100)

| Config | TP | FP | FN | TN | TSR [95% CI] | FCR [95% CI] | FRR [95% CI] | Precision | Recall | F1 | Accuracy |
|---|---|---|---|---|---|---|---|---|---|---|---|
| no_verification | 43 | 28 | 3 | 26 | 0.430 [0.337, 0.528] | 0.394 [0.289, 0.511] | 0.065 [0.022, 0.175] | 0.606 | 0.935 | 0.735 | 0.690 |
| basic_detection | 42 | 24 | 4 | 30 | 0.420 [0.328, 0.518] | 0.364 [0.258, 0.484] | 0.087 [0.034, 0.203] | 0.636 | 0.913 | 0.750 | 0.720 |
| evidence_gated | 37 | 19 | 10 | 34 | 0.370 [0.282, 0.468] | 0.339 [0.229, 0.470] | 0.213 [0.120, 0.349] | 0.661 | 0.787 | 0.718 | 0.710 |
| enhanced_validation | 39 | 8 | 12 | 41 | 0.390 [0.300, 0.488] | 0.170 [0.089, 0.301] | 0.235 [0.140, 0.368] | 0.830 | 0.765 | 0.796 | 0.800 |
| abl_no_evidence_collection | 37 | 19 | 10 | 34 | 0.370 [0.282, 0.468] | 0.339 [0.229, 0.470] | 0.213 [0.120, 0.349] | 0.661 | 0.787 | 0.718 | 0.710 |
| abl_no_evidence_validation | 43 | 28 | 3 | 26 | 0.430 [0.337, 0.528] | 0.394 [0.289, 0.511] | 0.065 [0.022, 0.175] | 0.606 | 0.935 | 0.735 | 0.690 |
| abl_no_memory | 38 | 20 | 9 | 33 | 0.380 [0.291, 0.478] | 0.345 [0.236, 0.473] | 0.191 [0.104, 0.325] | 0.655 | 0.809 | 0.724 | 0.710 |
| abl_no_recovery | 30 | 16 | 10 | 44 | 0.300 [0.219, 0.396] | 0.348 [0.227, 0.492] | 0.250 [0.142, 0.402] | 0.652 | 0.750 | 0.698 | 0.740 |
| mem_filtered | 38 | 19 | 10 | 33 | 0.380 [0.291, 0.478] | 0.333 [0.225, 0.463] | 0.208 [0.117, 0.343] | 0.667 | 0.792 | 0.724 | 0.710 |

## 2. Paired tests vs evidence_gated (exact two-sided McNemar)

Correct test: ref_only = evidence_gated correct and other wrong; other_only = the reverse. FP test: other_only = other has a false completion and evidence_gated does not. Risk difference = mean(FP_other - FP_ref).

| Config | correct ref_only | correct other_only | p (correct) | FP other_only | FP ref_only | p (FP) | FP risk diff |
|---|---|---|---|---|---|---|---|
| no_verification | 9 | 7 | 0.803619 | 9 | 0 | 0.003906 | +0.09 |
| basic_detection | 5 | 6 | 1.000000 | 5 | 0 | 0.062500 | +0.05 |
| enhanced_validation | 2 | 11 | 0.022461 | 0 | 11 | 0.000977 | -0.11 |
| abl_no_evidence_collection | 0 | 0 | 1.000000 | 0 | 0 | 1.000000 | +0.00 |
| abl_no_evidence_validation | 9 | 7 | 0.803619 | 9 | 0 | 0.003906 | +0.09 |
| abl_no_memory | 0 | 0 | 1.000000 | 1 | 0 | 1.000000 | +0.01 |
| abl_no_recovery | 0 | 3 | 0.250000 | 0 | 3 | 0.250000 | -0.03 |
| mem_filtered | 0 | 0 | 1.000000 | 0 | 0 | 1.000000 | +0.00 |

## 3. Memory subset (repeated == 1, N = 44)

| Config | TP | FP | FN | TN | TSR [95% CI] | FCR [95% CI] | FRR [95% CI] | Precision | Recall | F1 | Accuracy |
|---|---|---|---|---|---|---|---|---|---|---|---|
| abl_no_memory | 19 | 12 | 2 | 11 | 0.432 [0.297, 0.578] | 0.387 [0.237, 0.562] | 0.095 [0.027, 0.289] | 0.613 | 0.905 | 0.731 | 0.682 |
| evidence_gated | 18 | 11 | 3 | 12 | 0.409 [0.277, 0.556] | 0.379 [0.227, 0.560] | 0.143 [0.050, 0.346] | 0.621 | 0.857 | 0.720 | 0.682 |
| mem_filtered | 19 | 11 | 3 | 11 | 0.432 [0.297, 0.578] | 0.367 [0.219, 0.545] | 0.136 [0.047, 0.333] | 0.633 | 0.864 | 0.731 | 0.682 |

## 4. Recovery

| Config | rows | Recovery success (transient) | Failure detection | False completions | Unnecessary attempts (permanent) | Mean cost (s) |
|---|---|---|---|---|---|---|
| no_recovery | 120 (27 permanent) | 0/93 = 0.000 | 111/120 = 0.925 | 9 | 0 | 0.0000 |
| retry_based | 120 (27 permanent) | 69/93 = 0.742 | 111/120 = 0.925 | 9 | 162 | 10.8902 |
| evidence_guided | 120 (27 permanent) | 87/93 = 0.935 | 118/120 = 0.983 | 2 | 162 | 9.9733 |

## 5. Discrepancies vs results.json (tolerance 0.001)

**None.** Every compared field in `configs` (N, TP, FP, FN, TN, TSR, FCR, FRR, precision, recall, F1, accuracy), `paired_tests_vs_evidence_gated` (correct_ref_only, correct_other_only, mcnemar_p_correct, fp_other_only, fp_ref_only, mcnemar_p_fp, fp_rate_diff), `memory` (same confusion metrics) and `recovery` (recovery_success, failure_detection, false_completions, unnecessary_attempts, mean_cost_s) matches the independent recomputation within 0.001.
## 6. Notes and observations (not discrepancies)

- **Coverage:** 9 configs x 12 fields, 8 paired comparisons x 7 fields, 3 memory configs x 12 fields, and 3 recovery configs x 5 fields (counts given as [num, den] pairs) were checked against results.json. results.json stores no Wilson intervals under `configs`, so the CIs in Section 1 are reported here but could not be compared.
- **Ground truth differs by configuration:** `C_y` is not the same as `y_base`. Between 9 and 18 scenarios differ, depending on the configuration. This is why "correct" (reported == y) and "false completion" can move independently. For example, abl_no_memory and evidence_gated have 0/0 discordant pairs on correctness but a 1/0 split on false completions. In scenario S202-041 (y_base = 0), evidence_gated has reported=0 and y=1 (FN), while abl_no_memory has reported=1 and y=0 (FP). Both are wrong, but only one is a false completion. The definitions in the brief allow this, but readers of the paper should be told that each configuration's outcome label is specific to that configuration.
- **Substantive pattern:** evidence_gated's TSR (0.37) is lower than no_verification's (0.43), and its FRR is higher (0.213 vs 0.065). Its overall correctness is not significantly different (McNemar p = 0.80). The improvement that is significant is on false completions (9 vs 0 discordant, p = 0.0039, risk difference +0.09 for no_verification). enhanced_validation is significantly better than evidence_gated on both correctness (p = 0.022) and false completions (p = 0.00098).
- **Recovery:** retry_based and evidence_guided both spend 162 attempts on the 27 permanent failures, an average of 6 each. The evidence-guided strategy saves no attempts on permanent failures.
