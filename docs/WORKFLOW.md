# Practicum Workflow — Step-by-Step Guide

> **Project:** Factual error detection in computer-generated NBA basketball summaries
> using LLMs (Llama-3.1, Qwen-2.5).
> **GitHub:** https://github.com/AreenJain/llm-accuracy-evaluation

---

## 1. The Problem in One Paragraph

NBA game summaries written by LLMs often contain factual mistakes — wrong scores,
wrong player names, wrong dates, misleading context. The Thomson & Reiter (2021)
**shared task** released 60 such summaries with human annotations marking those
mistakes (the "GSML" gold-standard format). The shared task also ships an
official scorer `evaluate.py`. **Our research question:** can LLMs themselves
replicate human-level mistake annotation? We test 2 model families × 2 sizes
× 4 prompt strategies × 2 prompting modes (full-story vs sentence-by-sentence)
and score every combination through the shared task's official scorer.

---

## 2. Folder Structure (One-Look Map)

```
PRACTICUM/
├── docs/                        ← documentation (this file, Project Flow.md, logs.txt)
├── data/                        ← inputs (read-only)
│   ├── gsml.csv                 ← original 60-story GSML (gold standard)
│   ├── gsml_30_rows.csv         ← 30-story subset we use
│   ├── games.csv                ← full 60-game box scores + GENERATED_TEXT
│   ├── games_30_rows.csv        ← 30-game subset
│   ├── shared_task.jsonl        ← box-score JSON per game
│   ├── token_lookup.yaml        ← doc-token-id → (sentence_id, token_id) map
│   └── texts/                   ← 30 NBA story .txt files (one per game)
│
├── pipeline/                    ← LLM-call layer (runs on Grove HPC)
│   ├── grove_pipeline.py        ← MAIN: dispatches LLM, writes raw JSONL + CSV
│   ├── prompts.py               ← prompts p0, p0a, p1, p2, p3 (+ _sent variants) + p4 strategy prompt
│   ├── Huggingface_pipeline.py  ← older HF inference script
│   ├── ollama_pipeline.py       ← small-model variant via Ollama
│   ├── ollama_pipeline_sent.py  ← Ollama sentence-by-sentence variant
│   └── ollama_pipeline_strat_1.py ← Ollama strategy/anchoring (p4) variant
│
├── post_processing/             ← 3-stage cleanup pipeline (A→B→C, each with D+E inline)
│   ├── format_converter.py      ← Stage 0: rearrange columns + cast ints
│   ├── stage_a_sentence_only.py ← Stage A + D+E   → _a, _ade
│   ├── stage_b_nearest_fixed_n.py ← Stage B + D+E → _ab, _abde
│   ├── stage_c_strict_match.py  ← Stage C + D+E   → _abc, _abcde
│   ├── stage_d_overlap_resolver.py ← helper (resolve_overlaps)
│   ├── stage_e_drop_unmatched.py   ← helper (drop_unmatched + story-token validation)
│   └── recover_csv_from_raw.py  ← rebuild a results CSV from its raw JSONL (no re-run)
│
├── evaluation/                  ← scoring + comparison
│   ├── evaluate.py              ← canonical shared-task scorer (NEVER MODIFY)
│   ├── batch_evaluate.py        ← runs evaluate.py over all (run × stage); writes pivoted Excel
│   └── LLM_evaluate.py          ← legacy wrapper (kept for reference)
│
├── results/                     ← all generated outputs
│   ├── llm_raw/                 ← raw_outputs_<model>_<prompt_key>_run<N>.jsonl
│   ├── llm_csv/                 ← results_<model>_<prompt_key>_run<N>.csv (LLM annotations)
│   ├── formatted/               ← post-processing CSVs
│   │   ├── ordered/             ← _ordered.csv      (Stage 0)
│   │   ├── stage_a/             ← _a.csv            (Stage A only — diagnostic)
│   │   ├── stage_ade/           ← _ade.csv          (A + D + E, evaluable)
│   │   ├── stage_ab/            ← _ab.csv           (Stage B only — diagnostic)
│   │   ├── stage_abde/          ← _abde.csv         (A + B + D + E, evaluable)
│   │   ├── stage_abc/           ← _abc.csv          (Stage C only — diagnostic)
│   │   └── stage_abcde/         ← _abcde.csv        (A + B + C + D + E, final)
│   └── eval_outputs/            ← per-(run, stage) eval CSVs + master comparison
│
├── test_set/                    ← SELF-CONTAINED held-out test set (its own data + code + results)
│   ├── data/                    ← the 30 held-out games (TEXT_IDs T001–T030) + gold gsml
│   ├── pipeline/ post_processing/ evaluation/   ← copies of the code
│   └── results/                 ← test-set outputs (same structure as results/ above)
│
├── venv/                        ← Python virtual env (gitignored)
└── requirements.txt
```

