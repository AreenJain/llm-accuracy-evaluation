# LLM-Based Factual Error Detection in Basketball Game Summaries

Evaluating modern open-weight Large Language Models (LLMs) as automatic
factual error annotators for AI generated basketball game summaries, scored
against the human Gold Standard from the [2021 Accuracy Evaluation Shared
Task](https://aclanthology.org/2021.inlg-1.23/) (Thomson & Reiter, 2021).

---

## Overview

Given an AI-generated basketball game summary and its underlying box-score
data, the task is to find every factual error, categorise it
(`NAME` / `NUMBER` / `WORD` / `CONTEXT` / `NOT_CHECKABLE` / `OTHER`), and
report the exact text span and a correction. Submitted annotations are scored
against the human Gold Standard (GSML) using the unmodified 2021 shared task
evaluation script, at both **mistake level** and **token level**
(precision / recall).

We evaluate two open-weight families (**Llama 3.1** 8B/70B, **Qwen 2.5**
7B/72B, plus an exploratory 14B) across a grid of prompting strategies and
two generation modes (full story vs sentence by sentence), with a
deterministic post-processing pipeline that repairs misaligned spans.

---

## Repository structure

```
.
├── pipeline/
│   ├── grove_pipeline.py         # HuggingFace inference (HPC / GPU)
│   ├── ollama_pipeline.py        # Ollama inference (local, small models)
│   ├── ollama_pipeline_sent.py   # Ollama, sentence by sentence mode
│   ├── ollama_pipeline_strat_1.py # Ollama, alternate prompting strategy
│   └── prompts.py                # All prompt templates (p0–p4, p0a–p0d)
├── post_processing/
│   ├── format_converter.py       # Normalise raw LLM CSV to evaluator format
│   ├── stage_a_sentence_only.py  # A: resolve to a single ID basis
│   ├── stage_b_nearest_fixed_n.py # B: recover invalid spans by search
│   ├── stage_c_strict_match.py   # C: match strictness (redundant, see notes)
│   ├── stage_d_overlap_resolver.py # D: resolve overlapping spans
│   └── stage_e_drop_unmatched.py # E: drop still unresolved spans
├── evaluation/
│   ├── evaluate.py               # 2021 shared task scorer (mistake + token)
│   ├── batch_evaluate.py         # Batch evaluate all runs/stages
│   └── LLM_evaluate.py           # LLM based evaluation helper
├── glmm_analysis/                # Mixed effects (GLMM) statistical analysis
│   ├── 01_build_outcome_tables.py # Build per observation 0/1 outcome tables
│   ├── 02_run_glmm.py            # Fit the GLMM for each of the four metrics
│   ├── tables/                   # Per observation outcome tables (CSV)
│   └── results/                  # Fitted odds ratios + GLMM_SUMMARY.md
├── data/
│   ├── DRIVE LINK FOR DATA.docx   # Google Drive link: full summaries, GSML, per-summary texts
│   ├── shared_task.jsonl          # Box-score data per game
│   └── token_lookup.yaml          # Sentence-to-document token position map
├── results/
│   └── DRIVE LINK FOR RESULTS.docx # Google Drive link: all raw/parsed/evaluated run outputs
├── test_set/                      # Held-out test set (mirrors the pipeline)
│   ├── pipeline/                  #   same inference scripts as above
│   ├── post_processing/           #   same 5 stage pipeline
│   ├── evaluation/                #   evaluate.py, batch_evaluate.py, LLM_evaluate.py
│   ├── data/                      #   data on Google Drive (see its DRIVE LINK doc)
│   └── results/                   #   results on Google Drive (see its DRIVE LINK doc)
└── requirements.txt              # Python dependencies
```

---

## Data

Built on the corpus from the [2021 Accuracy Evaluation Shared
Task](https://github.com/ehudreiter/accuracySharedTask): AI generated
basketball summaries, each with box-score data and a human Gold Standard
error annotation. Development set = 30 summaries (674 gold errors); a
separate held out test set (30 summaries, 622 gold errors) is used for the
final evaluation.

Because of their size, the full datasets and all run outputs are hosted on
Google Drive rather than in the repository. The `DRIVE LINK FOR ...`
documents in `data/`, `results/`, `test_set/data/` and `test_set/results/`
contain the links.

---

## Usage

### 1. Run inference

**Locally with Ollama** (small models):

```bash
# Pull a model once
ollama pull llama3.1:8b        # or: ollama pull qwen2.5:7b

python3 pipeline/ollama_pipeline.py \
  --games data/games_30_rows.csv \
  --jsonl data/shared_task.jsonl \
  --model llama_small \
  --rows 30 \
  --prompt p0 \
  --by_sent yes
```

**On a GPU / HPC cluster** (larger models):

```bash
python3 pipeline/grove_pipeline.py \
  --games data/games_30_rows.csv \
  --jsonl data/shared_task.jsonl \
  --model qwen_medium \
  --rows 30 \
  --prompt p0 \
  --by_sent yes
```

| Argument | Options | Meaning |
|---|---|---|
| `--model` | `llama_small`, `llama_medium`, `qwen_small`, `qwen_medium` (+ `qwen_14b` exploratory) | Which model to run |
| `--prompt` | `p0`, `p0a`, `p1`, `p2`, `p3`, `p4` (+ `p0b`–`p0d` exploratory) | Prompt strategy |
| `--by_sent` | `yes`, `no` | Sentence-by-sentence vs full-story |
| `--rows` | integer | Number of summaries to process |

Output: raw JSONL in `results/llm_raw/`, parsed CSV in `results/llm_csv/`.

### 2. Post-process

Repairs misaligned spans so annotations can be scored. Run from the project
root (stages read `data/texts/`):

```bash
python3 post_processing/format_converter.py --input results/llm_csv/<run>.csv
python3 post_processing/stage_a_sentence_only.py
python3 post_processing/stage_b_nearest_fixed_n.py
python3 post_processing/stage_c_strict_match.py
python3 post_processing/stage_d_overlap_resolver.py
python3 post_processing/stage_e_drop_unmatched.py
```

Each stage emits a diagnostic file and an evaluator ready file, so the
marginal effect of each stage can be measured.

### 3. Evaluate

```bash
python3 evaluation/batch_evaluate.py
```

Produces per config mistake level and token level precision/recall in
`results/eval_outputs/`.

---

## Prompt strategies

**Confirmatory grid** (the originally planned experiment):

| Prompt | Description |
|---|---|
| `p0`  | Baseline: task description, minimal formatting |
| `p1`  | Rule tuned: explicit span-selection constraints |
| `p2`  | JSON structure focused variant of p1 |
| `p3`  | LLM as judge persona |
| `p4`  | Context anchored: returns context windows instead of numeric positions |
| `p0a` | Early span control variant of p0 |

**Exploratory extensions** (developed later):

| Prompt | Description |
|---|---|
| `p0b` | Hard 1 - 3 word span limit + minimal correction rule |
| `p0c` | Adds contiguous-only + copy verbatim rules; cleaned of legacy annotator text |
| `p0d` | Few shot worked examples demonstrating error density |

---

## Post-processing pipeline

| Stage | Name | Function |
|---|---|---|
| A | ID basis | Resolve all annotations to document-level indices |
| B | Recovery | Relocate invalid spans by searching the source text |
| C | Strictness | Validate recovered text (strict/casefold/normalised) |
| D | Overlap resolver | Resolve overlapping spans greedily, left to right |
| E | Unmatched policy | Drop any annotation still unresolved |

> **Note:** Stage C was found to be empirically redundant: in 50 of 51
> configurations its output is identical to skipping it, because Stage E's
> document position check subsumes it. It is kept in the repo for
> completeness but can be omitted.
