# LLM-Based Factual Error Detection in Basketball Game Summaries

Evaluating modern open-weight Large Language Models (LLMs) as automatic
factual-error annotators for AI-generated basketball game summaries, scored
against the human Gold Standard from the [2021 Accuracy Evaluation Shared
Task](https://aclanthology.org/2021.inlg-1.23/) (Thomson & Reiter, 2021).

This is an MSc practicum project at Dublin City University.

---

## Overview

Given an AI-generated basketball game summary and its underlying box-score
data, the task is to find every factual error, categorise it
(`NAME` / `NUMBER` / `WORD` / `CONTEXT` / `NOT_CHECKABLE` / `OTHER`), and
report the exact text span and a correction. Submitted annotations are scored
against the human Gold Standard (GSML) using the unmodified 2021 shared-task
evaluation script, at both **mistake level** and **token level**
(precision / recall).

We evaluate two open-weight families (**Llama 3.1** 8B/70B, **Qwen 2.5**
7B/72B, plus an exploratory 14B) across a grid of prompting strategies and
two generation modes (full-story vs sentence-by-sentence), with a
deterministic post-processing pipeline that repairs misaligned spans.

---

## Repository structure

```
.
├── pipeline/
│   ├── grove_pipeline.py         # HuggingFace inference (HPC / GPU)
│   ├── ollama_pipeline.py        # Ollama inference (local, small models)
│   └── prompts.py                # All prompt templates (p0–p4, p0a–p0d)
├── post_processing/
│   ├── format_converter.py       # Normalise raw LLM CSV → evaluator format
│   ├── stage_a_sentence_only.py  # A: resolve to a single ID basis
│   ├── stage_b_nearest_fixed_n.py# B: recover invalid spans by search
│   ├── stage_c_strict_match.py   # C: match-strictness (redundant, see notes)
│   ├── stage_d_overlap_resolver.py # D: resolve overlapping spans
│   └── stage_e_drop_unmatched.py # E: drop still-unresolved spans
├── evaluation/
│   ├── evaluate.py               # 2021 shared-task scorer (mistake + token)
│   └── batch_evaluate.py         # Batch-evaluate all runs/stages
├── glmm_analysis/                # Mixed-effects (GLMM) statistical analysis
├── data/
│   ├── games_30_rows.csv         # Summaries used (TEXT_ID, GENERATED_TEXT)
│   ├── shared_task.jsonl         # Box-score data per game
│   ├── gsml_30_rows.csv          # Gold Standard error annotations
│   ├── token_lookup.yaml         # Sentence↔document token position map
│   └── texts/                    # Per-summary .txt files (S001.txt …)
├── results/
│   ├── llm_raw/                  # Raw model output (JSONL)
│   ├── llm_csv/                  # Parsed annotations (CSV)
│   └── eval_outputs/             # Per-config evaluation results
├── test_set/                     # Held-out test set (mirror of the pipeline)
└── docs/
    └── WORKFLOW.md               # Step-by-step pipeline walkthrough
```

---

## Installation

Requires Python 3.9+.

```bash
git clone <repository-url>
cd PRACTICUM
pip install -r requirements.txt
```

Core dependencies: `pandas`, `pydantic`, `langchain-core`, `nltk`,
`rapidfuzz`, `pyyaml`. For local inference: [Ollama](https://ollama.com/).
For GPU inference: `transformers`, `torch`, `accelerate`, `bitsandbytes`.

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

Each stage emits a diagnostic file and an evaluator-ready file, so the
marginal effect of each stage can be measured. (Stage C can be skipped — see
the note below.)

### 3. Evaluate

```bash
python3 evaluation/batch_evaluate.py
```

Produces per-config mistake-level and token-level precision/recall in
`results/eval_outputs/`.

---

## Prompt strategies

**Confirmatory grid** (the originally planned experiment):

| Prompt | Description |
|---|---|
| `p0`  | Baseline: task description, minimal formatting |
| `p1`  | Rule-tuned: explicit span-selection constraints |
| `p2`  | JSON-structure-focused variant of p1 |
| `p3`  | LLM-as-judge persona |
| `p4`  | Context-anchored: returns context windows instead of numeric positions |
| `p0a` | Early span-control variant of p0 |

**Exploratory extensions** (developed later):

| Prompt | Description |
|---|---|
| `p0b` | Hard 1–3 word span limit + minimal-correction rule |
| `p0c` | Adds contiguous-only + copy-verbatim rules; cleaned of legacy annotator text |
| `p0d` | Few-shot worked examples demonstrating error density |

---

## Post-processing pipeline

| Stage | Name | Function |
|---|---|---|
| A | ID basis | Resolve all annotations to document-level indices |
| B | Recovery | Relocate invalid spans by searching the source text |
| C | Strictness | Validate recovered text (strict/casefold/normalised) |
| D | Overlap resolver | Resolve overlapping spans greedily, left to right |
| E | Unmatched policy | Drop any annotation still unresolved |

> **Note:** Stage C was found to be empirically redundant — in 50 of 51
> configurations its output is identical to skipping it, because Stage E's
> document-position check subsumes it. It is kept in the repo for
> completeness but can be omitted.

---

## Key findings

- **No configuration approaches the human Gold Standard.** The best result
  (Qwen-72B, p0, sentence mode) reaches ~0.41 recall / 0.76 precision on the
  development set — the pervasive high-precision/low-recall pattern reported
  in the LLM-reliability literature.
- **Model scale and sentence-level prompting** are the dominant performance
  factors (confirmed by a per-metric GLMM).
- **Simple prompts win on recall; span-control prompts win on token
  precision** — a clean precision–recall trade-off, with the effect sign
  flipping between the two metrics.
- **Context and Not-Checkable errors remain largely undetected**, matching
  the blind spot of the 2021 automatic systems. For Context errors the model
  usually locates the correct span but mislabels the error type.
- **Against the 2021 benchmark**, a zero-shot LLM lands mid-field among
  purpose-built automatic systems, with no task-specific engineering.

---

## Data

Built on the corpus from the [2021 Accuracy Evaluation Shared
Task](https://github.com/ehudreiter/accuracySharedTask): AI-generated
basketball summaries, each with box-score data and a human Gold Standard
error annotation. Development set = 30 summaries (674 gold errors); a
separate held-out test set (30 summaries, 622 gold errors) is used for the
final evaluation.

---

## Citation

If you use this work, please cite the shared task it builds on:

```bibtex
@inproceedings{thomson-reiter-2021-generation,
  title     = {Generation Challenges: Results of the Accuracy Evaluation Shared Task},
  author    = {Thomson, Craig and Reiter, Ehud},
  booktitle = {Proceedings of the 14th International Conference on Natural Language Generation},
  year      = {2021},
  address   = {Aberdeen, Scotland, UK},
  pages     = {240--248},
}
```

---

## Authors

Harshal Rajendra Ahire and Areen Jain — MSc practicum, Dublin City University.
Supervised by Anya Belz and Craig Thomson.

## Acknowledgements

Access to the Grove HPC cluster at Dublin City University.
