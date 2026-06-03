# Proposed Experiment Timeline

> Companion to the full pipeline guide: [WORKFLOW.md](WORKFLOW.md).
> This document lays out a **proposed week-by-week plan** for running the
> remaining experiments, evaluating them, and writing up the results.
> Dates are indicative and can be adjusted after discussion.

---

## 1. Where Things Stand Now

- **Pipeline** is working end-to-end (LLM call → post-processing → scoring →
  comparison sheet). See [WORKFLOW.md](WORKFLOW.md) for the full description.
- **Done so far:**
  - Full-story runs for the main model × prompt combinations.
  - Sentence-by-sentence mode for Llama-3.1-70B (p0–p3).
  - New strategy prompt **P4** added (small models).
  - Batch evaluation + colour-coded comparison sheet (flat and pivoted layouts).
- **Best result so far:** Qwen-2.5-72B, P0, full pipeline (`_abcde`) —
  Token Recall 0.416, Mistake Precision 0.677.

---

## 2. The Experiment Grid

The full experiment space is:

| Dimension | Values | Count |
|-----------|--------|-------|
| Model family | Llama-3.1, Qwen-2.5 | 2 |
| Size | small, medium | 2 |
| Prompt | P0, P1, P2, P3, P4 | 5 |
| Mode | full-story, sentence-by-sentence | 2 |

Each completed run is then scored at **8 post-processing stages**
(`raw, ordered, a, ade, ab, abde, abc, abcde`).

---

## 3. Proposed Plan

**Goal:** finish all experiments and analysis by **30 June**, leaving **1–15 July
(two weeks) for writing the research paper**.

### Phase 1 — Experiments (3 – 30 June)

| Week | Dates | Focus | Deliverable |
|------|-------|-------|-------------|
| 1 | Jun 3 – Jun 9 | **Finish core runs.** Complete any missing full-story runs (all models × P0–P4) and sentence-mode for the medium models. | All full-story + medium sentence runs in `results/llm_csv/` |
| 2 | Jun 10 – Jun 16 | **Complete the grid + Phase-2 variants.** Sentence mode for the small models (Llama-8B, Qwen-7B); P4 across remaining models; add and test post-processing alternates — A (`document_only`), B (`nearest_with_backoff`), C (`casefold`, `normalized`). | Full grid coverage + extra stage variants |
| 3 | Jun 17 – Jun 23 | **Diagnostic metrics + full evaluation.** Add % initially valid, % repaired by B, % blanked by C, % dropped by D/E, mean repair-shift distance; run batch evaluation across the whole grid; regenerate the master comparison sheet. | Final `master_comparison.xlsx` + diagnostics |
| 4 | Jun 24 – Jun 30 | **Analysis + error analysis.** Compare models/prompts/modes/stages; early vs. late-sentence behaviour; identify best configurations and common failure types; any quick follow-up runs. | Analysis notes, key plots, error summary |

### Phase 2 — Research Paper (1 – 15 July)

| Week | Dates | Focus | Deliverable |
|------|-------|-------|-------------|
| 5 | Jul 1 – Jul 7 | **Draft the paper.** Method, experiment setup, results and discussion sections using the analysis from Phase 1. | First full draft |
| 6 | Jul 8 – Jul 15 | **Revise and finalise.** Tighten the write-up, finalise tables/figures, tidy the repo and documentation. | Final paper ready for review |

---

## 4. Notes / Open Questions

- The plan is a **proposal** — happy to reprioritise (for example, bringing the
  diagnostic metrics earlier if they're more useful for the analysis).
- Compute time on the HPC is the main bottleneck for Weeks 1–2; the medium models
  (70B / 72B) take noticeably longer per run, so those runs are front-loaded.
- Questions to discuss in the Friday meeting:
  - Is the experiment grid above complete, or should any dimension be added/dropped?
  - Which metrics matter most for the final comparison?
  - Preferred venue / format for the research paper.

---

*Proposed timeline — to be confirmed. Last updated 2026-06-03.*
