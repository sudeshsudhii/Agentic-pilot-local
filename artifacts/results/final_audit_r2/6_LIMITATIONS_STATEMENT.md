# Limitations statement

This statement is suitable for the author's cover letter, and its substance is in §XII of the paper.

**What has been validated (ACTUAL, executed on the implementation):**

1. **Completion gate Φ.** It was exercised in the agent's real verification node, called directly with stubbed I/O, on 92 constructed browser states.
   - On 42 held-out states frozen before testing, it withheld 9 of 22 premature completions and rejected 1 of 20 completed states.
   - It was correct on significantly more states than a rule that accepts every dispatched action (exact McNemar p = 0.021).
   - It was **not** significantly better than the measured detector that applies only its error check (7 vs 1 discordant states, p = 0.070; pooled p = 0.11).
   - On the states its rules were fixed on, it withheld 20 of 23. That figure is optimistic and is reported without a test.
   - A decision costs a median of 26.8 ms and no model call.
   - A per-conjunct ablation shows which checks fire.
2. **Measured component behaviour:**
   - the memory store returns a relevant record in its top three for every query that has one, but it has no relevance threshold;
   - the recovery engine classifies a missing confirmation as unknown;
   - browser and evidence operations take tens of milliseconds.
3. **Locality.** By default the model client refuses non-loopback endpoints. In 70 control-loop episodes against a scripted stand-in model server, run on a clean commit, the agent's Python processes connected only to that stand-in on 127.0.0.1.
4. **Oracle.** The end-to-end oracle made no error on 35 correct solutions and 34 near misses written to test it.

**What has been studied only by simulation (SYNTHETIC, conditional on ASSUMED inputs; model v2, revised post hoc):**

- **False completions.** Under the stated assumptions, the gate lowers false completions: 19 against 28 of 100 synthetic scenarios, a paired reduction of 0.11 per scenario [0.05, 0.18]. The direction is fixed by the model's construction.
- **Decision accuracy and task success.** The gate's simulated decision accuracy did not differ significantly from accepting every claim (52 vs 46 of 74, p = 0.15), and neither did its simulated task success.
- **Dependence on an unmeasured rate.** The size of these effects depends on the premature-claim rate, which is unmeasured.
- **Memory, recovery and overhead:**
  - the simulated memory study is underpowered;
  - the recovery and overhead results follow from assumed per-attempt success rates and an assumed inference time;
  - the benefits of the proposed enhanced validation, evidence-guided recovery and relevance filter follow only from their assumed rates and are not evidence for those components.
- **Revision history.** The simulation model was revised twice after its first results were known, both times to match the code. The revisions moved the results in the gate's favour.

**What has not been validated:**

- **End-to-end agent performance.** The end-to-end evaluation of the full agent with a language model was implemented but not executed: the environment used for this work could not download model weights. As a result, the paper makes no claim about:
  - task success;
  - the gate's effect on real episodes;
  - the self-verification baseline;
  - memory or recovery in real use.
- **Locality beyond the instrumented processes.** The locality test does not cover:
  - a real model server, including Ollama cloud models, a remote `OLLAMA_HOST` or tunnels;
  - Chromium's own traffic, WebSockets, DNS and UDP;
  - proxies configured through environment variables;
  - the desktop client;
  - the monitoring UI's web fonts.

  Local data is stored unencrypted with default file permissions, and the local API has no authentication or Origin check. "Privacy-preserving" therefore holds only in the narrow sense defined in §XI. It is not a privacy guarantee.
- **Annotation independence.** The gate states and oracle labels were written by the same AI agent that designed the gate's fixes. No person or second annotator has relabelled them, and the held-out states are template-like. The recomputation checks were done by AI agents of the same pipeline, so they verify arithmetic, not ground truth.

Physical hardware testing is not part of this study's scope and is not required for the claims made.