---

## 3. End-to-End Flow at a Glance

```
                ┌──────────────────────────┐
                │  data/games_30_rows.csv  │
                │  data/shared_task.jsonl  │
                └─────────────┬────────────┘
                              ▼
              ┌────────────────────────────────┐
              │  pipeline/grove_pipeline.py    │  ← runs on Grove HPC
              │  --by_sent no  | --by_sent yes │
              └─────────────┬──────────────────┘
                            ▼
           results/llm_raw/raw_outputs_*.jsonl
           results/llm_csv/results_*.csv         ← raw LLM annotations
                            ▼
        ┌───────────────────────────────────────┐
        │  post_processing/format_converter.py  │  Stage 0
        └───────────────────┬───────────────────┘
                            ▼
                  results/formatted/ordered/_ordered.csv
                            ▼
        ┌───────────────────────────────────────┐
        │  stage_a_sentence_only.py             │  Stage A (+ D+E inline)
        └───────────────────┬───────────────────┘
                            ▼
                  results/formatted/stage_a/_a.csv      (full, may have NaN rows)
                  results/formatted/stage_ade/_ade.csv  (evaluable)
                            ▼
        ┌───────────────────────────────────────┐
        │  stage_b_nearest_fixed_n.py           │  Stage B (+ D+E inline)
        └───────────────────┬───────────────────┘
                            ▼
                  results/formatted/stage_ab/_ab.csv
                  results/formatted/stage_abde/_abde.csv
                            ▼
        ┌───────────────────────────────────────┐
        │  stage_c_strict_match.py              │  Stage C (+ D+E inline)
        └───────────────────┬───────────────────┘
                            ▼
                  results/formatted/stage_abc/_abc.csv
                  results/formatted/stage_abcde/_abcde.csv    ← final, fully cleaned
                            ▼
        ┌───────────────────────────────────────┐
        │  evaluation/batch_evaluate.py         │  runs evaluate.py × all (run, stage)
        └───────────────────┬───────────────────┘
                            ▼
                  results/eval_outputs/eval_<run>_<stage>.csv
                  results/eval_outputs/master_comparison.xlsx  ← final report
```

---

## 4. The Prompt Strategies

| Key | Style | Description |
|-----|-------|-------------|
| **p0** | Baseline | Shared-task instructions verbatim; minimal output rules |
| **p0a** | Short-span | p0 + a tail spelling out exactly which tokens to record for each category (NAME / NUMBER / WORD / NOT_CHECKABLE), to keep the TOKENS span minimal. Aimed at improving token precision. |
| **p1** | Strict-rules | Same as p0 + strict JSON-only output instructions (no markdown, no preamble) |
| **p2** | JSON-context | Recasts the box score as JSON; instructs the LLM to check sentence-by-sentence against JSON fields |
| **p3** | LLM-as-Judge | Persona prompt: "You are a senior sports fact-checker with 20 years experience…" |
| **p4** | Strategy / anchoring | Explicit field-by-field checking strategy (`p4` in `prompts.py`). Shown as **P4** in the comparison sheet. |

p0, p0a, p1, p2 and p3 each have a `_sent` variant (`p0_sent`, `p0a_sent`, …)
auto-derived in `prompts.py`. The `_sent` variant prepends a header forcing the
LLM to fact-check **one sentence at a time**, with `SENTENCE_ID` locked to the
loop value (not LLM-decided). p4 is currently run in full-story mode only.

---

## 5. Two LLM Prompting Modes

### Mode 1 — `--by_sent no` (full-story)
- One LLM call per story.
- Input: prompt + full story (~12 sentences) + full game data.
- Output: one JSON list of all mistakes found across the whole story.
- Files: `results_<model>_<prompt>_run<N>.csv` (no `_sent` suffix).

### Mode 2 — `--by_sent yes` (sentence-by-sentence)
- One LLM call **per sentence**, looped within each story.
- Input: sentence-mode prompt + single sentence + full game data + `sentence_id`.
- Output: per-sentence JSON list; merged into a single CSV per run.
- Files: `results_<model>_<prompt>_sent_run<N>.csv` (note `_sent`).
- `SENTENCE_ID` in the output is **forced** to the loop value — the LLM's
  reported `SENTENCE_ID` is ignored.

---

## 6. The Post-Processing Pipeline (Why It Exists)

LLM outputs cannot be fed directly into `evaluate.py` because:

1. **Column order mismatch** — LLM CSV has DOC_TOKEN columns before TYPE; GSML
   expects SENT_TOKEN columns first.
2. **Int-as-float** — pandas writes `18.0` when NaN exists; `evaluate.py`'s
   `int()` crashes on `"18.0"`.
3. **NaN positions** — LLM proposes TOKENS that aren't found verbatim in the
   story; position fields come out blank.
4. **Overlapping spans** — multiple annotations on the same tokens crash the
   evaluator with "Token X already used, duplicate".
5. **TYPE casing** — LLM outputs `"Name"`, evaluator expects `"NAME"`.

**Solution:** a 5-step cleanup pipeline applied serially. Stage A, B, C are
recovery/validation steps; Stage D, E are a forced-convert tail that always
runs after each. Design rule: D and E are single-method only;
variant exploration is reserved for A, B, C.

### Stage 0 — `format_converter.py`
- Reorders columns to GSML schema.
- Casts integer columns to `Int64` (handles NaN cleanly).
- Uppercases `TYPE` (`"Name"` → `"NAME"`).
- **Output:** `_ordered.csv`.

### Stage A — `stage_a_sentence_only.py`
- For each annotation with a `DOC_TOKEN_START/END`, looks up the corresponding
  `SENTENCE_ID` + `SENT_TOKEN_ID` from `data/token_lookup.yaml`.
- If start and end fall in **different sentences** (cross-sentence span), blanks
  the row (later stages will try to recover).
- **Output:** `_a.csv` (full, may have blank rows).
- Then **D + E** are applied in-memory to produce: `_ade.csv` (evaluable).

### Stage B — `stage_b_nearest_fixed_n.py`
- For each row with blank `SENT_TOKEN_START/END` but a known `SENTENCE_ID`
  and `TOKENS`, searches within the sentence for the n-gram match.
- Search order: distance 0, +1, −1, +2, −2, … from the original position.
- Fallback: doc-wide scan if sentence-level search fails.
- **Output:** `_ab.csv`. Then **D + E** → `_abde.csv` (evaluable).

> **Known issue (June 2026):** for some runs `_abde` scores *lower* than `_ade`
> (and `_abcde` lower than `_abde`). Stage B is recovering rows, but several of
> the recovered positions are not good matches — they land on the wrong span, so
> the scorer counts them as false positives and precision drops. In other words
> the extra recall from B/C is coming from low-quality recoveries. This needs to
> be investigated (tighten B's match acceptance, or only accept exact matches).

### Stage C — `stage_c_strict_match.py`
- For every row that still has a populated `SENT_TOKEN_START/END`, looks up
  the actual story tokens at that position and compares to the `TOKENS` field.
- If they don't match exactly, blanks the row.
- **Output:** `_abc.csv`. Then **D + E** → `_abcde.csv` (final, fully cleaned).

### Stage D (inline helper) — `resolve_overlaps(df)`
- Greedy left-to-right overlap removal.
- Sorts populated rows by `(TEXT_ID, SENTENCE_ID, SENT_TOKEN_START)`.
- Keeps the first occurrence of any (sentence_id, token_id) pair; blanks the rest.

### Stage E (inline helper) — `drop_unmatched(df)`
- Drops every row where `SENT_TOKEN_START` is `NaN`.
- Also drops rows whose tokens don't actually match the story at their position
  (the same check `evaluate.py` runs). This catches tokenization mismatches
  (e.g. the LLM wrote "11 point" but the story tokenizes it as "11-point") that
  would otherwise crash the scorer with an `AssertionError`. Uses `data/texts`
  and `data/token_lookup.yaml`, loaded once and cached.
- After this stage the CSV has no blanks and no mismatches → ready for `evaluate.py`.

> Why `_ade`, `_abde`, `_abcde` and not `_a`, `_ab`, `_abc`?
> Design decision: **D and E together = "forced convert" layer**. Every
> intermediate stage gets its own evaluable variant by applying D+E at the end.
> The `_a`/`_ab`/`_abc` files are kept as diagnostics only (they contain blank
> rows the evaluator can't handle).

---

## 7. Evaluation — `evaluation/batch_evaluate.py`

The shared-task scorer `evaluate.py` takes one submitted CSV at a time and
prints mistake-level and token-level Recall / Precision. `batch_evaluate.py`
wraps that:

1. **Auto-detect runs** — scans `results/llm_csv/` for `results_*.csv` files
   and extracts a list of `run_id` strings (e.g. `llama_medium_p0_run1`,
   `llama_medium_p0_sent_run1`).
2. **For each (run × stage) combo**, runs `evaluate.py` via `subprocess`.
   Stages evaluated: `raw`, `ordered`, `a`, `ade`, `ab`, `abde`, `abc`, `abcde`.
3. **Logs** every success to memory; every crash/missing file goes into
   `results/eval_outputs/_crashes.log`.
4. **Per-stage eval CSV** saved as `eval_<run>_<stage>.csv` in `results/eval_outputs/`.
5. **Master comparison** built at the end:
   - Reads the "combined" row (the one whose `categories` field contains `|`)
     from each successful eval CSV.
   - Produces `results/eval_outputs/master_comparison.xlsx`.
   - Color-scaled (red → yellow → green) so visual comparison is instant.

**Report layout:** `batch_evaluate.py` writes a **pivoted** table — left columns
are **Prompt | Mode | Stages**; across the top each **model** is a group (model
name → size small/medium → recall, token_recall, precision, token_precision).
Stray runs with no prompt in the filename are skipped automatically. (The old
separate `batch_evaluate_format.py` has been folded into `batch_evaluate.py`.)

---

## 8. How to Run End-to-End

### Setup (one-time)
```bash
cd /Users/areenjain/PRACTICUM
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Stage 1 — Generate LLM annotations (Grove HPC)
SSH into Grove, then for each (model × prompt × mode) combination:
```bash
# full-story
python3 grove_pipeline.py \
  --games games_30_rows.csv \
  --jsonl shared_task.jsonl \
  --model llama_medium \
  --rows 30 \
  --prompt p0 \
  --by_sent no

# sentence-by-sentence
python3 grove_pipeline.py \
  --games games_30_rows.csv \
  --jsonl shared_task.jsonl \
  --model llama_medium \
  --rows 30 \
  --prompt p0 \
  --by_sent yes
```
`--prompt` accepts: `p0`, `p0a`, `p1`, `p2`, `p3`, `p4`. `--model` accepts:
`llama_small`, `llama_medium`, `qwen_small`, `qwen_medium`.
Outputs land in `results/llm_raw/` (raw JSONL) and `results/llm_csv/` (CSV).
Download these back to local before running post-processing.

### Stage 2 — Post-process (local)
```bash
cd /Users/areenjain/PRACTICUM
source venv/bin/activate

python3 post_processing/format_converter.py
python3 post_processing/stage_a_sentence_only.py
python3 post_processing/stage_b_nearest_fixed_n.py
python3 post_processing/stage_c_strict_match.py
```
Each script auto-discovers all relevant inputs from the previous stage's folder.
No CLI args needed — defaults are wired to the new folder layout.

### Stage 3 — Evaluate everything
```bash
python3 evaluation/batch_evaluate.py
```
Takes 5–10 min; one attempt per (run × stage).
Final output: `results/eval_outputs/master_comparison.xlsx`.

### Recovering an empty CSV (no model re-run)
If a run left a valid raw JSONL but an empty CSV (p4 schema or a bare-object
reply), rebuild the CSV straight from the raw file:
```bash
python3 post_processing/recover_csv_from_raw.py \
  --raw   results/llm_raw/raw_outputs_qwen_medium_p4_run1.jsonl \
  --games data/games_30_rows.csv \
  --out   results/llm_csv/results_qwen_medium_p4_run1.csv \
  --model qwen_medium --prompt_key p4
```
It re-parses with a forgiving `json.loads`, auto-numbers `ANNOTATION_ID` when
missing, and recomputes `DOC_TOKEN_START/END` exactly like `grove_pipeline`.
Then re-run Stages 2 and 3.

### Running the held-out test set
The `test_set/` folder is **self-contained** — it has its own `data/`, code, and
`results/`. Run everything **from inside it** so the relative paths (and the
story-token validation in Stage E) resolve to the test data, not the dev data:
```bash
cd test_set
python3 post_processing/format_converter.py
python3 post_processing/stage_a_sentence_only.py
python3 post_processing/stage_b_nearest_fixed_n.py
python3 post_processing/stage_c_strict_match.py
python3 evaluation/batch_evaluate.py
```
> Running the test-set scripts from the project root instead loads the **dev**
> texts in Stage E and silently drops every test row (empty `_ade`/`_abde`/
> `_abcde`). Always `cd test_set` first.

---

## 9. Configuration Reference

### Models tested
| Key | Size | Path on Grove (`MODELS` dict in grove_pipeline.py) |
|-----|------|-----------------------------------------------------|
| `llama_small` | 8B  | `/home/support/llm/Llama-3.1-8B-Instruct` (shared dir) |
| `llama_medium` | 70B (4-bit quant) | `/home/support/llm/Llama-3.1-70B-Instruct` (shared dir) |
| `qwen_small` | 7B  | `~/models/Qwen2.5-7B-Instruct` (download yourself; `~` resolves per user) |
| `qwen_medium` | 72B (4-bit quant) | `/home/support/llm/Qwen2.5-72B-Instruct` (shared dir) |

Medium models load with BitsAndBytes 4-bit NF4 quantization on 2× RTX A6000 GPUs.
Most models live in the shared `/home/support/llm/` directory; Qwen-7B is **not**
there, so each user downloads it into their own `~/models/` (the dict uses
`os.path.expanduser` so it works for everyone).

### File naming pattern
- Full-story:   `raw_outputs_llama_medium_p0_run1.jsonl` / `results_llama_medium_p0_run1.csv`
- Sentence:     `raw_outputs_llama_medium_p0_sent_run1.jsonl` / `results_llama_medium_p0_sent_run1.csv`

Counter (`_run1`, `_run2`, …) is per-(model, prompt_key) and bumps automatically.

### CSV schema (LLM annotations)
```
TEXT_ID, SENTENCE_ID, ANNOTATION_ID, TOKENS,
DOC_TOKEN_START, DOC_TOKEN_END,
TYPE, CORRECTION, COMMENT,
MODEL, PROMPT_KEY, TIME_SECONDS
```
After format_converter, GSML schema with extras:
```
TEXT_ID, SENTENCE_ID, ANNOTATION_ID, TOKENS,
SENT_TOKEN_START, SENT_TOKEN_END,
DOC_TOKEN_START, DOC_TOKEN_END,
TYPE, CORRECTION, COMMENT
```

### Raw JSONL line schema
```json
{
  "text_id": "S001",
  "sentence_id": 1,             // only present in sentence mode
  "prompt_key": "p0_sent",
  "is_valid_json": true,
  "raw_output": "[ ... ]"
}
```

---

## 10. Current Status (as of June 2026)

- **Pipeline:** working end-to-end on **both** the dev set (30 games, S001–S030)
  and the held-out **test set** (30 games, T001–T030 in `test_set/`). Full grid:
  Llama-3.1 / Qwen-2.5 × small / medium × P0, P0a, P1–P4 × full / sentence
  (P4 is full-story only). Both produce a `master_comparison.xlsx`.

### Key results (full pipeline `_abcde`, token recall)
| Finding | Dev | Test |
|---------|-----|------|
| Best config: **Qwen-72B, P0, sentence** | 0.751 (prec 0.761) | 0.561 (prec 0.615) |
| Same config, **full-story** | 0.416 | 0.362 |
| **Sentence mode lifts recall a lot** (Llama-70B P0) | 0.031 → 0.493 | 0.040 → 0.267 |
| **7B sentence ≈ 72B full-story** (Qwen) | small-sent 0.416 = medium-full 0.416 | — |

### Headline findings (consistent across dev and test)
1. **Sentence-by-sentence prompting is the biggest lever** and lets a 7B model
   match a 72B model in full-story mode.
2. **Detection vs localization gap:** models locate errors well (mistake
   precision ~0.76) but over-extend the span (token precision ~0.12). **P0a**
   confirms it — token precision roughly doubles (0.12 → 0.23) but recall halves.
3. **Per-category:** strong on NAME (prec ~0.87) and NUMBER, weak on WORD;
   CONTEXT precision collapses (~0.03) because the model over-predicts subjective
   "misleading/redundant" judgments that aren't in the gold standard.
4. **Findings generalise:** the best-config ranking is identical on the held-out
   test set; absolute numbers drop ~25% but precision stays high.

- **Known issues:**
  - Some runs produced an **empty CSV from a valid raw JSONL** — the p4 prompt
    omits `ANNOTATION_ID` (rejected by the strict parser), and a few sentence
    runs returned a bare object. Fixed by re-running `recover_csv_from_raw.py`
    (rebuilds the CSV from the raw JSONL, no model re-run). See Section 8.
  - Post-processing anomaly: for some runs `_abde` scores lower than `_ade` —
    Stage B/C recover low-quality rows that act as false positives. For the strong
    runs the stages are neutral (ade = abde = abcde). Needs investigation.
  - Degenerate repetition in some runs (the same annotation many times) — a
    decoding issue, to be tackled with temperature / repetition-penalty later.
- **Pending:**
  - `test_set` `llama_small` runs (no raw was produced yet — re-run on Grove).
  - Decoding-level ablation; the planned diagnostic metrics below.
- **Diagnostic metrics to add** (planned):
  - % initially valid · % repaired by B · % blanked by C · % dropped by D/E
  - Mean repair shift distance (B)

---

## 11. Key Decisions / Conventions

- `evaluate.py` is **never modified** — it is the canonical scorer.
- Folder names never contain spaces (scripts use relative paths from project root).
- Every script is run **from the project root**, e.g.
  `python3 post_processing/stage_a_sentence_only.py`, never `cd`-ing into the
  subfolder.
- All intermediate stages keep their full output (`_a`, `_ab`, `_abc`) for
  diagnostics — even though they aren't evaluable themselves.
- `MODE` column in `master_comparison.xlsx` always identifies whether a row
  came from a full-story or sentence-mode run.

---

## 12. Glossary

- **GSML** — Gold-Standard Mistake List. The 60-story human-annotated dataset from Thomson & Reiter 2021.
- **Annotation** — A single mistake marked by a human (or LLM) with a token span, type, and correction.
- **Doc token** — A token's position counted across the whole story (1-indexed).
- **Sentence token** — A token's position within its own sentence (1-indexed per sentence).
- **Span** — A `(SENT_TOKEN_START, SENT_TOKEN_END)` pair marking the wrong word(s).
- **Stage** — A single processing step (raw, ordered, a, ade, ab, abde, abc, abcde).
- **Mode** — Either `full` (whole-story per LLM call) or `sent` (sentence-by-sentence).
- **Prompt key** — `p0`/`p0a`/`p1`/`p2`/`p3`/`p4` for full-story, or `p0_sent`/`p0a_sent`/etc. for sentence mode (p0–p3 and p0a). p0a is the short-span prompt; p4 is the strategy prompt, shown as **P4**.
- **Run ID** — `<model>_<size>_<prompt_key>_run<N>`, e.g. `llama_medium_p0_sent_run1`.

---

## 13. Handy One-Off Commands

Run the p4 (strategy) prompt on a single small model, full-story:
```bash
python pipeline/ollama_pipeline_strat_1.py \
  --games data/games_30_rows.csv \
  --jsonl data/shared_task.jsonl \
  --model llama_small \
  --rows 30 \
  --prompt p4 \
  --by_sent no
```

Score one stage manually with the canonical scorer:
```bash
python evaluation/evaluate.py \
  --gsml data/gsml_30_rows.csv \
  --submitted results/formatted/ordered/results_llama_small_p4_run1_ordered.csv \
  --token_lookup data/token_lookup.yaml \
  --text_dir data/texts \
  --csv_out results/eval_outputs/eval_llama_small_p4_run1.csv
```

---
